"""Batch Analysis page (admin-only): Trigger/Monitor/Correct batch stock-analysis runs
via the Batch Analysis UI API (src/share_insights_v1/api/batch_jobs.py), which runs
jobs as durable, independent OS processes so they survive a dropped connection or the
browser closing - see BATCH_ANALYSIS_UI_REQUIREMENTS.md (repo root) for the full
requirements this implements.
"""

import os
import sys

import requests
import streamlit as st

# Add project root to path for absolute imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# NOTE: pages/login_page.py, not the top-level dashboard/login_page.py - these are two
# different modules with identically-named functions.
from src.share_insights_v1.dashboard.pages.login_page import check_authentication, render_navigation
from src.share_insights_v1.dashboard.components.disclaimer import show_disclaimer
from src.share_insights_v1.dashboard.components.theme import inject_theme_css, section_label, render_kv_table

API_BASE = "http://localhost:8000/api/batch-jobs"

_STATUS_EMOJI = {
    "running": "🟢", "queued": "🟡", "completed": "✅",
    "failed": "🔴", "cancelled": "⚪", "crashed": "💥",
}


def _api_get(path, **params):
    try:
        resp = requests.get(f"{API_BASE}{path}", params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API request failed: {e}")
        return None


def _api_post(path, json=None):
    try:
        resp = requests.post(f"{API_BASE}{path}", json=json, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API request failed: {e}")
        return None


def _api_put(path, json=None):
    try:
        resp = requests.put(f"{API_BASE}{path}", json=json, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API request failed: {e}")
        return None


def _render_trigger_tab():
    files_data = _api_get("/input-files") or {"files": []}
    files = files_data.get("files", [])

    if not files:
        st.warning("No CSV files found in stock_dump/.")
        return

    selected_files = st.multiselect(
        "Files to run (in order)", files,
        help="Every .csv in stock_dump/ - including the small ones, useful for testing this page."
    )
    threads = st.number_input("Threads", min_value=1, value=2)

    if st.button("🚀 Trigger", type="primary", disabled=not selected_files):
        result = _api_post("/trigger", json={
            "files": selected_files,
            "threads": int(threads),
            "created_by": st.session_state.get("username", "admin"),
        })
        if result:
            st.success(f"Queued {len(result.get('batch_job_ids', []))} job(s): {', '.join(selected_files)}")
            st.rerun()


def _render_job_row(job):
    label = (
        f"{_STATUS_EMOJI.get(job['status'], '❔')} {job['exchange']} — {job['status'].upper()} "
        f"({job['completed_stocks']}/{job['total_stocks']} done, {job['failed_stocks']} failed)"
    )
    with st.expander(label):
        if job["status"] == "running" and job["total_stocks"]:
            done = job["completed_stocks"] + job["failed_stocks"]
            st.progress(min(done / job["total_stocks"], 1.0))

        pairs = [
            ("Batch Job ID", job["batch_job_id"]),
            ("Created", job["created_at"] or "-"),
            ("Started", job["started_at"] or "-"),
            ("Completed", job["completed_at"] or "-"),
            ("Threads", job["thread_count"]),
            ("Created By", job["created_by"] or "-"),
        ]
        if job.get("eta_seconds") is not None:
            pairs.append(("ETA", f"{job['eta_seconds']}s"))
        render_kv_table(pairs, cols=2)

        if job["failed_stocks"]:
            if st.button("🔍 View failures", key=f"failures_{job['batch_job_id']}"):
                data = _api_get(f"/{job['batch_job_id']}/failures")
                if data and data.get("available"):
                    st.dataframe(data["failures"], use_container_width=True)
                else:
                    st.caption("No structured failure log available for this job "
                               "(older jobs used a plain-text log format).")

        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if job["status"] in ("running", "queued"):
                action = "Cancel" if job["status"] == "running" else "Remove from queue"
                if st.button(f"🛑 {action}", key=f"cancel_{job['batch_job_id']}"):
                    _api_post(f"/{job['batch_job_id']}/cancel")
                    st.rerun()
        with action_col2:
            if job["status"] in ("completed", "failed", "cancelled", "crashed") and job["failed_stocks"]:
                if st.button("🔁 Retry remaining", key=f"retry_{job['batch_job_id']}"):
                    _api_post(f"/{job['batch_job_id']}/retry")
                    st.rerun()


def _render_monitor_tab():
    if st.button("🔄 Refresh"):
        st.rerun()

    data = _api_get("/")
    jobs = (data or {}).get("jobs", [])
    if not jobs:
        st.info("No batch jobs yet - trigger one from the Trigger tab.")
        return

    running = [j for j in jobs if j["status"] == "running"]
    queued = [j for j in jobs if j["status"] == "queued"]
    history = [j for j in jobs if j["status"] not in ("running", "queued")]

    if running:
        section_label(f"Running ({len(running)})")
        for job in running:
            _render_job_row(job)

    if queued:
        section_label(f"Queued ({len(queued)})")
        for job in queued:
            _render_job_row(job)

    if history:
        section_label(f"History ({len(history)})")
        for job in history:
            _render_job_row(job)


def _render_correct_tab():
    section_label("Queue")
    if st.button("🧹 Clear entire queue", help="Cancels every currently queued job."):
        result = _api_post("/queue/clear")
        if result is not None:
            st.success(f"Cleared {len(result.get('cancelled', []))} queued job(s).")
            st.rerun()

    section_label("Concurrency Limit")
    st.caption("How many batch jobs can run at once - additional triggers wait in the queue.")
    current = _api_get("/settings/concurrency-limit") or {"limit": 1}
    new_limit = st.number_input("Max concurrent batch jobs", min_value=1, value=current["limit"], key="concurrency_limit_input")
    if st.button("Save limit"):
        _api_put("/settings/concurrency-limit", json={"limit": int(new_limit)})
        st.success("Updated.")
        st.rerun()

    st.caption("Cancel and retry individual jobs from the Monitor tab, next to each job.")


def main():
    if not check_authentication():
        st.switch_page("pages/login_page.py")
        return

    render_navigation()

    if st.session_state.get("user_role") != "admin":
        st.error("🚫 Access Denied: Admin role required")
        st.info("Please contact your administrator for access to batch analysis.")
        return

    inject_theme_css()

    st.title("⚙️ Batch Analysis")
    show_disclaimer()
    st.markdown("*Trigger, monitor, and manage batch stock-analysis runs*")

    tab_trigger, tab_monitor, tab_correct = st.tabs(["🚀 Trigger", "📡 Monitor", "🛠️ Correct"])
    with tab_trigger:
        _render_trigger_tab()
    with tab_monitor:
        _render_monitor_tab()
    with tab_correct:
        _render_correct_tab()


if __name__ == "__main__":
    main()
