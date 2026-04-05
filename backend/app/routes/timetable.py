from flask import Blueprint, request, jsonify, g
from app.middleware.auth import verify_token, require_role
from app.services.firestore_service import (
    add_timetable_entry,
    list_all_timetable,
    list_faculty_timetable,
    list_student_timetable,
    update_timetable_entry,
    delete_timetable_entry,
    check_timetable_conflicts,
    get_student,
    list_users_by_role
)

from flask_cors import CORS

timetable_bp = Blueprint("timetable", __name__)
CORS(timetable_bp)

@timetable_bp.route("/", methods=["POST"])
@verify_token
@require_role("admin")
def add_tt():
    data = request.json
    conflicts = check_timetable_conflicts(data)
    if conflicts:
        return jsonify({"error": "Timetable conflict", "details": conflicts}), 409
    
    try:
        res = add_timetable_entry(data)
        return jsonify(res), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@timetable_bp.route("/", methods=["GET"])
@verify_token
def get_tt_list():
    try:
        role = g.user_data.get("role")
        if role == "student":
            student = get_student(g.uid)
            if not student: return jsonify({"error": "Student profile not found"}), 404
            res = list_student_timetable(student.get("course"), student.get("semester", "1"))
        elif role == "faculty":
            res = list_faculty_timetable(g.uid)
        else: # admin
            res = list_all_timetable()
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@timetable_bp.route("/", methods=["PUT"])
@verify_token
@require_role("admin")
def edit_tt():
    data = request.json
    tid = data.get("id")
    if not tid: return jsonify({"error": "id required"}), 400
    
    try:
        data.pop('id', None) # Remove ID from the data body before updating document
        
        from app.services.firestore_service import _get_db
        ref = _get_db().collection("timetables").document(tid)
        doc = ref.get()
        if not doc.exists:
            return jsonify({"error": "Timetable entry not found"}), 404
            
        existing = doc.to_dict()
        merged = {**existing, **data}
        
        conflicts = check_timetable_conflicts(merged, exclude_id=tid)
        if conflicts:
            return jsonify({"error": "Timetable conflict", "details": conflicts}), 409

        res = update_timetable_entry(tid, data, g.uid)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@timetable_bp.route("/", methods=["DELETE"])
@verify_token
@require_role("admin")
def del_tt():
    tid = request.args.get("id")
    if not tid: return jsonify({"error": "id required"}), 400
    try:
        delete_timetable_entry(tid)
        return jsonify({"message": "Timetable entry deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@timetable_bp.route("/seed", methods=["POST"])
@verify_token
@require_role("admin")
def seed_tt():
    from app.services.firestore_service import list_courses, list_semesters, list_subjects
    
    # 1. Fetch valid course structure
    courses = list_courses()
    if not courses: return jsonify({"error": "Seed course structure first"}), 400
    
    # Use first course found (usually seeded BCA/BBA)
    course = courses[0]
    cid = course["id"]
    
    sems = list_semesters(cid)
    if not sems: return jsonify({"error": "No semesters found in course"}), 400
    sem = sems[0]
    sid = sem["id"]
    
    subs = list_subjects(cid, sid)
    if not subs: return jsonify({"error": "No subjects found in semester"}), 400
    
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    slots = ["09:00-10:00", "10:00-11:00", "11:15-12:15", "12:15-01:15", "02:00-03:00", "03:00-04:00", "04:00-05:00"]
    rooms = ["Room 101", "Lab 1", "Room 202", "Physics Lab"]
    
    count = 0
    for day in days:
        for i, slot in enumerate(slots):
            sub = subs[i % len(subs)]
            if not sub.get("facultyId"): continue # Skip if no faculty linked
            
            entry = {
                "courseId": cid,
                "semId": sid,
                "subjectId": sub["id"],
                "facultyId": sub["facultyId"],
                "day": day,
                "timeSlot": slot,
                "room": rooms[i % len(rooms)]
            }
            try:
                add_timetable_entry(entry)
                count += 1
            except Exception as e:
                print(f"Seed entry error: {str(e)}")
            
    return jsonify({"message": f"Seeded {count} relational entries for {course['courseName']} Sem {sem['semesterNumber']}"})
