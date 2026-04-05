from flask import Blueprint, request, jsonify, g
from app.middleware.auth import verify_token, require_role
from app.services.firestore_service import (
    add_assignment, list_assignments, get_assignment, 
    submit_assignment, list_submissions, grade_submission, list_courses
)
from datetime import datetime
import random

assignments_bp = Blueprint("assignments", __name__)

@assignments_bp.route("/add", methods=["POST"])
@verify_token
@require_role("admin", "faculty")
def create_assignment():
    data = request.json
    try:
        record = {
            "title": data.get("title"),
            "description": data.get("description", ""),
            "subjectId": data.get("subjectId"),
            "subjectName": data.get("subjectName"),
            "courseId": data.get("courseId"),
            "semester": data.get("semester"),
            "dueDate": data.get("dueDate"),
            "maxMarks": float(data.get("maxMarks", 100)),
            "createdBy": g.uid,
            "createdAt": datetime.now().isoformat(),
            "isActive": True
        }
        res = add_assignment(record)
        return jsonify(res), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@assignments_bp.route("/", methods=["GET"])
@verify_token
def get_assignments():
    try:
        data = list_assignments()
        return jsonify(data), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@assignments_bp.route("/submit", methods=["POST"])
@verify_token
def submit_student_assignment():
    data = request.json
    try:
        assignment_id = data.get("assignmentId")
        if not assignment_id: return jsonify({"error": "assignmentId required"}), 400
        
        record = {
            "studentId": g.uid,
            "studentName": g.user_data.get("name", "Student"),
            "fileUrl": data.get("fileUrl"),
            "submittedAt": datetime.now().isoformat(),
            "status": "submitted"
        }
        res = submit_assignment(assignment_id, record)
        return jsonify(res), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@assignments_bp.route("/submissions", methods=["GET"])
@verify_token
@require_role("admin", "faculty")
def get_submissions():
    assignment_id = request.args.get("assignmentId")
    if not assignment_id: return jsonify({"error": "assignmentId required"}), 400
    try:
        data = list_submissions(assignment_id)
        return jsonify(data), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@assignments_bp.route("/my-submissions", methods=["GET"])
@verify_token
def get_my_submissions():
    from app.services.firestore_service import get_db
    try:
        db = get_db()
        # Query across all assignments for this student's submissions
        assignments = db.collection("assignments").stream()
        my_subs = []
        for a in assignments:
            sub = db.collection("assignments").document(a.id).collection("submissions").document(g.uid).get()
            if sub.exists:
                my_subs.append({**sub.to_dict(), "assignmentId": a.id})
        return jsonify(my_subs), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@assignments_bp.route("/grade", methods=["PUT"])
@verify_token
@require_role("admin", "faculty")
def grade_student_submission():
    data = request.json
    try:
        res = grade_submission(
            data["assignmentId"], data["studentId"], 
            float(data["marks"]), data.get("feedback", ""), g.uid
        )
        return jsonify(res), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@assignments_bp.route("/edit", methods=["PUT"])
@verify_token
@require_role("admin", "faculty")
def edit_assignment_route():
    data = request.json
    aid = data.get("id")
    if not aid: return jsonify({"error": "id required"}), 400
    try:
        from app.services.firestore_service import update_assignment
        data.pop('id', None)
        update_assignment(aid, data, g.uid)
        return jsonify({"message": "Assignment updated"}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@assignments_bp.route("/delete", methods=["DELETE"])
@verify_token
@require_role("admin", "faculty")
def delete_assignment_route():
    try:
        aid = request.args.get("id")
        if not aid: return jsonify({"error": "id required"}), 400
        from app.services.firestore_service import get_db
        db = get_db()
        db.collection("assignments").document(aid).delete()
        return jsonify({"message": "Assignment deleted"}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@assignments_bp.route("/seed", methods=["POST"])
@verify_token
@require_role("admin")
def seed_assignments():
    try:
        courses = list_courses()
        if not courses: return jsonify({"error": "No courses found"}), 400
        c = courses[0]
        
        from app.services.firestore_service import add_material
        
        # 1. Materials
        add_material({
            "title": "Intro to Web Tech",
            "description": "Basic HTML/CSS slides",
            "subjectId": "sub1",
            "subjectName": "Web Technologies",
            "courseId": c["id"],
            "semester": 1,
            "uploadedBy": "admin",
            "fileUrl": "https://example.com/slide1.pdf",
            "createdAt": datetime.now().isoformat()
        })
        
        # 2. Assignment
        a = add_assignment({
            "title": "Build a Simple Form",
            "description": "Create an HTML form with validation",
            "subjectId": "sub1",
            "subjectName": "Web Technologies",
            "courseId": c["id"],
            "semester": 1,
            "dueDate": "2026-05-01T23:59:00",
            "maxMarks": 100,
            "createdBy": "admin",
            "createdAt": datetime.now().isoformat(),
            "isActive": True
        })
        
        return jsonify({"message": "Seeded materials and assignments"}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
