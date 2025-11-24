
import httpx
from config.logger import setup_logging
from typing import Optional

logger = setup_logging()

def get_agent_config_from_api(agent_id: str, config: dict) -> Optional[dict]:
    """
    Get agent configuration from live-agent-api
    
    Args:
        agent_id: Agent ID
        config: System config containing live-agent-api URL
    
    Returns:
        Agent config dict or None if failed
    """
    
    live_api_config = config.get("live-agent-api", {})
    base_url = live_api_config.get("url", "http://live-agent-api:8080/api/live_agent/v1")
    timeout = live_api_config.get("timeout", 10)
    
    url = f"{base_url}/internal/agents/{agent_id}/config"
    
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request("GET", url)
            response.raise_for_status()
            result = response.json()
            
            # Extract data from success_response format
            if result.get("code") == 200 and "data" in result:
                agent_config = result["data"]
                logger.info(f"Successfully fetched agent config for agent_id={agent_id}")
                return agent_config
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