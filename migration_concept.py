"""
FSRS v5 Migration Concept
"""

def migrate_item(item):
    """
    Migrate a legacy LearningProgress item to FSRS v5 Native.
    """
    # 1. Reset FSRS State
    # Default Difficulty (D) = 5.0 (Center of 1-10 scale)
    item.fsrs_difficulty = 5.0
    
    # Stability (S) = 0.0
    # Treating all cards as fresh for the new algorithm to re-learn patterns
    item.fsrs_stability = 0.0
    
    # 2. Migrate History to Lapses
    # Lapses are critical for FSRS (retrievability calc on failure).
    # Proxy: Use total incorrect count as lapses.
    item.lapses = item.times_incorrect
    
    # 3. State Mapping (String -> Int)
    # If legacy status exists, map it to int state.
    legacy_status_map = {
        'new': 0,        # STATE_NEW
        'learning': 1,   # STATE_LEARNING
        'reviewing': 2,  # STATE_REVIEW
        'relearning': 3, # STATE_RELEARNING
        'mastered': 2    # Treat mastered as Review
    }
    # (Assuming we have a way to access legacy status string)
    # item.fsrs_state = legacy_status_map.get(legacy_status_string, 0)
    
    # 4. Clear Legacy Fields (Optional)
    # item.easiness_factor = None # (If column still exists)
