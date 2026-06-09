#!/bin/bash

# Navigate to the backend directory
cd /home/spc/Desktop/spctekai-backend

set -Eeuo pipefail

LOG_DIR="logs"
ERROR_LOG="$LOG_DIR/deployment_errors.log"
STATUS_FILE="$LOG_DIR/deployment_status.json"

mkdir -p "$LOG_DIR"
exec 2>> "$ERROR_LOG"
rm -f "$STATUS_FILE"

log_error() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") ERROR $1" >> "$ERROR_LOG"
}

on_error() {
    local exit_code="$1"
    local line_number="$2"
    log_error "Deployment failed at line ${line_number} with exit code ${exit_code}"
}

trap 'on_error "$?" "$LINENO"' ERR

# Pull latest changes
git pull origin main

# Install dependencies
./venv/bin/pip install -r requirements.txt

# Generate the current timestamp (e.g., 2026-05-13 22:05:12)
DEPLOY_TIME=$(date +"%Y-%m-%d %H:%M:%S")

# Restart via PM2
pm2 restart spctekai-backend

# Record successful deployment status
cat > "$STATUS_FILE" <<EOF
{
  "status": "success",
  "last_run": "$DEPLOY_TIME"
}
EOF
