from enum import Enum
from typing import Union, Optional


class InterfaceType(Enum):
    # Interface type
    STREAM = "STREAM"  # Streaming interface
    NON_STREAM = "NON_STREAM"  # Non-streaming interface
    LOCAL = "LOCAL"  # Local service
