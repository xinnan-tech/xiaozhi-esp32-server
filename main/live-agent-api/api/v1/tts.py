"""
TTS (Text-to-Speech) API endpoints
简单封装 Fish Audio TTS，供移动端/嵌入式设备调用
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

from infra.fishaudio import get_fish_audio
from config.logger import setup_logging

TAG = __name__
logger = setup_logging(TAG)

router = APIRouter()


class TTSSynthesizeRequest(BaseModel):
    """TTS 合成请求"""
    text: str  # 要合成的文本
    voice_id: Optional[str] = None  # 可选的音色 ID (Fish Audio voice reference_id)
    format: str = "mp3"  # 输出格式: mp3, wav, pcm


@router.post("/synthesize", summary="Text to Speech Synthesis")
async def synthesize_speech(
    request: TTSSynthesizeRequest,
    fish_client = Depends(get_fish_audio)
):
    """
    将文本合成为语音
    
    - **text**: 要合成的文本内容
    - **voice_id**: 可选，Fish Audio 音色 ID。不提供则使用默认音色
    - **format**: 输出格式，支持 mp3(默认), wav, pcm
    
    Returns:
        音频文件流 (audio/mpeg 或 audio/wav)
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    text = request.text.strip()
    
    # 限制文本长度（避免过长的请求）
    if len(text) > 1000:
        raise HTTPException(status_code=400, detail="Text too long, max 1000 characters")
    
    logger.bind(tag=TAG).info(f"TTS request: text='{text[:50]}...', voice_id={request.voice_id}, format={request.format}")
    
    try:
        # 调用 Fish Audio TTS
        audio_bytes = await fish_client.tts.convert(
            text=text,
            reference_id=request.voice_id,  # 可以为 None，使用默认音色
            format=request.format
        )
        
        logger.bind(tag=TAG).info(f"TTS success, audio size: {len(audio_bytes)} bytes")
        
        # 根据格式返回不同的 Content-Type
        content_type_map = {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "pcm": "audio/pcm"
        }
        content_type = content_type_map.get(request.format, "audio/mpeg")
        
        return Response(
            content=audio_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f"inline; filename=tts.{request.format}"
            }
        )
        
    except Exception as e:
        logger.bind(tag=TAG).error(f"TTS failed: {e}")
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")


@router.get("/health", summary="TTS Service Health Check")
async def tts_health(fish_client = Depends(get_fish_audio)):
    """
    检查 TTS 服务是否可用
    """
    try:
        # 简单检查 Fish Audio 客户端是否可用
        if fish_client is None:
            return {"status": "unavailable", "message": "Fish Audio client not initialized"}
        return {"status": "available", "message": "TTS service is ready"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
