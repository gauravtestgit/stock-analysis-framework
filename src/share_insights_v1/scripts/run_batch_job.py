#!/usr/bin/env python3
"""Thin CLI entry point spawned as a subprocess by the Batch Analysis UI
(src/share_insights_v1/api/batch_jobs.py's queue-promotion function) to actually run a
queued or retried BatchJob row.

Must be invoked as a module so its relative imports resolve, with cwd set to the repo
root (same constraint as tests/test_batch_analysis.py, which this intentionally does
NOT modify or replace - that script stays the CLI/cron entry point; this one is only
ever launched by the API layer, which always pre-creates the BatchJob row so a
--batch-job-id is always available here):

    python -m src.share_insights_v1.scripts.run_batch_job --batch-job-id <uuid> --threads <N>

Unlike test_batch_analysis.py (which always starts a fresh BatchJob from a full input
file), this script always resolves "what to run" via
BatchAnalysisService.build_run_input_csv - the diff between the job's original input
file and whatever's already succeeded under that batch_job_id. For a first-ever attempt
that's the whole file (nothing has succeeded yet); for a retry/resume it's just what's
left. Same code path either way - see build_run_input_csv's docstring.
"""

import argparse
import sys
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(description='Run (or retry/resume) a queued batch analysis job')
    parser.add_argument('--batch-job-id', required=True, help='Existing BatchJob row to attach this run to')
    parser.add_argument('--threads', '-t', type=int, default=2, help='Number of threads (default: 2)')
    args = parser.parse_args()

    from ..services.batch.batch_analysis_service_quant import BatchAnalysisService
    from ..models.database import SessionLocal
    from ..models.strategy_models import BatchJob

    db = SessionLocal()
    try:
        batch_job = db.query(BatchJob).filter(BatchJob.id == args.batch_job_id).first()
        if not batch_job:
            print(f"No BatchJob found for id={args.batch_job_id}", file=sys.stderr)
            sys.exit(1)
        exchange = batch_job.exchange
        output_csv_path = batch_job.output_file
        created_by = batch_job.created_by
    finally:
        db.close()

    service = BatchAnalysisService(save_to_db=True, enable_detailed_news_analysis=False, max_workers=args.threads)

    run_csv_path = service.build_run_input_csv(args.batch_job_id)

    if run_csv_path is None:
        # Every ticker in the original file already succeeded under this batch_job_id -
        # nothing left to do. This can happen on an explicit retry after everything
        # already passed, but also when a prior attempt's own progress-tracking crashed
        # or was killed *after* the underlying analyses actually completed (e.g.
        # ThreadPoolExecutor's context manager waits for already-submitted in-flight
        # work to finish even if the main thread errors out first) - so completed_stocks
        # on the row can be stale/wrong here and needs recomputing from the DB, not left
        # at whatever it was when this attempt started.
        print(f"Nothing left to run for batch job {args.batch_job_id} - marking completed.")
        from sqlalchemy import func
        from ..models.strategy_models import AnalysisHistory

        db = SessionLocal()
        try:
            batch_job = db.query(BatchJob).filter(BatchJob.id == args.batch_job_id).first()
            if batch_job:
                succeeded = (
                    db.query(func.count(func.distinct(AnalysisHistory.ticker)))
                    .filter(AnalysisHistory.batch_job_id == args.batch_job_id)
                    .scalar()
                ) or 0
                batch_job.completed_stocks = succeeded
                batch_job.failed_stocks = max((batch_job.total_stocks or 0) - succeeded, 0)
                batch_job.status = "completed"
                batch_job.completed_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()
        return

    print(f"Running batch job {args.batch_job_id} ({exchange}) with {args.threads} threads...")
    service.process_csv(
        input_csv_path=run_csv_path,
        output_csv_path=output_csv_path,
        exchange=exchange,
        created_by=created_by,
        existing_batch_job_id=args.batch_job_id,
    )


if __name__ == "__main__":
    main()
