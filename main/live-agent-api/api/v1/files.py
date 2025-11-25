"""
File upload API endpoints (for App only)
"""
from fastapi import APIRouter, File, UploadFile, Depends, Header
from typing import Optional

from infra import get_s3
from repositories import FileRepository
from utils.response import success_response
from api.auth import get_current_user_id

router = APIRouter()


@router.post("/upload", summary="Upload file to S3 (App only)")
async def upload_file(
    file: UploadFile = File(..., description="File to upload (image, PDF, etc.)"),
    agent_id: Optional[str] = Header(None, alias="Agent-Id", description="Agent ID (optional)"),
    current_user_id: str = Depends(get_current_user_id),  # 需要用户认证
    s3 = Depends(get_s3)
):
    """
    Upload file to S3 storage (for App clients only)
    
    Headers:
        - Authorization: Bearer <token> (required)
        - Agent-Id: <agent_id> (optional, for organizing files by agent)
    
    Returns:
        - url: Public URL of uploaded file
        - filename: Original filename
        - size: File size in bytes
    
    Example:
        POST /api/live_agent/v1/files/upload
        Headers:
            Authorization: Bearer eyJhbGc...
            Agent-Id: agent_01JD8X0000ABC
        Body:
            file: [binary data]
    """
    # 根据 agent_id 组织文件夹结构
    if agent_id:
        folder = f"vision/users/{current_user_id}/agents/{agent_id}"
    else:
        folder = f"vision/users/{current_user_id}"
    
    # Upload to S3 using FileRepository
    file_url = await FileRepository.upload(
        s3=s3,
        file=file,
        folder=folder
    )
    
    # 获取文件大小
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
