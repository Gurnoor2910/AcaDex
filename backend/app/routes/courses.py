from flask import Blueprint, request, jsonify, g
from app.middleware.auth import verify_token, require_role
from app.services.firestore_service import (
    add_course, list_courses, update_course, add_semester, list_semesters, 
    update_semester, add_subject, list_subjects, update_subject, 
    assign_faculty_to_subject, get_full_course_structure, 
    get_user_courses, get_user_current_structure,
    delete_course_item, list_users_by_role
)

courses_bp = Blueprint("courses", __name__)

@courses_bp.route("/my", methods=["GET"])
@verify_token
def get_my_courses():
    try:
        res = get_user_courses(g.uid)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@courses_bp.route("/current-structure", methods=["GET"])
@verify_token
def get_cur_struct():
    try:
        res = get_user_current_structure(g.uid)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@courses_bp.route("/edit", methods=["PUT"])
@verify_token
@require_role("admin")
def edit_course_route():
    data = request.json
    cid = data.get("courseId")
    if not cid: return jsonify({"error": "courseId required"}), 400
    try:
        data.pop('courseId', None)
        update_course(cid, data, g.uid)
        res = get_full_course_structure()
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@courses_bp.route("/edit-semester", methods=["PUT"])
@verify_token
@require_role("admin")
def edit_sem_route():
    data = request.json
    cid = data.get("courseId")
    sid = data.get("semesterId")
    num = data.get("semesterNumber")
    if not all([cid, sid, num]): return jsonify({"error": "courseId, semesterId, and semesterNumber required"}), 400
    try:
        update_semester(cid, sid, int(num), g.uid)
        res = get_full_course_structure()
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@courses_bp.route("/edit-subject", methods=["PUT"])
@verify_token
@require_role("admin")
def edit_sub_route():
    data = request.json
    cid = data.get("courseId")
    sid = data.get("semesterId")
    subid = data.get("subjectId")
    if not all([cid, sid, subid]): return jsonify({"error": "courseId, semesterId, and subjectId required"}), 400
    try:
        data.pop('courseId', None)
        data.pop('semesterId', None)
        data.pop('subjectId', None)
        update_subject(cid, sid, subid, data, g.uid)
        res = get_full_course_structure()
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@courses_bp.route("/add", methods=["POST"])
@verify_token
@require_role("admin")
def add_new_course():
    data = request.json
    if not data.get("courseName"): return jsonify({"error": "courseName required"}), 400
    try:
        add_course(data)
        res = get_full_course_structure()
        return jsonify(res), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@courses_bp.route("/all", methods=["GET"])
@verify_token
def get_all_courses():
    try:
        res = list_courses()
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@courses_bp.route("/add-semester", methods=["POST"])
@verify_token
@require_role("admin")
def add_sem():
    data = request.json
    cid = data.get("courseId")
    num = data.get("semesterNumber")
    if not cid or not num: return jsonify({"error": "courseId and semesterNumber required"}), 400
    try:
        add_semester(cid, int(num))
        res = get_full_course_structure()
        return jsonify(res), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@courses_bp.route("/semesters", methods=["GET"])
@verify_token
def get_sems():
    cid = request.args.get("courseId")
    if not cid: return jsonify({"error": "courseId required"}), 400
    try:
        res = list_semesters(cid)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@courses_bp.route("/add-subject", methods=["POST"])
@verify_token
@require_role("admin")
def add_sub():
    data = request.json
    cid = data.get("courseId")
    sid = data.get("semesterId")
    if not cid or not sid: return jsonify({"error": "courseId and semesterId required"}), 400
    try:
        add_subject(cid, sid, data)
        res = get_full_course_structure()
        return jsonify(res), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@courses_bp.route("/subjects", methods=["GET"])
@verify_token
def get_subs():
    cid = request.args.get("courseId")
    sid = request.args.get("semesterId")
    if not cid or not sid: return jsonify({"error": "courseId and semesterId required"}), 400
    try:
        res = list_subjects(cid, sid)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@courses_bp.route("/assign-faculty", methods=["PUT"])
@verify_token
@require_role("admin")
def assign_fac():
    data = request.json
    cid = data.get("courseId")
    sid = data.get("semesterId")
    subid = data.get("subjectId")
    fid = data.get("facultyId")
    fname = data.get("facultyName")
    if not all([cid, sid, subid, fid, fname]): return jsonify({"error": "All fields required"}), 400
    try:
        assign_faculty_to_subject(cid, sid, subid, fid, fname)
        res = get_full_course_structure()
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@courses_bp.route("/structure", methods=["GET"])
@verify_token
def get_struct():
    try:
        res = get_full_course_structure()
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@courses_bp.route("/delete", methods=["DELETE"])
@verify_token
@require_role("admin")
def del_item():
    path = request.args.get("path")
    if not path: return jsonify({"error": "path required"}), 400
    try:
        delete_course_item(path)
        res = get_full_course_structure()
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@courses_bp.route("/seed", methods=["POST"])
@verify_token
@require_role("admin")
def seed_courses():
    faculties = list_users_by_role("faculty")
    if not faculties: return jsonify({"error": "No faculty found to assign"}), 400
    
    course_templates = [
        {"name": "BCA", "duration": 3},
        {"name": "BBA", "duration": 3}
    ]
    
    subjects_pool = ["C Programming", "Discrete Mathematics", "Operating Systems", "DBMS", "Java", "Networking", "Economics", "Accounts", "Management"]
    
    count = 0
    for ct in course_templates:
        try:
            c = add_course({"courseName": ct["name"], "duration": ct["duration"], "totalSemesters": ct["duration"]*2})
            for sem in range(1, c["totalSemesters"] + 1):
                s = add_semester(c["id"], sem)
                for i in range(4): # 4 subjects per sem
                    f = faculties[count % len(faculties)]
                    add_subject(c["id"], s["id"], {
                        "subjectName": subjects_pool[(sem + i) % len(subjects_pool)],
                        "subjectCode": f"{ct['name']}-{sem}{i}",
                        "facultyId": f["uid"],
                        "facultyName": f["name"],
                        "credits": 4
                    })
                    count += 1
        except: continue # Skip if already exists
        
    return jsonify({"message": "Courses, Semesters and Subjects seeded successfully"})
