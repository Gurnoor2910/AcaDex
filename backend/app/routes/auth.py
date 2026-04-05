from flask import Blueprint, request, jsonify, g
from app.middleware.auth import verify_token
from app.services.firestore_service import create_user, get_user_by_uid

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
@verify_token
def register():
    """
    Registers a new user in Firestore after Firebase Auth signup.
    The UID is taken from the verified token.
    """
    data = request.json
    uid = g.uid
    
    # Check if user already exists
    existing_user = get_user_by_uid(uid)
    if existing_user:
        return jsonify({"message": "User already exists", "user": existing_user}), 200
        
    user_data = {
        "name": data.get("name"),
        "email": data.get("email"),
        "role": data.get("role", "student"), # Default to student
        "uid": uid
    }
    
    created_user = create_user(uid, user_data)
    return jsonify({"message": "User registered successfully", "user": created_user}), 201

@auth_bp.route("/me", methods=["GET"])
@verify_token
def get_current_user():
    """Returns the current user's profile and role."""
    if not g.user_data:
        return jsonify({"message": "Profile not initialized", "role": None}), 200
    return jsonify(g.user_data), 200
