# Prefect Worker Cycle Service (Railway Cron)

This folder defines a lightweight Railway service that runs the Prefect worker
cycle once and exits. Point a Railway Cron schedule at this service to drain
pending flow runs on-demand without keeping a long-lived worker online.

## Files

- `Dockerfile` – Builds a Python image, installs Prefect, and executes
  `prefect_worker_cycle.py`.
- `prefect_worker_cycle.py` – Resumes the work pool, optionally triggers
  deployments, starts a run-once worker, waits for active flow runs to finish,
  and (optionally) pauses the pool again.

## Expected Environment Variables

Set these variables in the Railway service before enabling the cron schedule:

- `PREFECT_API_URL` – Prefect API endpoint
- `PREFECT_API_KEY` *(optional)* – Required only when talking to Prefect Cloud
- `GITHUB_ACCESS_TOKEN` *(optional)* – Personal access token for cloning if the
  repository is private or to avoid GitHub rate limits
- `PREFECT_TRIGGER_DEPLOYMENTS` *(optional)* – Comma-separated list of
  deployment names to kick off before the worker starts
- `PREFECT_WORK_POOL` *(optional)* – Defaults to `default-agent-pool`
- `PREFECT_WORKER_NAME` *(optional)* – Worker name shown in Prefect UI/logs
- `PREFECT_WORKER_TYPE` *(optional)* – Worker type (`process`, `docker`, etc.)
- `PREFECT_WORKER_PREFETCH_SECONDS` *(optional)* – How far ahead to prefetch
- `PREFECT_WORKER_FLOW_LIMIT` *(optional)* - Max simultaneous flow runs
- `PREFECT_WORKER_RUN_FOREVER` *(optional, default `false`)* - When `true`,
  keeps the worker online until the container stops (no auto-pause)
- `PREFECT_WAIT_FOR_COMPLETION` *(optional, default `true`)* - Wait until the
  pool has no flow runs in active states before exiting
- `PREFECT_WAIT_TIMEOUT_SECONDS` *(optional)* – Give up waiting after this many
  seconds (0 = no timeout)
- `PREFECT_WAIT_POLL_SECONDS` *(optional)* – Poll interval while waiting
- `PREFECT_ACTIVE_STATE_TYPES` *(optional)* - Comma-separated flow-run state
  types to treat as "active" (defaults to `PENDING,RUNNING`)
- `PREFECT_AUTO_PAUSE` *(optional, default `true`)* - Pause the work pool once
  the cycle completes
- `PREFECT_WORKER_REPOSITORY` *(optional, default `https://github.com/monuit/truecivic.git`)* - Repository to preflight before starting the worker
- `PREFECT_WORKER_BRANCH` *(optional, default `main`)* - Branch to check during repository preflight
- `PREFECT_WORKER_VERIFY_REPOSITORY` *(optional, default `true`)* - Disable to skip the preflight git connectivity check
- `TRUECIVIC_CODE_DIR` *(optional, default `/opt/truecivic`)* - Directory where the worker syncs the codebase
- `TRUECIVIC_INSTALL_REQUIREMENTS` *(optional, default `true`)* - Install `requirements.txt` after syncing
- `TRUECIVIC_REQUIREMENTS_FILE` *(optional, default `requirements.txt`)* - Override the requirements file path
- `TRUECIVIC_INSTALL_EDITABLE` *(optional, default `false`)* - Install the project in editable mode (`pip install -e .`)

The script resumes the pool, launches a `--run-once` worker to drain scheduled
runs, waits for active runs to finish, and then (by default) pauses the pool so
no new work queues up while the cron job is idle. Set
`PREFECT_WORKER_RUN_FOREVER=true` (and optionally `PREFECT_AUTO_PAUSE=false`)
to run a 24/7 worker for testing; disable the cron schedule in that case and
deploy the service as a standard worker.
