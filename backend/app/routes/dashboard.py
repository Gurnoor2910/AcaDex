from flask import Blueprint, jsonify, g
from app.middleware.auth import verify_token, require_role
from app.services.firestore_service import (
    get_admin_dashboard_data,
    get_faculty_dashboard_data,
    get_student_dashboard_data
)

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/admin", methods=["GET"])
@verify_token
@require_role("admin")
def admin_dashboard():
    try:
        data = get_admin_dashboard_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@dashboard_bp.route("/faculty", methods=["GET"])
@verify_token
@require_role("faculty")
def faculty_dashboard():
    try:
        data = get_faculty_dashboard_data(g.uid)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@dashboard_bp.route("/student", methods=["GET"])
@verify_token
@require_role("student")
def student_dashboard():
    try:
        data = get_student_dashboard_data(g.uid)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
