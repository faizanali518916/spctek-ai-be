#!/bin/bash

# Navigate to the backend directory
cd /home/spc/Desktop/spctekai-backend

# Pull latest changes
git pull origin main

# Install dependencies
./venv/bin/pip install -r requirements.txt

# Generate the current timestamp (e.g., 2026-05-13 22:05:12 PKT)
DEPLOY_TIME=$(date +"%Y-%m-%d %H:%M:%S %Z")

# Restart via PM2 and inject/update the environment variable
(sleep 2 && DEPLOYMENT_UPDATED_AT="$DEPLOY_TIME" pm2 restart spctekai-backend --update-env) &