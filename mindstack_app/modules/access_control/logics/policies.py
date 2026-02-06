from typing import Dict, Any, Union

# --- Constants: Roles ---
ROLE_ADMIN = 'admin'
ROLE_USER = 'user'   # Represents Premium/VIP
ROLE_FREE = 'free'
ROLE_ANONYMOUS = 'anonymous'

# --- Constants: Permission Keys ---
CAN_EXPORT_EXCEL = 'can_export_excel'
CAN_USE_FSRS = 'can_use_fsrs'
CAN_MANAGE_SYSTEM = 'can_manage_system'
CAN_CREATE_COURSE = 'can_create_course'

# --- Constants: Limit Keys ---
LIMIT_FLASHCARDS = 'limit_flashcards'
LIMIT_AI_REQUESTS_DAILY = 'limit_ai_requests_daily'

class PolicyValues:
    """Helper for infinite limits"""
    UNLIMITED = float('inf')

# --- Policy Matrix ---
ROLE_POLICIES: Dict[str, Dict[str, Any]] = {
    ROLE_ADMIN: {
        'permissions': {
            CAN_EXPORT_EXCEL: True,
            CAN_USE_FSRS: True,
            CAN_MANAGE_SYSTEM: True,
            CAN_CREATE_COURSE: True,
        },
        'limits': {
            LIMIT_FLASHCARDS: PolicyValues.UNLIMITED,
            LIMIT_AI_REQUESTS_DAILY: PolicyValues.UNLIMITED,
        }
    },
    ROLE_USER: {  # Premium
        'permissions': {
            CAN_EXPORT_EXCEL: True,
            CAN_USE_FSRS: True,
            CAN_MANAGE_SYSTEM: False,
            CAN_CREATE_COURSE: True,
        },
        'limits': {
            LIMIT_FLASHCARDS: 1000,
            LIMIT_AI_REQUESTS_DAILY: 100,
        }
    },
    ROLE_FREE: {
        'permissions': {
            CAN_EXPORT_EXCEL: False,
            CAN_USE_FSRS: False,  # Simple SRS only? Or just basic FSRS? Policy says "FSRS" is premium feature logic.
            CAN_MANAGE_SYSTEM: False,
            CAN_CREATE_COURSE: False,
        },
        'limits': {
            LIMIT_FLASHCARDS: 50,
            LIMIT_AI_REQUESTS_DAILY: 5,
        }
    },
    ROLE_ANONYMOUS: {
        'permissions': {
            CAN_EXPORT_EXCEL: False,
            CAN_USE_FSRS: False,
            CAN_MANAGE_SYSTEM: False,
            CAN_CREATE_COURSE: False,
        },
        'limits': {
            LIMIT_FLASHCARDS: 0,
            LIMIT_AI_REQUESTS_DAILY: 0,
        }
    }
}

def get_role_policy(role: str) -> Dict[str, Any]:
    """Retrieve policy for a specific role with fallback to FREE."""
    return ROLE_POLICIES.get(role, ROLE_POLICIES[ROLE_FREE])
