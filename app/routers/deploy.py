import json
import os
import subprocess
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/deploy", tags=["Deployment"])
PROJECT_DIR = "/home/spc/Desktop/spctekai-backend"
LOG_DIR = os.path.join(PROJECT_DIR, "logs")
DEPLOYMENT_LOG = os.path.join(LOG_DIR, "deployment.log")
DEPLOYMENT_ERROR_LOG = os.path.join(LOG_DIR, "deployment_errors.log")
DEPLOYMENT_STATUS_FILE = os.path.join(LOG_DIR, "deployment_status.json")


class DeployRequest(BaseModel):
    password: str


def log_deployment_error(message: str) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DEPLOYMENT_ERROR_LOG, "a", encoding="utf-8") as log_file:
        log_file.write(f"{timestamp} ERROR {message}\n")


def read_json_file(path: str) -> dict | None:
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as status_file:
        return json.load(status_file)


def read_recent_log_lines(path: str, limit: int = 50) -> list[str]:
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8", errors="replace") as log_file:
        return [line.rstrip("\n") for line in log_file.readlines()[-limit:]]


def parse_deployment_error(line: str) -> dict[str, str | None]:
    if not line:
        return {"timestamp": None, "level": None, "message": None}

    parts = line.split(" ", 3)
    if len(parts) == 4 and parts[2] == "ERROR":
        return {"timestamp": f"{parts[0]} {parts[1]}", "level": parts[2], "message": parts[3]}

    return {"timestamp": None, "level": None, "message": line}


def is_error_line(line: str) -> bool:
    parts = line.split(" ", 3)
    return len(parts) == 4 and parts[2] == "ERROR"


@router.get("/status")
async def deployment_status():
    """
    Returns the latest deployment status by reading files in the logs directory.
    """
    status_data = read_json_file(DEPLOYMENT_STATUS_FILE)
    recent_log = read_recent_log_lines(DEPLOYMENT_LOG)
    recent_error_lines = [line for line in read_recent_log_lines(DEPLOYMENT_ERROR_LOG) if is_error_line(line)]
    last_error = parse_deployment_error(recent_error_lines[-1]) if recent_error_lines else None

    if status_data and status_data.get("status") in {"running", "success"}:
        last_error = None

    log_files = []
    if os.path.isdir(LOG_DIR):
        for name in sorted(os.listdir(LOG_DIR)):
            path = os.path.join(LOG_DIR, name)
            if os.path.isfile(path):
                stat_result = os.stat(path)
                log_files.append(
                    {
                        "name": name,
                        "path": path,
                        "size_bytes": stat_result.st_size,
                        "modified_at": datetime.fromtimestamp(stat_result.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

    if status_data:
        current_status = status_data.get("status", "unknown")
        last_run = status_data.get("last_run")
    elif last_error:
        current_status = "failed"
        last_run = last_error.get("timestamp")
    else:
        current_status = "unknown"
        last_run = None

    return {
        "status": current_status,
        "last_run": last_run,
        "deployment": status_data,
        "last_success": status_data if current_status == "success" else None,
        "last_error": last_error,
        "recent_errors": recent_error_lines,
        "recent_log": recent_log,
        "logs_directory": LOG_DIR,
        "logs_directory_exists": os.path.isdir(LOG_DIR),
        "files": log_files,
    }


@router.post("")
async def deploy(request: DeployRequest):
    """
    Triggers the update.sh script in a fully detached background process.
    """
    deploy_password = settings.DEPLOY_PASSWORD

    if not deploy_password:
        log_deployment_error("DEPLOY_PASSWORD environment variable not set")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DEPLOY_PASSWORD environment variable not set",
        )

    if request.password != deploy_password:
        log_deployment_error("Invalid deployment password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid deployment password",
        )

    script_path = os.path.join(PROJECT_DIR, "update.sh")

    if not os.path.exists(script_path):
        log_deployment_error(f"update.sh not found at {script_path}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"update.sh not found at {script_path}",
        )

    try:
        os.makedirs(LOG_DIR, exist_ok=True)

        subprocess.Popen(
            ["bash", script_path],
            cwd=PROJECT_DIR,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )

        # 4. Return immediate success response before the server restarts
        return {
            "success": True,
            "message": "Deployment started in background.",
        }

    except Exception as e:
        log_deployment_error(f"Failed to initiate deployment script: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to initiate deployment script: {str(e)}"
        )
