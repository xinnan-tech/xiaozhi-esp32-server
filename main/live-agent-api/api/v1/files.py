"""
File upload API endpoints (for App only)
"""
from fastapi import APIRouter, File, UploadFile, Depends, Form, HTTPException

from infra import get_s3
from repositories import FileRepository
from utils.response import success_response
from api.auth import get_current_user_id

router = APIRouter()


@router.post("/upload", summary="Upload file to S3 (App only)")
async def upload_file(
    file: UploadFile = File(..., description="File to upload (image, PDF, etc.)"),
    agent_id: str = Form(..., description="Agent ID (required, for organizing files by agent)"),
    current_user_id: str = Depends(get_current_user_id),  # need user authentication
    s3 = Depends(get_s3)
):
    """
    Upload file to S3 storage (for App clients only)
    
    Headers:
        - Authorization: Bearer <token> (required)
    
    Form Data:
        - file: File to upload (required)
        - agent_id: Agent ID (required, for organizing files by agent)
    
    Returns:
        - url: Public URL of uploaded file
        - filename: Original filename
        - size: File size in bytes
    
    Example:
        POST /api/live_agent/v1/files/upload
        Headers:
            Authorization: Bearer eyJhbGc...
        Form Data:
            file: [binary data]
            agent_id: agent_01JD8X0000ABC
    """
    # Validate agent_id format (basic validation)
    if not agent_id or len(agent_id.strip()) == 0:
        raise HTTPException(status_code=400, detail="agent_id cannot be empty")
    
    folder = f"files/{agent_id}"
    
    # Upload to S3 using FileRepository
    name = file.filename.split('.')[0] if '.' in file.filename else file.filename
    file_url = await FileRepository.upload(
        s3=s3,
        file=file,
        folder=folder,
        custom_filename=name
    )
    
    # file size
    await file.seek(0)
    content = await file.read()
    file_size = len(content)
    
    return success_response(
        data={
            "url": file_url,
            "filename": file.filename,
            "size": file_size
        },
        message="File uploaded successfully"
    )
