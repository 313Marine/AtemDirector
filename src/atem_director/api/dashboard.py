from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter()

@router.get("/")
async def dashboard():
    """Serve dashboard HTML."""
    template_path = os.path.join(os.path.dirname(__file__), "../../templates/dashboard.html")
    return FileResponse(template_path, media_type="text/html")
