# Batch Analysis UI — Business Requirements

## Background

Batch analysis runs (`test_batch_analysis` / `batch_analysis_service_quant.BatchAnalysisService`) are currently triggered by SSH'ing into EC2 and running the script manually, or via a cron job. This has no UI visibility, no way to monitor progress remotely, and — as surfaced directly by an incident during this requirements process — a manually-launched run is killed outright if the triggering SSH session drops (SIGHUP), with no way to resume or even know it happened until someone checks.

This document defines requirements for a dedicated "Batch Analysis" page to replace that workflow, covering three capabilities: **Trigger**, **Monitor**, **Correct**.

Three separate batch implementations already exist in the codebase:
- `services/batch/batch_analysis_service.py`
- `services/batch/batch_analysis_service_quant.py` — used by `test_batch_analysis` and the cron job; the one this page targets.
- `api/batch_service.py` — powers `/batch/upload`, `/batch/{id}/status`, `/batch/{id}/results`, `/batch/jobs`. Fully built but **not called by any dashboard page today** — out of scope, not reused, to avoid running a second, less-exercised code path with potentially different Comparable/DCF behavior than what's already tuned for large runs.

A `BatchJob` DB model (`batch_jobs` table) already tracks `status`, `total_stocks`, `completed_stocks`, `failed_stocks`, `exchange`, `input_file`, `output_file`, `created_by`, `completed_at`. `AnalysisHistory` rows link back to it via `batch_job_id` (groups all stocks in one run) — distinct from `batch_analysis_id` (groups one stock's DCF/Comparable/Technical/etc. records within a single analysis).

## Access & Placement

- **Admin-only** — matches the existing role gate used by Stock Management.
- New "Batch Analysis" page under the **Main** nav group, alongside Live Analysis and Historical Analysis (not "Under Work Pages"). No planned relocation later — single user currently, so simplicity wins over anticipating a larger nav structure.

## Trigger

- Start a batch run for a selected input file from the UI.
- **File/exchange dropdown lists every `.csv` in `stock_dump/` directly** — no filtering or curation. All of them hold real tickers and are legitimate to run, including the smaller ones (`small.csv`, `single.csv`) which are specifically useful for testing this page without kicking off a full exchange run. This is a different (and simpler) source than the existing "Bulk Analysis" exchange dropdown under Historical Analysis, which is DB-derived from past `BatchJob.exchange` values and can't show an exchange that's never been run.
- Support running **multiple files/exchanges in sequence** in one request (the original NASDAQ → NYSE use case).
- Uses `batch_analysis_service_quant.BatchAnalysisService` — same behavior as `test_batch_analysis`/the cron job (config-only Comparable, no DCF preset scenarios, slim 5-analyzer set).
- **Thread count**: user-configurable, defaults to **2**.
- **Analyzer set**: fixed at today's defaults, not exposed as a UI option.
- **Concurrency limit**: configurable, defaults to **1** — caps how many batch jobs can be actively running at once.
- A trigger beyond the concurrency limit is **queued**, not rejected.
- **Architecture**: batch runs execute as an independent OS process (`subprocess.Popen`), not in-process inside the API/dashboard server. This is required for both durability (below) and cancellation (see Correct) — an in-process background task dies with its parent server process, which would break both. `BatchJob` gets a new `pid` column to track this.

## Monitor

- Runs must be **durable**: tracked server-side via `BatchJob`, surviving the browser tab closing or the admin's SSH/network connection dropping. The UI polls and displays current state; it does not need to stay open for the run to continue. This is the core problem this page exists to solve.
- Live progress while a run is active: completed/failed/remaining counts, ETA — sourced from `BatchJob`'s existing `completed_stocks`/`failed_stocks`/`total_stocks` fields, already updated during a run via `_update_batch_job_progress`.
- **Show queued jobs** — what's waiting, and in what order. Queue state is **DB-backed** (a `queued` value on `BatchJob.status`, not an in-memory list), so queued jobs also survive a server process restart, consistent with the durability requirement for running jobs. A lightweight poller promotes the oldest queued job to running when a concurrency slot frees up.
- Historical view of past runs on this page (start/end time, duration, success rate) — **always includes cancelled and failed runs**, unlike the existing Bulk Analysis view (see below). This page's job is to show the full picture of everything triggered from it.
- Failure detail visible directly in the UI — ticker / error_type / error_message, sourced from the CSV failure log — not just an aggregate failure count.

## Correct

- **Cancel** an in-progress batch job. No pause/resume — evaluated and explicitly descoped: the current architecture (synchronous `ThreadPoolExecutor` loop with no interrupt checkpoints) has no natural hook for true suspend/resume, and building one would conflict with the durability requirement (an in-process cooperative-cancellation flag can't survive a server restart the way a separate OS process + PID can).
  - **Implementation**: cancel sends `SIGTERM` to the job's persisted `pid` and immediately sets `BatchJob.status = 'cancelled'`. In-flight tickers are abandoned (their results are simply not produced); tickers already committed to `AnalysisHistory` before the kill remain valid data.
  - `'cancelled'` is a new, distinct status value — different from `'failed'` (unexpected error).
- **Remove a specific job from the queue**, or **clear the whole queue**.
- **Retry failed tickers from a run**, reusing the **same `batch_job_id`** as the original run — not a new batch job. Each retried stock gets its own fresh `batch_analysis_id` (per-stock, as normal), but rolls up under the original `BatchJob` row's counts and identity.
  - "Retry" also covers **resuming a cancelled run** — instead of only retrying failed tickers, it can also pick up tickers that were never processed at all before the cancel, giving the practical effect of resume without needing true pause/resume infrastructure.
- Editing the input ticker list is out of scope — that's just triggering a new run against a different CSV.
- Single-stock re-analysis stays in Live Analysis; out of scope here.

## Impact on Existing Code

Introducing `'cancelled'` as a status surfaces a real gap in two existing queries (`historical_analysis_service.py`), both currently filtered to `status.in_(['completed', 'running'])`:

- **`get_available_exchanges()`** (exchange-level dropdown, Bulk Analysis): stays as-is. A cancelled job's exchange correctly falls out of this rollup by default — incomplete results shouldn't count as "available analysis" for that exchange, unless another completed/running job exists for it.
- **`get_batch_jobs_by_exchange()`** (per-run list you drill into for results): needs a **"show cancelled jobs" toggle**, defaulting off (preserves today's view), switchable on so an admin can find and review a specific cancelled run's partial results — otherwise a cancelled job's results become permanently unreachable in the UI once cancelled.

## Out of Scope

- Reusing/wiring up `api/batch_service.py`'s existing `/batch/*` endpoints.
- True pause/resume (freeze mid-run, hold state, resume without re-processing) — see Correct.
- Configurable analyzer set per run.
- Editing the input ticker list from this page.
- Single-stock triggering/re-analysis (already covered by Live Analysis).
- Notifications (email/Slack/etc. on completion or failure) — not discussed, flag if wanted.
