"""
FSRS Optimizer Service

Trains user-specific FSRS parameters from their ReviewLog history.
Uses fsrs-rs-python's compute_parameters() method.
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fsrs_rs_python import FSRS, FSRSItem, FSRSReview, DEFAULT_PARAMETERS


class FsrsOptimizerService:
    """
    Service to optimize FSRS parameters for individual users.
    
    Usage:
        # Train parameters from user's review history
        params = FsrsOptimizerService.train_for_user(user_id=1)
        
        # Use optimized parameters
        engine = HybridFSRSEngine(custom_weights=params)
    """
    
    # Minimum reviews required to train parameters
    MIN_REVIEWS_FOR_TRAINING = 100
    
    @classmethod
    def train_for_user(cls, user_id: int, save_to_db: bool = True) -> Optional[List[float]]:
        """
        Train FSRS parameters from a user's ReviewLog history.
        
        Args:
            user_id: User ID to train for
            save_to_db: Whether to save parameters to user.fsrs_parameters
            
        Returns:
            List of 19 optimized parameters, or None if not enough data
        """
        from mindstack_app.models import ReviewLog, User, db
        
        # 1. Query all reviews for this user, grouped by item
        reviews_by_item = cls._get_reviews_by_item(user_id)
        
        if not reviews_by_item:
            return None
            
        # 2. Check minimum data requirement
        total_reviews = sum(len(revs) for revs in reviews_by_item.values())
        if total_reviews < cls.MIN_REVIEWS_FOR_TRAINING:
            return None
            
        # 3. Convert to FSRSItem format
        train_set = cls._convert_to_fsrs_items(reviews_by_item)
        
        if not train_set:
            return None
            
        # 4. Train parameters using fsrs-rs-python
        try:
            fsrs = FSRS(parameters=list(DEFAULT_PARAMETERS))
            optimized_params = fsrs.compute_parameters(train_set)
            params_list = list(optimized_params)
        except Exception as e:
            print(f"[FsrsOptimizer] Training failed: {e}")
            return None
            
        # 5. Save to database if requested
        if save_to_db:
            try:
                user = User.query.get(user_id)
                if user:
                    user.fsrs_parameters = params_list
                    db.session.commit()
            except Exception as e:
                print(f"[FsrsOptimizer] Failed to save params: {e}")
                
        return params_list
    
    @classmethod
    def get_user_parameters(cls, user_id: int) -> List[float]:
        """
        Get FSRS parameters for a user.
        Returns user's optimized params or default if not available.
        """
        from mindstack_app.models import User
        
        try:
            user = User.query.get(user_id)
            if user and user.fsrs_parameters:
                return list(user.fsrs_parameters)
        except Exception:
            pass
            
        return list(DEFAULT_PARAMETERS)
    
    @staticmethod
    def _get_reviews_by_item(user_id: int) -> Dict[int, List[Dict]]:
        """Query ReviewLog and group by item_id."""
        from mindstack_app.models import ReviewLog
        
        reviews = ReviewLog.query.filter_by(user_id=user_id)\
            .order_by(ReviewLog.item_id, ReviewLog.timestamp)\
            .all()
            
        grouped = {}
        for log in reviews:
            item_id = log.item_id
            if item_id not in grouped:
                grouped[item_id] = []
            grouped[item_id].append({
                'timestamp': log.timestamp,
                'rating': log.rating,
                'interval': log.interval
            })
            
        return grouped
    
    @staticmethod
    def _convert_to_fsrs_items(reviews_by_item: Dict[int, List[Dict]]) -> List[FSRSItem]:
        """
        Convert review history to FSRSItem format for training.
        
        FSRSItem expects:
        - reviews: list of FSRSReview(rating: 1-4, delta_t: int days)
        """
        items = []
        
        for item_id, reviews in reviews_by_item.items():
            if len(reviews) < 2:
                # Need at least 2 reviews to calculate delta_t
                continue
                
            fsrs_reviews = []
            prev_timestamp = None
            
            for rev in reviews:
                # Map rating: our 0-5 -> FSRS 1-4
                # 0-1 -> Again(1), 2 -> Hard(2), 3 -> Good(3), 4-5 -> Easy(4)
                raw_rating = rev['rating']
                if raw_rating <= 1:
                    fsrs_rating = 1
                elif raw_rating == 2:
                    fsrs_rating = 2
                elif raw_rating == 3:
                    fsrs_rating = 3
                else:
                    fsrs_rating = 4
                
                # Calculate delta_t (days since last review)
                if prev_timestamp:
                    delta_days = (rev['timestamp'] - prev_timestamp).days
                    delta_t = max(0, delta_days)
                else:
                    delta_t = 0  # First review
                    
                fsrs_reviews.append(FSRSReview(fsrs_rating, delta_t))
                prev_timestamp = rev['timestamp']
            
            if len(fsrs_reviews) >= 2:
                items.append(FSRSItem(reviews=fsrs_reviews))
                
        return items
    
    @classmethod
    def get_training_stats(cls, user_id: int) -> Dict[str, Any]:
        """
        Get statistics about user's review data for training.
        
        Returns:
            Dict with review counts, item counts, and training eligibility
        """
        reviews_by_item = cls._get_reviews_by_item(user_id)
        
        total_reviews = sum(len(revs) for revs in reviews_by_item.values())
        total_items = len(reviews_by_item)
        items_with_multiple = sum(1 for revs in reviews_by_item.values() if len(revs) >= 2)
        
        return {
            'total_reviews': total_reviews,
            'total_items': total_items,
            'items_with_multiple_reviews': items_with_multiple,
            'min_reviews_required': cls.MIN_REVIEWS_FOR_TRAINING,
            'can_train': total_reviews >= cls.MIN_REVIEWS_FOR_TRAINING,
            'reviews_needed': max(0, cls.MIN_REVIEWS_FOR_TRAINING - total_reviews)
        }
