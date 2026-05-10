"""
Authentication Middleware for Morphic Platform
Provides decorators and middleware for protecting routes
"""
from functools import wraps
from flask import request, jsonify
from services.auth_service import AuthService
from models.database import DatabaseManager


def init_auth_middleware(db_manager: DatabaseManager):
    """Initialize auth middleware with database manager"""
    auth_service = AuthService(db_manager)
    return auth_service


def require_auth(auth_service: AuthService):
    """Decorator to require authentication for a route"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({"error": "Missing or invalid authorization header"}), 401
            
            token = auth_header.split(' ')[1]
            payload = auth_service.decode_token(token)
            
            if not payload:
                return jsonify({"error": "Invalid or expired token"}), 401
            
            user_id = int(payload.get('sub'))
            user = auth_service.get_user_by_id(user_id)
            
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            if not user.is_active:
                return jsonify({"error": "User account is inactive"}), 403
            
            # Add user to request context
            request.current_user = user
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_admin(auth_service: AuthService):
    """Decorator to require admin role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({"error": "Missing or invalid authorization header"}), 401
            
            token = auth_header.split(' ')[1]
            payload = auth_service.decode_token(token)
            
            if not payload:
                return jsonify({"error": "Invalid or expired token"}), 401
            
            user_id = int(payload.get('sub'))
            user = auth_service.get_user_by_id(user_id)
            
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            if user.role != 'admin':
                return jsonify({"error": "Admin access required"}), 403
            
            request.current_user = user
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
