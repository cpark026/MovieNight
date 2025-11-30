"""
API Handlers for Feedback System

This module provides Flask API endpoints for handling user feedback (dislikes)
and integrating it with the recommendation model.

Endpoints:
- POST /api/dislike: Record a user dislike
- GET /api/dislike-history: Get user's dislike history
- GET /api/dislike-patterns: Analyze user's dislike patterns
- GET /api/feedback-metrics: Get feedback improvement metrics
"""

from flask import request, jsonify
from typing import Tuple, Dict
import os

# These will be imported in app.py
def register_feedback_routes(app):
    """
    Register all feedback-related API routes with Flask app.
    
    Args:
        app: Flask application instance
    """
    
    @app.route('/api/dislike', methods=['POST'])
    def handle_dislike():
        """
        Record a user dislike for a movie recommendation.
        
        Expected JSON:
        {
            "movie_id": int (optional),
            "movie_title": str,
            "recommendation_set_id": int (optional),
            "predicted_score": float,
            "reason": str (wrong_genre, poor_quality, already_watched, not_interested),
            "feedback_text": str (optional)
        }
        
        Returns:
            JSON with dislike_id and impact analysis
        """
        try:
            from .feedback_handler import save_dislike, get_dislike_pattern_analysis
            from .feedback_reinforcement import (
                apply_dislike_to_training_data,
                calculate_feature_adjustment_from_dislike
            )
            from flask import session
            
            data = request.get_json()
            
            # Validate required fields
            if not data.get('movie_title'):
                return jsonify({'error': 'movie_title is required'}), 400
            
            # Get user ID from header or session
            user_id = request.headers.get('X-User-ID', type=int)
            if not user_id and 'user_id' in session:
                user_id = session.get('user_id')
            
            if not user_id:
                return jsonify({'error': 'Not authenticated'}), 401
            
            # Save the dislike
            dislike_id = save_dislike(
                user_id=user_id,
                movie_id=data.get('movie_id'),
                movie_title=data['movie_title'],
                recommendation_set_id=data.get('recommendation_set_id'),
                predicted_score=data.get('predicted_score', 0.0),
                reason=data.get('reason', 'not_interested'),
                feedback_text=data.get('feedback_text', '')
            )
            
            if dislike_id < 0:
                return jsonify({'error': 'Failed to save dislike'}), 500
            
            # Convert to training data
            training_data = apply_dislike_to_training_data(
                user_id=user_id,
                movie_id=data.get('movie_id'),
                movie_title=data['movie_title'],
                predicted_score=data.get('predicted_score', 0.0)
            )
            
            # Calculate feature adjustments
            movie_metadata = {
                'genres': data.get('genres', []),
                'cast': data.get('cast', [])
            }
            feature_adjustments = calculate_feature_adjustment_from_dislike(
                movie_metadata,
                reason=data.get('reason', 'not_interested')
            )
            
            # Get updated patterns
            patterns = get_dislike_pattern_analysis(user_id)
            
            return jsonify({
                'success': True,
                'dislike_id': dislike_id,
                'training_impact': {
                    'error_recorded': training_data.get('error', 0.0),
                    'weight': training_data.get('weight', 0.0)
                },
                'feature_adjustments': feature_adjustments,
                'user_patterns': patterns
            }), 201
        
        except Exception as e:
            print(f"[API ERROR] Error handling dislike: {e}")
            return jsonify({'error': str(e)}), 500
    
    
    @app.route('/api/dislike-history', methods=['GET'])
    def get_dislike_history():
        """
        Retrieve a user's dislike history.
        
        Query params:
            limit (int, default 50): Number of recent dislikes to retrieve
        
        Returns:
            JSON list of dislike records
        """
        try:
            from .feedback_handler import get_user_dislikes
            from flask import session
            
            # Get user ID from header or session
            user_id = request.headers.get('X-User-ID', type=int)
            if not user_id and 'user_id' in session:
                user_id = session.get('user_id')
            
            if not user_id:
                return jsonify({'error': 'Not authenticated'}), 401
            
            limit = request.args.get('limit', 50, type=int)
            dislikes = get_user_dislikes(user_id, limit=limit)
            
            return jsonify({
                'success': True,
                'count': len(dislikes),
                'dislikes': dislikes
            }), 200
        
        except Exception as e:
            print(f"[API ERROR] Error retrieving dislike history: {e}")
            return jsonify({'error': str(e)}), 500
    
    
    @app.route('/api/dislike-patterns', methods=['GET'])
    def get_patterns():
        """
        Analyze patterns in a user's dislikes.
        
        Returns:
            JSON with dislike pattern analysis
        """
        try:
            from .feedback_handler import get_dislike_pattern_analysis
            from flask import session
            
            # Get user ID from header or session
            user_id = request.headers.get('X-User-ID', type=int)
            if not user_id and 'user_id' in session:
                user_id = session.get('user_id')
            
            if not user_id:
                return jsonify({'error': 'Not authenticated'}), 401
            
            patterns = get_dislike_pattern_analysis(user_id)
            
            return jsonify({
                'success': True,
                'patterns': patterns
            }), 200
        
        except Exception as e:
            print(f"[API ERROR] Error analyzing patterns: {e}")
            return jsonify({'error': str(e)}), 500
    
    
    @app.route('/api/feedback-metrics', methods=['GET'])
    def get_metrics():
        """
        Get system-wide feedback improvement metrics.
        
        Returns:
            JSON with feedback metrics and improvement indicators
        """
        try:
            from .feedback_reinforcement import get_feedback_improvement_metrics
            # Import model_versioning from parent
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from model_versioning import get_active_model_version
            
            metrics = get_feedback_improvement_metrics()
            
            # Get active model version info
            active_version = get_active_model_version()
            
            return jsonify({
                'success': True,
                'metrics': metrics,
                'active_model_version': active_version
            }), 200
        
        except Exception as e:
            print(f"[API ERROR] Error getting feedback metrics: {e}")
            return jsonify({'error': str(e)}), 500
    
    
    print("[FEEDBACK] Feedback API routes registered successfully")
