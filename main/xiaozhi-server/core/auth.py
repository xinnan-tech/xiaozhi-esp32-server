from config.logger import setup_logging

TAG = __name__

logger = setup_logging()

class AuthenticationError(Exception):
    """Authentication exception"""
    pass

class AuthMiddleware:
    def __init__(self, config):
        self.config = config
        self.auth_config = config["server"].get("auth", {})
        
        # Build token lookup table
        self.tokens = {
            item["token"]: item["name"]
            for item in self.auth_config.get("tokens", [])
        }
        
        # Device whitelist
        self.allowed_devices = set(
            self.auth_config.get("allowed_devices", [])
        )
    
    async def authenticate(self, headers):
        """Verify connection request"""
        # Check if authentication is enabled
        if not self.auth_config.get("enabled", False):
            return True
        
        # Check if device is in whitelist
        device_id = headers.get("device-id", "")
        if self.allowed_devices and device_id in self.allowed_devices:
            return True
        
        # Verify Authorization header
        auth_header = headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.bind(tag=TAG).error("Missing or invalid Authorization header")
            raise AuthenticationError("Missing or invalid Authorization header")
        
        token = auth_header.split(" ")[1]
        if token not in self.tokens:
            logger.bind(tag=TAG).error(f"Invalid token: {token}")
            raise AuthenticationError("Invalid token")
        
        logger.bind(tag=TAG).info(f"Authentication successful - Device: {device_id}, Token: {self.tokens[token]}")
        return True
    
    def get_token_name(self, token):
        """Get device name corresponding to token"""
        return self.tokens.get(token)