from flask import Blueprint, request, jsonify, g
from app.middleware.auth import verify_token, require_role
from app.services.firestore_service import (
    list_students, mark_attendance, add_mark, add_announcement
)
from datetime import datetime

faculty_bp = Blueprint("faculty", __name__)

@faculty_bp.route("/my-students", methods=["GET"])
@verify_token
@require_role("faculty")
def get_assigned_students():
    # Only get students assigned to this faculty
    students = list_students(faculty_uid=g.uid)
    return jsonify(students), 200

@faculty_bp.route("/mark-attendance", methods=["POST"])
@verify_token
@require_role("faculty")
def faculty_mark_attendance():
    data = request.json
    student_id = data.get("studentId")
    status = data.get("status") # present/absent
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    
    if not student_id or not status:
        return jsonify({"error": "studentId and status are required"}), 400
        
    record = {
        "date": date,
        "status": status,
        "markedBy": g.uid
    }
    
    result = mark_attendance(student_id, record)
    return jsonify(result), 200

@faculty_bp.route("/upload-marks", methods=["POST"])
@verify_token
@require_role("faculty")
def faculty_upload_marks():
    data = request.json
    student_id = data.get("studentId")
    subject = data.get("subject")
    score = data.get("score")
    max_score = data.get("maxScore", 100)
    
    if not student_id or not subject or score is None:
        return jsonify({"error": "studentId, subject and score are required"}), 400
        
    record = {
        "subject": subject,
        "score": score,
        "maxMarks": max_score,
        "examType": "Assignment",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "uploadedBy": g.uid,
        "timestamp": datetime.now().isoformat()
    }
    
    result = add_mark(student_id, record)
    return jsonify(result), 200

@faculty_bp.route("/announce", methods=["POST"])
@verify_token
@require_role("faculty")
def announce():
    data = request.json
    title = data.get("title")
    content = data.get("content")
    
    if not title or not content:
        return jsonify({"error": "title and content are required"}), 400
        
    announcement = {
        "title": title,
        "content": content,
        "facultyName": g.user_data.get("name"),
        "facultyUid": g.uid,
        "timestamp": datetime.now().isoformat()
    }
    
    result = add_announcement(announcement)
    return jsonify(result), 201
@faculty_bp.route("/my-structure", methods=["GET"])
@verify_token
@require_role("faculty")
def get_faculty_structure():
    user_data = g.user_data
    # Get assigned IDs
    courses = user_data.get("assignedCourses", [])
    sems = user_data.get("assignedSemesters", [])
    subjects = user_data.get("assignedSubjects", [])
    
    # We need to return the structure for these courses
    from app.services.firestore_service import list_courses, get_db
    db = get_db()
    
    struct = []
    for cid in courses:
        c_doc = db.collection("courses").document(cid).get()
        if not c_doc.exists: continue
        c_data = c_doc.to_dict()
        
        course_entry = {
            "courseId": cid,
            "courseName": c_data.get("courseName"),
            "semesters": []
        }
        
        # Get semesters
        sem_docs = db.collection("courses").document(cid).collection("semesters").stream()
        for sd in sem_docs:
            sd_data = sd.to_dict()
            s_num = sd_data.get("semesterNumber")
            # Filter by assigned semesters
            if s_num not in sems: continue
            
            sem_entry = {
                "id": sd.id,
                "semesterNumber": s_num,
                "subjects": []
            }
            
            # Get subjects
            sub_docs = db.collection("courses").document(cid).collection("semesters").document(sd.id).collection("subjects").stream()
            for sud in sub_docs:
                sud_data = sud.to_dict()
                # Filter by assigned subjects if any (if empty, assume all in assigned sem?)
                # Usually better to check if facultyId matches in subject doc or assignedSubjects list
                if subjects and sud.id not in subjects: continue
                # Also check if facultyId matches directly in subject record
                if sud_data.get("facultyId") == g.uid or sud.id in subjects:
                    sem_entry["subjects"].append({
                        "id": sud.id,
                        "subjectName": sud_data.get("subjectName")
                    })
            
            if sem_entry["subjects"]:
                course_entry["semesters"].append(sem_entry)
        
        if course_entry["semesters"]:
            struct.append(course_entry)
            
    return jsonify(struct), 200
