# modules/fsrs/config.py

try:
    from fsrs_rs_python import DEFAULT_PARAMETERS
except ImportError:
    # Fallback if library missing
    DEFAULT_PARAMETERS = [0.4, 0.6, 2.4, 5.8, 4.93, 0.94, 0.86, 0.01, 1.49, 0.14, 0.94, 2.18, 0.05, 0.34, 1.26, 0.29, 2.61, 0.25, 1.0]

class FSRSDefaultConfig:
    FSRS_DESIRED_RETENTION = 0.90
    FSRS_MAX_INTERVAL = 36500
    FSRS_ENABLE_FUZZ = False
    FSRS_GLOBAL_WEIGHTS = list(DEFAULT_PARAMETERS)
