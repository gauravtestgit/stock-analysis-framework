"""API endpoints for the Batch Analysis UI page (Trigger/Monitor/Correct).

Runs batch jobs (via services/batch/batch_analysis_service_quant.py, the same service
test_batch_analysis.py/the cron job use) as independent OS processes so they survive
the browser tab closing, the admin's connection dropping, or this API server itself
restarting - the durability problem that motivated this feature. See
BATCH_ANALYSIS_UI_REQUIREMENTS.md (repo root) for the full requirements this implements.

Deliberately does not touch the existing /batch/* endpoints in main.py (a different,
in-process async mechanism via api/batch_service.py, unused by any UI today) or
test_batch_analysis.py (left exactly as-is for the existing cron job).
"""

import csv
import os
import subprocess
import sys
from datetime import datetime, timezone
from typing import List, Optional

import psutil
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..models.database import SessionLocal
from ..models.strategy_models import BatchJob, BatchSettings

router = APIRouter()

# __file__ = .../src/share_insights_v1/api/batch_jobs.py
_SHARE_INSIGHTS_V1_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(os.path.dirname(_SHARE_INSIGHTS_V1_DIR))
_STOCK_DUMP_DIR = os.path.join(_SHARE_INSIGHTS_V1_DIR, "resources", "stock_dump")
_STOCK_ANALYSES_DIR = os.path.join(_SHARE_INSIGHTS_V1_DIR, "resources", "stock_analyses")
_BATCH_LOGS_DIR = os.path.join(_SHARE_INSIGHTS_V1_DIR, "resources", "tmp", "batch_logs")


class TriggerRequest(BaseModel):
    files: List[str]
    threads: int = 2
    created_by: str = "admin"


class ConcurrencyLimitRequest(BaseModel):
    limit: int


def _get_concurrency_limit(db: Session) -> int:
    settings = db.query(BatchSettings).filter(BatchSettings.id == 1).first()
    return settings.concurrency_limit if settings else 1


def _count_csv_rows(csv_path: str) -> int:
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)  # header
        return sum(1 for _ in reader)


def _job_to_dict(job: BatchJob) -> dict:
    remaining = None
    eta_seconds = None
    if job.status == "running" and job.total_stocks:
        remaining = max(job.total_stocks - job.completed_stocks - job.failed_stocks, 0)
        if job.started_at:
            elapsed = (datetime.utcnow() - job.started_at).total_seconds()
            done = job.completed_stocks + job.failed_stocks
            if done > 0 and elapsed > 0:
                eta_seconds = round((elapsed / done) * remaining)
    return {
        "batch_job_id": str(job.id),
        "name": job.name,
        "exchange": job.exchange,
        "status": job.status,
        "total_stocks": job.total_stocks,
        "completed_stocks": job.completed_stocks,
        "failed_stocks": job.failed_stocks,
        "remaining_stocks": remaining,
        "eta_seconds": eta_seconds,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "created_by": job.created_by,
        "thread_count": job.thread_count,
        "pid": job.pid,
    }


def _spawn_job(job: BatchJob, db: Session):
    """Launch job as a detached OS subprocess and mark it running with its pid."""
    os.makedirs(_BATCH_LOGS_DIR, exist_ok=True)
    log_path = os.path.join(_BATCH_LOGS_DIR, f"{job.id}.log")

    cmd = [
        sys.executable, "-m", "src.share_insights_v1.scripts.run_batch_job",
        "--batch-job-id", str(job.id),
        "--threads", str(job.thread_count or 2),
    ]
    env = os.environ.copy()
    # The child's stdout encoding is governed by its own environment, not by how the
    # parent opened the log file it's redirected into - on Windows this defaults to the
    # console codepage (cp1252), which crashes on the first emoji print() anywhere in
    # the analysis pipeline (there are several). Force UTF-8 so a detached subprocess
    # with no real console still works the same as an interactive one.
    env['PYTHONIOENCODING'] = 'utf-8'

    popen_kwargs = dict(cwd=_REPO_ROOT, env=env)
    if os.name == 'nt':
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    with open(log_path, 'a', encoding='utf-8') as logfile:
        logfile.write(f"\n=== Starting attempt at {datetime.utcnow().isoformat()} ===\n")
        logfile.flush()
        process = subprocess.Popen(cmd, stdout=logfile, stderr=subprocess.STDOUT, **popen_kwargs)

    job.status = "running"
    job.pid = process.pid
    db.commit()


