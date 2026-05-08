#!/bin/bash

cd /home/spc/Desktop/spctekai-backend

git pull origin main

./venv/bin/pip install -r requirements.txt

(sleep 2 && pm2 restart spctekai-backend) &