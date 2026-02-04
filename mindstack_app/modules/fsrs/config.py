from typing import Any
from fsrs_rs_python import DEFAULT_PARAMETERS

class DefaultConfig:
    """Default configuration for FSRS module."""
    FSRS_DESIRED_RETENTION = 0.9
    FSRS_ROLLING_WINDOW = 30  # Days to look back for optimization
    FSRS_MAX_INTERVAL = 365  # Days
    FSRS_ENABLE_FUZZING = True
    FSRS_ENABLE_FUZZ = True # Legacy alias
    FSRS_GLOBAL_WEIGHTS = list(DEFAULT_PARAMETERS)

# Backward compatibility alias
FSRSDefaultConfig = DefaultConfig