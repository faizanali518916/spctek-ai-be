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
    Deployment webhook endpoint.
    Requires correct DEPLOY_PASSWORD to execute deployment commands.
    """
    # Get the deployment password from environment variable
    deploy_password = settings.DEPLOY_PASSWORD

    if not deploy_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DEPLOY_PASSWORD environment variable not set",
        )

    # Verify the password
    if request.password != deploy_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid deployment password",
        )

    # Define deployment commands
    commands = ["git pull origin main", "venv/bin/pip install -r requirements.txt"]

    # Set the working directory
    cwd = "/home/spc/Desktop/spctekai-backend"

    results = []

    for command in commands:
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                text=True,
                shell=True,
                timeout=300,
                capture_output=True,
            )

            results.append(
                {
                    "command": command,
                    "returncode": result.returncode,
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )

            # If any command fails, return early with failure status
            if result.returncode != 0:
                return {
                    "success": False,
                    "message": f"Deployment failed at command: {command}",
                    "results": results,
                }

        except subprocess.TimeoutExpired:
            results.append(
                {
                    "command": command,
                    "success": False,
                    "error": "Command timed out (exceeded 5 minutes)",
                }
            )
            return {
                "success": False,
                "message": f"Deployment failed - command timed out: {command}",
                "results": results,
            }
        except Exception as e:
            results.append(
                {
                    "command": command,
                    "success": False,
                    "error": str(e),
                }
            )
            return {
                "success": False,
                "message": f"Deployment failed with error: {str(e)}",
                "results": results,
            }

    return {
        "success": True,
        "message": "Deployment completed successfully",
        "results": results,
    }
