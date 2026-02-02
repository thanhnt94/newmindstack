# File: mindstack_app/modules/fsrs/services/optimizer_service.py
from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from flask import current_app
from fsrs_rs_python import FSRS, FSRSItem, FSRSReview, DEFAULT_PARAMETERS
from mindstack_app.models import User, db
from mindstack_app.modules.learning_history.models import StudyLog

class FSRSOptimizerService:
    """Service to optimize FSRS parameters for individual users."""
    
    MIN_REVIEWS_FOR_TRAINING = 100
    
    @classmethod
    def train_for_user(cls, user_id: int, save_to_db: bool = True) -> Optional[List[float]]:
        reviews_by_item = cls._get_reviews_by_item(user_id)
        if not reviews_by_item:
            return None
            
        total_reviews = sum(len(revs) for revs in reviews_by_item.values())
        if total_reviews < cls.MIN_REVIEWS_FOR_TRAINING:
            return None
            
        train_set = cls._convert_to_fsrs_items(reviews_by_item)
        if not train_set:
            return None
            
        try:
            fsrs = FSRS(parameters=list(DEFAULT_PARAMETERS))
            optimized_params = fsrs.compute_parameters(train_set)
            params_list = list(optimized_params)
        except Exception as e:
            current_app.logger.error(f"[FsrsOptimizer] Training failed for user {user_id}: {e}")
            return None
            
        if save_to_db:
            try:
                user = User.query.get(user_id)
                if user:
                    user.fsrs_parameters = params_list
                    db.session.commit()
            except Exception as e:
                current_app.logger.error(f"[FsrsOptimizer] Failed to save params for user {user_id}: {e}")
                
        return params_list
    
    @classmethod
    def get_user_parameters(cls, user_id: int) -> List[float]:
        try:
            user = User.query.get(user_id)
            if user and user.fsrs_parameters:
                return list(user.fsrs_parameters)
        except Exception:
            pass
        return list(DEFAULT_PARAMETERS)
    
    @staticmethod
    def _get_reviews_by_item(user_id: int) -> Dict[int, List[Dict]]:
        # Query StudyLog instead of ReviewLog
        reviews = StudyLog.query.filter_by(user_id=user_id)\
            .order_by(StudyLog.item_id, StudyLog.timestamp)\
            .all()
            
        grouped = {}
        for log in reviews:
            item_id = log.item_id
            if item_id not in grouped:
                grouped[item_id] = []
            
            # Extract interval from snapshot
            fsrs = log.fsrs_snapshot or {}
            interval = fsrs.get('scheduled_days', 0.0)
            
            grouped[item_id].append({
                'timestamp': log.timestamp,
                'rating': log.rating,
                'interval': interval
            })
        return grouped
    
    @staticmethod
    def _convert_to_fsrs_items(reviews_by_item: Dict[int, List[Dict]]) -> List[FSRSItem]:
        items = []
        for item_id, reviews in reviews_by_item.items():
            if len(reviews) < 2:
                continue
            fsrs_reviews = []
            prev_timestamp = None
            for rev in reviews:
                raw_rating = rev['rating']
                if raw_rating <= 1:
                    fsrs_rating = 1
                elif raw_rating == 2:
                    fsrs_rating = 2
                elif raw_rating == 3:
                    fsrs_rating = 3
                else:
                    fsrs_rating = 4
                
                if prev_timestamp:
                    delta_days = (rev['timestamp'] - prev_timestamp).days
                    delta_t = max(0, delta_days)
                else:
                    delta_t = 0
                fsrs_reviews.append(FSRSReview(fsrs_rating, delta_t))
                prev_timestamp = rev['timestamp']
            if len(fsrs_reviews) >= 2:
                items.append(FSRSItem(reviews=fsrs_reviews))
        return items