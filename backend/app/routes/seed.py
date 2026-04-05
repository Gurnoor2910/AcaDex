from flask import Blueprint, request, jsonify
from app.services.seeder_service import SeederService
from functools import wraps

seed_bp = Blueprint("seed", __name__)

# Simple Role-based decorator (Basic: user's role is extracted from Firestore or assumed from auth context)
# For the purpose of this seeding system, we trust the Admin context from frontend.
# REAL APP: You would verify Firebase Auth token here.

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # In a real app: check user role from token
        # For this dev tool: we rely on frontend calling it from admin dash
        return f(*args, **kwargs)
    return decorated_function

@seed_bp.route("/all", methods=["POST"])
@admin_only
def seed_all():
    """
    POST /api/seed/all
    Body: { "mode": "full" | "quick", "clear": true | false }
    """
    data = request.json or {}
    mode = data.get("mode", "full")
    clear = data.get("clear", True)
    
    seeder = SeederService()
    
    try:
        if clear:
            print("[API] Clearing existing data...")
            seeder.clear_all_data()
            
        print(f"[API] Starting {mode} seed...")
        steps = seeder.seed_all(mode=mode)
        
        return jsonify({
            "status": "success",
            "message": "System data initialized successfully.",
            "steps": steps
        }), 200
        
    except Exception as e:
        print(f"[API] Seeding Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
