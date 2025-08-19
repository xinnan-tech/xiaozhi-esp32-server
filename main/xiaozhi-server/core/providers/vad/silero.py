"""Silero Voice Activity Detection (VAD) provider.

This module provides the VAD implementation using either ONNX (production-ready)
or PyTorch models based on configuration.
"""

import os
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

# Try to import the ONNX implementation first
try:
    from core.providers.vad.silero_onnx import VADProvider as ONNXVADProvider
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logger.bind(tag=TAG).warning("ONNX runtime not available, falling back to PyTorch implementation")

# Import PyTorch implementation as fallback
if not ONNX_AVAILABLE:
    try:
        from core.providers.vad.silero_torch_backup import VADProvider as TorchVADProvider
    except ImportError:
        logger.bind(tag=TAG).error("Neither ONNX nor PyTorch VAD implementations are available")
        raise


class VADProvider:
    """Unified VAD provider that automatically selects the best implementation.
    
    Prefers ONNX for production use, falls back to PyTorch if ONNX is not available.
    """
    
    def __new__(cls, config):
        """Create appropriate VAD provider instance based on availability and config.
        
        Args:
            config: Configuration dictionary with VAD parameters
            
        Returns:
            Either ONNXVADProvider or TorchVADProvider instance
        """
        # Check if user explicitly requested PyTorch implementation
        use_torch = config.get("use_torch", False)
        
        # Determine which implementation to use
        if ONNX_AVAILABLE and not use_torch:
            logger.bind(tag=TAG).info("Using ONNX-based Silero VAD (production-ready)")
            
            # Set default ONNX model path if not provided
            if "model_path" not in config:
                # Check multiple possible locations for the ONNX model
                possible_paths = [
                    "models/snakers4_silero-vad/src/silero_vad/data/silero_vad.onnx",
                    "models/silero_vad.onnx",
                    os.path.join(config.get("model_dir", ""), "silero_vad.onnx") if "model_dir" in config else None
                ]
                
                for path in possible_paths:
                    if path and os.path.exists(path):
                        config["model_path"] = path
                        break
                else:
                    logger.bind(tag=TAG).warning("ONNX model not found in default locations, check model_path config")
            
            return ONNXVADProvider(config)
        else:
            logger.bind(tag=TAG).info("Using PyTorch-based Silero VAD")
            return TorchVADProvider(config)