def _promote_queued_jobs(db: Session):
    """Opportunistic queue-promotion, called at the end of every mutating endpoint and
    every list/status poll - no scheduler/background thread exists or is needed, since
    a batch job's own subprocess already writes its progress/completion straight to the
    DB, and nothing here needs to "wait" for that beyond the next time this is called."""

    # Detect processes that died without reaching completion (crash/OOM/etc.), freeing
    # their concurrency slot instead of leaving it stuck forever - the same kind of
    # silent-death problem (an SSH session dropping) that motivated this whole feature.
    running_jobs = db.query(BatchJob).filter(BatchJob.status == "running").all()
    for job in running_jobs:
        if job.pid is None or not psutil.pid_exists(job.pid):
            job.status = "crashed"
            job.completed_at = datetime.now(timezone.utc)
    if running_jobs:
        db.commit()

    limit = _get_concurrency_limit(db)
    running_count = db.query(BatchJob).filter(BatchJob.status == "running").count()

    while running_count < limit:
        next_job = (
            db.query(BatchJob)
            .filter(BatchJob.status == "queued")
            .order_by(BatchJob.created_at.asc())
            .first()
        )
        if not next_job:
            break
        _spawn_job(next_job, db)
        running_count += 1


@router.get("/input-files")
async def list_input_files():
    """Every .csv in stock_dump/, for the Trigger dropdown - listed as-is, no
    filtering/curation (all of them hold real tickers and are legitimate to run,
    including the smaller ones which are specifically useful for testing this page)."""
    if not os.path.isdir(_STOCK_DUMP_DIR):
        return {"files": []}
    files = sorted(f for f in os.listdir(_STOCK_DUMP_DIR) if f.lower().endswith('.csv'))
    return {"files": files}


@router.post("/trigger")
async def trigger_batch_jobs(request: TriggerRequest):
    """Create a queued BatchJob row per requested file, in order. Running multiple
    files "in sequence" falls out of this for free - they're just multiple queued rows,
    and the concurrency-limited promotion below naturally runs them one after another."""
    if not request.files:
        raise HTTPException(status_code=400, detail="No files specified")

    db = SessionLocal()
    try:
        created_ids = []
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        for filename in request.files:
            input_path = os.path.join(_STOCK_DUMP_DIR, filename)
            if not os.path.isfile(input_path):
                raise HTTPException(status_code=404, detail=f"Input file not found: {filename}")

            exchange = os.path.splitext(filename)[0].upper()
            total_stocks = _count_csv_rows(input_path)
            output_path = os.path.join(_STOCK_ANALYSES_DIR, f"{exchange}_{timestamp}_analysis.csv")

            job = BatchJob(
                name=f"{exchange} Analysis {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                exchange=exchange,
                status="queued",
                total_stocks=total_stocks,
                completed_stocks=0,
                failed_stocks=0,
                input_file=input_path,
                output_file=output_path,
                created_by=request.created_by,
                thread_count=request.threads,
            )
            db.add(job)
            db.flush()
            created_ids.append(str(job.id))

        db.commit()
        _promote_queued_jobs(db)
        return {"batch_job_ids": created_ids}
    finally:
        db.close()


@router.get("/")
async def list_batch_jobs(include_cancelled: bool = True):
    """Full job list for the Monitor tab - running, queued, and history. Always
    includes cancelled/failed/crashed by default here (this page's job is the full
    picture); include_cancelled only matters for callers that want to narrow it."""
    db = SessionLocal()
    try:
        _promote_queued_jobs(db)
        query = db.query(BatchJob)
        if not include_cancelled:
            query = query.filter(BatchJob.status != "cancelled")
        jobs = query.order_by(BatchJob.created_at.desc()).all()
        return {"jobs": [_job_to_dict(j) for j in jobs]}
    finally:
        db.close()


