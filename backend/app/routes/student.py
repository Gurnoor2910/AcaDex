from flask import Blueprint, jsonify, g
from app.middleware.auth import verify_token, require_role
from app.services.firestore_service import (
    get_student, get_attendance, get_marks, list_student_announcements
)

student_bp = Blueprint("student", __name__)

@student_bp.route("/profile", methods=["GET"])
@verify_token
@require_role("student")
def get_student_profile():
    # In this ERP, we assume students login with their email.
    # We need to find the student document that matches their UID or email.
    # For simplicity, we'll look for a student doc where studentId matches uid
    # OR we could query students collection by email.
    
    # Let's try to fetch by UID first (assuming studentId = uid)
    student = get_student(g.uid)
    if not student:
        return jsonify({"error": "Student profile not found"}), 404
        
    return jsonify(student), 200

@student_bp.route("/get-attendance", methods=["GET"])
@student_bp.route("/attendance", methods=["GET"])
@verify_token
@require_role("student")
def student_get_attendance():
    records = get_attendance(g.uid)
    return jsonify(records), 200

@student_bp.route("/marks", methods=["GET"])
@verify_token
@require_role("student")
def student_get_marks():
    records = get_marks(g.uid)
    return jsonify(records), 200

@student_bp.route("/announcements", methods=["GET"])
@verify_token
def get_announcements():
    announcements = list_student_announcements(g.uid)
    return jsonify(announcements), 200
