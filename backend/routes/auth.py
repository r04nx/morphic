"""
Authentication Routes for Morphic Platform
Handles user registration, login, logout, and token management
"""
from flask import Blueprint, request, jsonify
from models.user import UserCreate, UserLogin, UserResponse, TokenResponse
from services.auth_service import AuthService
from models.database import DatabaseManager


def register_auth_routes(app, db_manager: DatabaseManager):
    """Register authentication routes"""
    auth_service = AuthService(db_manager)
    
    # Initialize users table
    auth_service.initialize_users_table()
    
    auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
    
    @auth_bp.route('/register', methods=['POST'])
    def register():
        """Register a new user"""
        try:
            data = request.get_json()
            user_data = UserCreate(**data)
            user = auth_service.register_user(user_data)
            return jsonify({"message": "User registered successfully", "user": user.dict()}), 201
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": "Registration failed"}), 500
    
    @auth_bp.route('/login', methods=['POST'])
    def login():
        """Login user and return JWT token"""
        try:
            data = request.get_json()
            login_data = UserLogin(**data)
            user = auth_service.authenticate_user(login_data.email, login_data.password)
            
            if not user:
                return jsonify({"error": "Invalid email or password"}), 401
            
            # Create access token
            access_token = auth_service.create_access_token(
                data={"sub": str(user.id), "email": user.email, "role": user.role}
            )
            
            return jsonify(TokenResponse(
                access_token=access_token,
                token_type="bearer",
                user=user
            ).dict()), 200
        except Exception as e:
            return jsonify({"error": "Login failed"}), 500
    
    @auth_bp.route('/logout', methods=['POST'])
    def logout():
        """Logout user (client-side token removal)"""
        return jsonify({"message": "Logged out successfully"}), 200
    
    @auth_bp.route('/me', methods=['GET'])
    def get_current_user():
        """Get current authenticated user"""
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
        
        return jsonify(user.dict()), 200
    
    @auth_bp.route('/refresh', methods=['POST'])
    def refresh_token():
        """Refresh access token"""
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
        
        # Create new access token
        new_token = auth_service.create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role}
        )
        
        return jsonify({
            "access_token": new_token,
            "token_type": "bearer"
        }), 200
    
    app.register_blueprint(auth_bp)
