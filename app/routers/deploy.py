import os
import stat
import subprocess
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/deploy", tags=["Deployment"])


class DeployRequest(BaseModel):
    password: str


@router.post("")
async def deploy(request: DeployRequest):
    """
    Triggers the update.sh script and returns immediately.
    Ensures the script has executable permissions before running.
    """
    # 1. Verify Authentication
    deploy_password = settings.DEPLOY_PASSWORD

    if not deploy_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DEPLOY_PASSWORD environment variable not set",
        )

    if request.password != deploy_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid deployment password",
        )

    project_dir = "/home/spc/Desktop/spctekai-backend"
    script_path = os.path.join(project_dir, "update.sh")

    # 2. Automatically make update.sh executable (chmod +x)
    try:
        if os.path.exists(script_path):
            # Get current file permissions
            st = os.stat(script_path)
            # Add user, group, and other executable permissions (equivalent to +x)
            os.chmod(script_path, st.st_mode | stat.S_IEXEC)
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"update.sh not found at {script_path}",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set executable permissions on update.sh: {str(e)}",
        )

    # 3. Trigger the script in the background (Non-blocking)
    try:
        subprocess.Popen(
            ["bash", "./update.sh"],
            cwd=project_dir
        )
        
        # 4. Return immediate success response before the server restarts
        return {
            "success": True,
            "message": "Deployment initiated successfully. Server is pulling changes and restarting."
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate deployment script: {str(e)}"
        )