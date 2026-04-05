from flask import Blueprint, request, jsonify, g
from app.middleware.auth import verify_token, require_role
from app.services.firestore_service import (
    mark_attendance, get_attendance, list_attendance_multi, get_student
)
from datetime import datetime

attendance_bp = Blueprint("attendance", __name__)

@attendance_bp.route("/mark", methods=["POST"])
@verify_token
@require_role("admin", "faculty")
def submit_attendance():
    data = request.json
    student_id = data.get("studentId")
    status = data.get("status")
    subject = data.get("subject", "General")
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    
    if not student_id or not status:
        return jsonify({"error": "studentId and status are required"}), 400

    # Role specific validation: Faculty can only mark assigned students
    if g.user_data.get("role") == "faculty":
        student = get_student(student_id)
        if not student or student.get("facultyAssigned") != g.uid:
            return jsonify({"error": "Unauthorized: Student is not assigned to you"}), 403

    record = {
        "date": date,
        "subject": subject,
        "status": status,
        "markedBy": g.uid,
        "teacherName": g.user_data.get("name"),
        "timestamp": datetime.now().isoformat()
    }
    
    result = mark_attendance(student_id, record)
    return jsonify(result), 200

@attendance_bp.route("/student", methods=["GET"])
@verify_token
@require_role("student")
def get_my_attendance_v2():
    records = get_attendance(g.uid)
    return jsonify(records), 200

@attendance_bp.route("/class", methods=["GET"])
@verify_token
@require_role("admin", "faculty")
def get_class_attendance():
    date = request.args.get("date")
    subject = request.args.get("subject")
    
    # Restrict to assigned students if faculty
    faculty_uid = g.uid if g.user_data.get("role") == "faculty" else None
    
    # Simple search for now
    records = list_attendance_multi(date, subject, faculty_uid)
    return jsonify(records), 200

@attendance_bp.route("/edit", methods=["PUT"])
@verify_token
@require_role("admin", "faculty")
def edit_attendance():
    data = request.json
    student_id = data.get("studentId")
    record_id = data.get("recordId")
    
    if not student_id or not record_id:
        return jsonify({"error": "studentId and recordId are required"}), 400

    # Role specific validation
    if g.user_data.get("role") == "faculty":
        student = get_student(student_id)
        if not student or student.get("facultyAssigned") != g.uid:
            return jsonify({"error": "Unauthorized: Cannot edit record for unassigned student"}), 403

    # Update logic
    from app.services.firestore_service import update_attendance as update_svc
    
    update_data = {
        "status": data.get("status"),
        "date": data.get("date"),
        "subject": data.get("subject"),
        "lastUpdatedAt": datetime.now().isoformat(),
        "updatedBy": g.uid
    }
    
    # Filter out None values to prevent overwriting with nulls if optional
    update_data = {k: v for k, v in update_data.items() if v is not None}

    try:
        updated = update_svc(student_id, record_id, update_data)
        return jsonify(updated), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
