#!/bin/bash

# Navigate to the backend directory
cd /home/spc/Desktop/spctekai-backend

set -Eeuo pipefail

LOG_DIR="logs"
DEPLOYMENT_LOG="$LOG_DIR/deployment.log"
ERROR_LOG="$LOG_DIR/deployment_errors.log"
STATUS_FILE="$LOG_DIR/deployment_status.json"

mkdir -p "$LOG_DIR"
exec >> "$DEPLOYMENT_LOG" 2>&1
DEPLOY_TIME=$(date +"%Y-%m-%d %H:%M:%S")
rm -f "$STATUS_FILE"

write_status() {
    local status="$1"
    cat > "$STATUS_FILE" <<EOF
{
  "status": "$status",
  "last_run": "$DEPLOY_TIME"
}
EOF
}

log_error() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") ERROR $1" >> "$ERROR_LOG"
}

on_error() {
    local exit_code="$1"
    local line_number="$2"
    log_error "Deployment failed at line ${line_number} with exit code ${exit_code}"
    write_status "failed"
}

trap 'on_error "$?" "$LINENO"' ERR

write_status "running"

# Set latest
git fetch origin main
git reset --hard origin/main

# Install dependencies
./venv/bin/pip install -r requirements.txt

# Restart via PM2
pm2 restart spctekai-backend

# Record successful deployment status
write_status "success"
