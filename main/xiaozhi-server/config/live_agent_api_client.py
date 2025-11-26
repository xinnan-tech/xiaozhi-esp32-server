"""
Live Agent API Client - Singleton HTTP client for live-agent-api

Features:
1. Singleton pattern ensures global unique httpx.Client instance
2. Connection pool reuse for better performance
3. Thread-safe for concurrent requests
"""

import os
import httpx
from config.logger import setup_logging
from typing import Optional, List, Dict

logger = setup_logging()


class LiveAgentApiClient:
    """Singleton HTTP client for live-agent-api"""
    _instance = None
    _client: httpx.Client = None
    _base_url: str = None
    
    def __new__(cls, config: dict = None):
        """Singleton pattern ensures global unique instance"""
        if cls._instance is None:
            if config is None:
                raise ValueError("Config required for first initialization")
            cls._instance = super().__new__(cls)
            cls._init_client(config)
        return cls._instance
    
    @classmethod
    def _init_client(cls, config: dict):
        """Initialize persistent connection pool"""
        live_api_config = config.get("live-agent-api", {})
        cls._base_url = live_api_config.get("url", "http://live-agent-api:8080/api/live_agent/v1")
        timeout = live_api_config.get("timeout", 30)
        
        cls._client = httpx.Client(
            base_url=cls._base_url,
            headers={
                "User-Agent": f"XiaozhiServer/1.0 (PID:{os.getpid()})",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )
        logger.info(f"LiveAgentApiClient initialized: {cls._base_url}")
    
    @classmethod
    def _request(cls, method: str, endpoint: str, **kwargs) -> dict:
        """Send HTTP request and handle response"""
        endpoint = endpoint.lstrip("/")
        response = cls._client.request(method, endpoint, **kwargs)
        response.raise_for_status()
        return response.json()
    
    @classmethod
    def safe_close(cls):
        """Safely close connection pool"""
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._instance = None
            logger.info("LiveAgentApiClient closed")


def init_live_agent_api(config: dict):
    """Initialize the singleton client (call once at startup)"""
    LiveAgentApiClient(config)


def get_agent_config_from_api(agent_id: str, config: dict = None) -> Optional[dict]:
    """
    Get agent configuration from live-agent-api
    
    Args:
        agent_id: Agent ID
        config: System config (optional if client already initialized)
    
    Returns:
        Agent config dict or None if failed
    """
    try:
        # Ensure client is initialized
        if LiveAgentApiClient._instance is None:
            if config is None:
                logger.error("LiveAgentApiClient not initialized and no config provided")
                return None
            LiveAgentApiClient(config)
        
        result = LiveAgentApiClient._request("GET", f"/internal/agents/{agent_id}/config")
        
        if result.get("code") == 200 and "data" in result:
            logger.info(f"Successfully fetched agent config for agent_id={agent_id}")
            return result["data"]
        else:
            logger.error(f"Invalid response format from live-agent-api: {result}")
            return None
            
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.error(f"Agent not found: agent_id={agent_id}")
        else:
            logger.error(f"HTTP error fetching agent config: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to fetch agent config for {agent_id}: {e}")
        return None


def report_chat_message(
    agent_id: str,
    role: int,
    content_items: List[Dict[str, str]],
    config: dict = None
) -> Optional[dict]:
    """
    Report chat message to live-agent-api
    
    Args:
        agent_id: Agent ID
        role: 1=user, 2=agent
        content_items: List of message parts, format:
            [
                {"message_type": "text", "message_content": "Hello"},
                {"message_type": "audio", "message_content": "base64_opus_data"},
                {"message_type": "image", "message_content": "s3_url"},
                {"message_type": "file", "message_content": "s3_url"}
            ]
        config: System config (optional if client already initialized)
    
    Returns:
        Response dict or None if failed
    """
    try:
        # Ensure client is initialized
        if LiveAgentApiClient._instance is None:
            if config is None:
                logger.error("LiveAgentApiClient not initialized and no config provided")
                return None
            LiveAgentApiClient(config)
        
        payload = {
            "agent_id": agent_id,
            "role": role,
            "content": content_items
        }
        
        result = LiveAgentApiClient._request("POST", "/chat/report", json=payload)
        
        if result.get("code") == 200:
            logger.debug(f"Successfully reported message for agent_id={agent_id}, role={role}")
            return result.get("data")
        else:
            logger.error(f"Failed to report message: {result}")
            return None
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error reporting message: {e}, response: {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Failed to report message for {agent_id}: {e}")
        return None


def live_agent_api_safe_close():
    """Safe close for shutdown"""
    LiveAgentApiClient.safe_close()
