#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="/home/spc/Desktop/spctekai-backend"
cd "$APP_DIR"

LOG_DIR="$APP_DIR/logs"
DEPLOYMENT_LOG="$LOG_DIR/deployment.log"
ERROR_LOG="$LOG_DIR/deployment_errors.log"
STATUS_FILE="$LOG_DIR/deployment_status.json"
LOCK_FILE="$LOG_DIR/deployment.lock"

mkdir -p "$LOG_DIR"

exec >> "$DEPLOYMENT_LOG" 2>&1

DEPLOY_TIME=$(date +"%Y-%m-%d %H:%M:%S")

write_status() {
    local status="$1"
    local step="${2:-}"
    local message="${3:-}"

    cat > "$STATUS_FILE.tmp" <<EOF
{
  "status": "$status",
  "last_run": "$DEPLOY_TIME",
  "step": "$step",
  "message": "$message",
  "updated_at": "$(date +"%Y-%m-%d %H:%M:%S")"
}
EOF

    mv "$STATUS_FILE.tmp" "$STATUS_FILE"
}

log_error() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") ERROR $1" >> "$ERROR_LOG"
}

on_error() {
    local exit_code="$1"
    local line_number="$2"
    local message="Deployment failed at line ${line_number} with exit code ${exit_code}"

    log_error "$message"
    write_status "failed" "error" "$message"
}

trap 'on_error "$?" "$LINENO"' ERR

# Prevent multiple deployments running at the same time.
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    write_status "failed" "locked" "Another deployment is already running"
    exit 1
fi

echo "========================================"
echo "Starting deployment at $DEPLOY_TIME"
echo "========================================"

# Clear old error log for this run.
: > "$ERROR_LOG"

write_status "running" "start" "Deployment started"

# Prevent chmod/file mode churn from showing up as Git changes.
git config core.fileMode false

write_status "running" "git_fetch" "Fetching latest code from GitHub"
git fetch origin main

write_status "running" "git_reset" "Force syncing server code with origin/main"
git reset --hard origin/main

write_status "running" "git_clean" "Cleaning untracked files except protected files"
git clean -fd -e logs/ -e venv/ -e .env

write_status "running" "dependencies" "Installing Python dependencies"
./venv/bin/pip install -r requirements.txt

write_status "running" "pm2_restart" "Restarting backend with PM2"
timeout 60s pm2 restart spctekai-backend --update-env

write_status "running" "pm2_status" "Checking PM2 status"
pm2 status

write_status "success" "complete" "Deployment completed successfully"

echo "Deployment completed successfully at $(date +"%Y-%m-%d %H:%M:%S")"
