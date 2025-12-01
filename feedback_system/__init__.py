"""
Feedback System Package

This package manages user negative feedback (dislikes) and integrates it
into the recommendation model for continuous learning and improvement.

Modules:
- feedback_handler: Manage dislike records and feedback storage
- feedback_reinforcement: Integrate feedback into model training
- feedback_api: Flask API endpoints for frontend integration

Usage:
    from feedback_system import save_dislike, get_dislike_pattern_analysis
    from feedback_system import register_feedback_routes
"""

from .feedback_handler import (
    save_dislike,
    get_user_dislikes,
    get_user_disliked_movies,
    calculate_dislike_weight,
    get_dislike_pattern_analysis,
    record_feedback_impact,
    get_model_feedback_metrics,
    init_feedback_tables,
    DislikeReason
)

from .feedback_reinforcement import (
    apply_dislike_to_training_data,
    calculate_feature_adjustment_from_dislike,
    get_untrained_negative_feedback_count,
    should_retrain_from_feedback,
    mark_negative_examples_as_used,
    get_negative_training_batch,
    apply_feature_adjustments,
    get_feedback_improvement_metrics
)

from .feedback_api import register_feedback_routes

__all__ = [
    # Handler functions
    'save_dislike',
    'get_user_dislikes',
    'get_user_disliked_movies',
    'calculate_dislike_weight',
    'get_dislike_pattern_analysis',
    'record_feedback_impact',
    'get_model_feedback_metrics',
    'init_feedback_tables',
    'DislikeReason',
    
    # Reinforcement functions
    'apply_dislike_to_training_data',
    'calculate_feature_adjustment_from_dislike',
    'get_untrained_negative_feedback_count',
    'should_retrain_from_feedback',
    'mark_negative_examples_as_used',
    'get_negative_training_batch',
    'apply_feature_adjustments',
    'get_feedback_improvement_metrics',
    
    # API registration
    'register_feedback_routes'
]

__version__ = '1.0.0'
__author__ = 'MovieNight Team'
