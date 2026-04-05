from flask import Blueprint, request, jsonify, g
from app.middleware.auth import verify_token, require_role
from app.services.firestore_service import (
    get_marks, add_mark, list_class_marks, update_mark, delete_mark, get_student
)
from datetime import datetime

marks_bp = Blueprint("marks", __name__)

@marks_bp.route("/", methods=["POST"])
@verify_token
@require_role("admin", "faculty")
def submit_marks():
    data = request.json
    student_id = data.get("studentId")
    score = data.get("score")
    max_marks = data.get("maxMarks", 100)
    subject = data.get("subject", "General")
    exam_type = data.get("examType", "Midterm")
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    
    if not student_id or score is None:
        return jsonify({"error": "studentId and score are required"}), 400
        
    try:
        score = float(score)
        max_marks = float(max_marks)
    except ValueError:
        return jsonify({"error": "Score and maxMarks must be numbers"}), 400
        
    if score > max_marks:
        return jsonify({"error": f"Score ({score}) cannot exceed max marks ({max_marks})"}), 400

    if g.user_data.get("role") == "faculty":
        student = get_student(student_id)
        if not student or student.get("facultyAssigned") != g.uid:
            return jsonify({"error": "Unauthorized: Student is not assigned to you"}), 403

    record = {
        "subject": subject,
        "score": score,
        "maxMarks": max_marks,
        "examType": exam_type,
        "date": date,
        "teacherName": g.user_data.get("name"),
        "markedBy": g.uid,
        "createdAt": datetime.now().isoformat(),
        "lastUpdatedAt": datetime.now().isoformat()
    }
    
    try:
        result = add_mark(student_id, record)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@marks_bp.route("/student", methods=["GET"])
@verify_token
@require_role("student")
def get_my_marks():
    records = get_marks(g.uid)
    return jsonify(records), 200

@marks_bp.route("/class", methods=["GET"])
@verify_token
@require_role("admin", "faculty")
def get_class_marks_list():
    date = request.args.get("date")
    subject = request.args.get("subject")
    exam_type = request.args.get("examType")
    
    faculty_uid = g.uid if g.user_data.get("role") == "faculty" else None
    
    records = list_class_marks(subject, exam_type, date, faculty_uid)
    return jsonify(records), 200

@marks_bp.route("/", methods=["PUT"])
@verify_token
@require_role("admin", "faculty")
def edit_marks():
    data = request.json
    student_id = data.get("studentId")
    record_id = data.get("recordId")
    
    if not student_id or not record_id:
        return jsonify({"error": "studentId and recordId are required"}), 400

    if g.user_data.get("role") == "faculty":
        student = get_student(student_id)
        if not student or student.get("facultyAssigned") != g.uid:
            return jsonify({"error": "Unauthorized: Cannot edit record for unassigned student"}), 403

    update_data = {
        "score": data.get("score"),
        "maxMarks": data.get("maxMarks"),
        "subject": data.get("subject"),
        "examType": data.get("examType"),
        "date": data.get("date"),
        "lastUpdatedAt": datetime.now().isoformat(),
        "updatedBy": g.uid
    }
    
    # Filter out None values
    update_data = {k: v for k, v in update_data.items() if v is not None}
    
    if "score" in update_data:
        try:
            update_data["score"] = float(update_data["score"])
            if "maxMarks" in update_data:
                update_data["maxMarks"] = float(update_data["maxMarks"])
        except ValueError:
            return jsonify({"error": "Score and maxMarks must be numbers"}), 400

    try:
        updated = update_mark(student_id, record_id, update_data)
        return jsonify(updated), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@marks_bp.route("/", methods=["DELETE"])
@verify_token
@require_role("admin", "faculty")
def delete_marks_entry():
    student_id = request.args.get("studentId")
    record_id = request.args.get("recordId")
    
    if not student_id or not record_id:
        return jsonify({"error": "studentId and recordId are required"}), 400
        
    if g.user_data.get("role") == "faculty":
        student = get_student(student_id)
        if not student or student.get("facultyAssigned") != g.uid:
            return jsonify({"error": "Unauthorized: Cannot delete record for unassigned student"}), 403
            
    try:
        delete_mark(student_id, record_id)
        return jsonify({"message": "Marks record deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
