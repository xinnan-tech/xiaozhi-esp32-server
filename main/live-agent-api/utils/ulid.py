from ulid import ULID


def generate_user_id() -> str:
    """
    Generate unique user ID with 'user_' prefix and ULID
    
    Format: user_01JD8X0000ABC123DEF456GH (31 chars total)
    - Prefix: user_
    - ULID: 26 chars (128-bit unique, time-sortable)
    """
    return f"user_{ULID()}"


def generate_agent_id() -> str:
    """
    Generate unique agent ID with 'agent_' prefix and ULID
    
    Format: agent_01JD8X0000ABC123DEF456GH (32 chars total)
    - Prefix: agent_
    - ULID: 26 chars (128-bit unique, time-sortable)
    """
    return f"agent_{ULID()}"


def generate_template_id() -> str:
    """
    Generate unique template ID with 'template_' prefix and ULID
    
    Format: template_01JD8X0000ABC123DEF456GH (35 chars total)
    - Prefix: template_
    - ULID: 26 chars (128-bit unique, time-sortable)
    """
    return f"template_{ULID()}"


def generate_voice_id() -> str:
    """
    Generate unique voice ID with 'voice_' prefix and ULID
    
    Format: voice_01JD8X0000ABC123DEF456GH (32 chars total)
    - Prefix: voice_
    - ULID: 26 chars (128-bit unique, time-sortable)
    """
    return f"voice_{ULID()}"