@router.get("/{batch_job_id}/failures")
async def get_batch_job_failures(batch_job_id: str):
    """Ticker/error_type/error_message/timestamp rows from the job's failure CSV.
    Degrades gracefully (not an error) if the file doesn't exist yet, or predates the
    structured-CSV failure log format (still .txt for any job run before that change)."""
    db = SessionLocal()
    try:
        job = db.query(BatchJob).filter(BatchJob.id == batch_job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Batch job not found")
        if not job.output_file:
            return {"failures": [], "available": False}

        failure_csv = job.output_file.replace('.csv', '_failures.csv')
        if not os.path.isfile(failure_csv):
            return {"failures": [], "available": False}

        failures = []
        with open(failure_csv, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != ['Ticker', 'Error_Type', 'Error_Message', 'Timestamp']:
                # Old .txt-era file reused the .csv name, or an unexpected format - don't
                # try to parse it as structured data.
                return {"failures": [], "available": False}
            failures = list(reader)
        return {"failures": failures, "available": True}
    finally:
        db.close()


@router.post("/{batch_job_id}/cancel")
async def cancel_batch_job(batch_job_id: str):
    """Unified cancel-or-dequeue: a queued job just gets marked cancelled (no process
    exists yet); a running job gets its process terminated first."""
    db = SessionLocal()
    try:
        job = db.query(BatchJob).filter(BatchJob.id == batch_job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Batch job not found")

        if job.status == "running" and job.pid:
            try:
                if psutil.pid_exists(job.pid):
                    psutil.Process(job.pid).terminate()
            except psutil.NoSuchProcess:
                pass
        elif job.status not in ("queued", "running"):
            return {"batch_job_id": batch_job_id, "status": job.status}  # already terminal, no-op

        job.status = "cancelled"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

        _promote_queued_jobs(db)
        return {"batch_job_id": batch_job_id, "status": job.status}
    finally:
        db.close()


@router.post("/queue/clear")
async def clear_queue():
    """Cancel every currently-queued job."""
    db = SessionLocal()
    try:
        queued_jobs = db.query(BatchJob).filter(BatchJob.status == "queued").all()
        for job in queued_jobs:
            job.status = "cancelled"
            job.completed_at = datetime.now(timezone.utc)
        db.commit()
        return {"cancelled": [str(j.id) for j in queued_jobs]}
    finally:
        db.close()


@router.post("/{batch_job_id}/retry")
async def retry_batch_job(batch_job_id: str):
    """Re-queue the same BatchJob row (not a new one) so its next promotion re-runs
    only what hasn't succeeded yet - see build_run_input_csv in
    batch_analysis_service_quant.py for the actual diff logic, invoked uniformly by
    run_batch_job.py when this row is picked up again."""
    db = SessionLocal()
    try:
        job = db.query(BatchJob).filter(BatchJob.id == batch_job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Batch job not found")
        if job.status in ("running", "queued"):
            raise HTTPException(status_code=400, detail=f"Cannot retry a job that is {job.status}")

        job.status = "queued"
        job.pid = None
        job.completed_at = None
        db.commit()

        _promote_queued_jobs(db)
        return {"batch_job_id": batch_job_id, "status": job.status}
    finally:
        db.close()


@router.get("/settings/concurrency-limit")
async def get_concurrency_limit():
    db = SessionLocal()
    try:
        return {"limit": _get_concurrency_limit(db)}
    finally:
        db.close()


@router.put("/settings/concurrency-limit")
async def set_concurrency_limit(request: ConcurrencyLimitRequest):
    if request.limit < 1:
        raise HTTPException(status_code=400, detail="Concurrency limit must be at least 1")
    db = SessionLocal()
    try:
        settings = db.query(BatchSettings).filter(BatchSettings.id == 1).first()
        if not settings:
            settings = BatchSettings(id=1, concurrency_limit=request.limit)
            db.add(settings)
        else:
            settings.concurrency_limit = request.limit
        db.commit()
        _promote_queued_jobs(db)
        return {"limit": request.limit}
    finally:
        db.close()
