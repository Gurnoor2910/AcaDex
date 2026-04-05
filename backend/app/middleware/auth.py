"""
Acadex - Authentication Middleware
Verifies Firebase ID tokens and enforces role-based access control.
"""

import functools
from flask import request, jsonify, g
from firebase_admin import auth
from app.services.firestore_service import get_user_by_uid


def verify_token(f):
    """
    Decorator: Validates the Firebase Bearer token in the Authorization header.
    Sets g.uid and g.user_data on success.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if request.method == "OPTIONS":
            return f(*args, **kwargs)
            
        auth_header = request.headers.get("Authorization", "")
        print(f"DEBUG AUTH HEADER: {auth_header[:20]}...")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        id_token = auth_header.split("Bearer ")[1]
        print(f"DEBUG ID TOKEN (start): {id_token[:10]}...")
        try:
            decoded = auth.verify_id_token(id_token)
            g.uid = decoded["uid"]
        except Exception as e:
            print(f"DEBUG AUTH ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Token verification failed: {str(e)}"}), 401

        # Fetch user data from Firestore and attach to request context
        user_data = get_user_by_uid(g.uid)
        g.user_data = user_data

        return f(*args, **kwargs)
    return decorated


def require_role(*roles):
    """
    Decorator factory: Allows access only if the authenticated user has one
    of the specified roles. Must be applied AFTER @verify_token.

    Usage:
        @verify_token
        @require_role("admin", "faculty")
        def my_view(): ...
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            if not g.get("user_data"):
                return jsonify({"error": "User profile not found in database"}), 404
            
            user_role = g.user_data.get("role", "")
            if user_role not in roles:
                return jsonify({
                    "error": f"Access denied. Required role(s): {', '.join(roles)}"
                }), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
