"""
Acadex - Firestore Service Layer
All database interactions are centralised here to keep routes clean.
"""

from firebase_admin import firestore
from datetime import datetime, timedelta

# Lazy-initialise the Firestore client once per process
_db = None

def get_db():
    global _db
    if _db is None:
        _db = firestore.client()
    return _db


# ── Users ─────────────────────────────────────────────────────────────────────

def get_user_by_uid(uid: str) -> dict | None:
    doc = get_db().collection("users").document(uid).get()
    return doc.to_dict() if doc.exists else None


def create_user(uid: str, data: dict) -> dict:
    data["uid"] = uid
    get_db().collection("users").document(uid).set(data, merge=True)
    return data


def list_users_by_role(role: str) -> list[dict]:
    docs = get_db().collection("users").where("role", "==", role).stream()
    return [{**d.to_dict(), "uid": d.id} for d in docs]


def delete_user_record(uid: str) -> None:
    get_db().collection("users").document(uid).delete()


# ── Students ──────────────────────────────────────────────────────────────────

def get_student(student_id: str) -> dict | None:
    doc = get_db().collection("students").document(student_id).get()
    return doc.to_dict() if doc.exists else None


def list_students(faculty_uid: str = None) -> list[dict]:
    ref = get_db().collection("students")
    if faculty_uid:
        ref = ref.where("facultyAssigned", "==", faculty_uid)
    return [{**d.to_dict(), "uid": d.id, "studentId": d.id} for d in ref.stream()]


def create_student(student_id: str, data: dict) -> dict:
    data["studentId"] = student_id
    get_db().collection("students").document(student_id).set(data)
    return data


def update_student(student_id: str, data: dict) -> dict:
    get_db().collection("students").document(student_id).update(data)
    return {**data, "studentId": student_id}


def delete_student(student_id: str) -> None:
    # Delete subcollections first via batch
    db = get_db()
    for sub in ("attendance", "marks"):
        docs = db.collection("students").document(student_id).collection(sub).stream()
        for d in docs:
            d.reference.delete()
    
    # Delete from both students and users collections
    db.collection("students").document(student_id).delete()
    db.collection("users").document(student_id).delete()


# ── Attendance ────────────────────────────────────────────────────────────────

def get_attendance(student_id: str) -> list[dict]:
    docs = (get_db()
            .collection("students").document(student_id)
            .collection("attendance").stream())
    return [{**d.to_dict(), "id": d.id} for d in docs]


def mark_attendance(student_id: str, record: dict) -> dict:
    # Use composite ID to prevent duplicate for same student + date + subject
    date_id = record.get("date")
    subject_id = record.get("subject", "General").replace(" ", "_")
    compound_id = f"{date_id}_{subject_id}"
    
    # Enrichment: Add student info to the record for global reports
    student = get_student(student_id)
    if student:
        record["studentId"] = student_id
        record["studentName"] = student.get("name", "Unknown")
        record["studentEmail"] = student.get("email", "N/A")

    ref = (get_db()
           .collection("students").document(student_id)
           .collection("attendance").document(compound_id))
    
    ref.set(record)
    return record


def list_attendance_multi(date: str = None, subject: str = None, faculty_uid: str = None) -> list[dict]:
    """
    Robust listing across all students. 
    Can filter by faculty to only show assigned students.
    """
    all_logs = []
    try:
        # Get student IDs (optionally filtered by faculty)
        students = list_students(faculty_uid)
        db = get_db()
        
        for s in students:
            sid = s.get("uid") or s.get("id")
            if not sid: continue
            
            # Fetch attendance subcollection for this student
            query = db.collection("students").document(sid).collection("attendance")
            
            if date:
                query = query.where("date", "==", date)
            if subject:
                query = query.where("subject", "==", subject)
            
            docs = query.stream()
            for d in docs:
                data = d.to_dict()
                data["id"] = d.id # Ensure ID is present for editing
                # Ensure student info is present
                data["studentId"] = sid
                if "studentName" not in data:
                    data["studentName"] = s.get("name", "Student")
                all_logs.append(data)
                
    except Exception as e:
        print(f"REPORTING ERROR: {str(e)}")
        # If this fails, return empty list instead of crashing
        return []
        
    return all_logs

def update_attendance(student_id: str, old_record_id: str, new_data: dict) -> dict:
    """
    Updates attendance with composite ID migration if date/subject changes.
    Preserves existing fields like 'markedBy' and 'teacherName'.
    """
    db = get_db()
    ref_col = db.collection("students").document(student_id).collection("attendance")
    
    old_ref = ref_col.document(old_record_id)
    old_snap = old_ref.get()
    if not old_snap.exists:
        raise Exception("Attendance record not found.")
    
    current_data = old_snap.to_dict()
    
    # Generate new composite ID
    date = new_data.get("date") or current_data.get("date")
    subject = new_data.get("subject") or current_data.get("subject", "General")
    new_compound_id = f"{date}_{subject.replace(' ', '_')}"
    
    # Merge data
    updated_data = {**current_data, **new_data}
    
    # Check if we are moving the record to a new ID
    if new_compound_id != old_record_id:
        if ref_col.document(new_compound_id).get().exists:
            raise Exception(f"Conflict: Attendance already exists for {subject} on {date}")
        
        # Delete old, set new
        old_ref.delete()
        ref_col.document(new_compound_id).set(updated_data)
    else:
        # Just update existing
        old_ref.update(new_data)
    
    return {**updated_data, "id": new_compound_id}


# ── Marks ─────────────────────────────────────────────────────────────────────

def get_marks(student_id: str) -> list[dict]:
    docs = (get_db()
            .collection("students").document(student_id)
            .collection("marks").stream())
    return [{**d.to_dict(), "id": d.id} for d in docs]

def add_mark(student_id: str, record: dict) -> dict:
    subject = record.get("subject", "").replace(" ", "_")
    exam_type = record.get("examType", "").replace(" ", "_")
    date = record.get("date", "")
    compound_id = f"{subject}_{exam_type}_{date}"
    
    student = get_student(student_id)
    if student:
        record["studentId"] = student_id
        record["studentName"] = student.get("name", "Unknown")
        
    ref = (get_db()
           .collection("students").document(student_id)
           .collection("marks").document(compound_id))
           
    if ref.get().exists:
         raise Exception(f"Marks entry already exists for {subject} {exam_type} on {date}")
         
    ref.set(record)
    return {**record, "id": compound_id}

def list_class_marks(subject: str = None, exam_type: str = None, date: str = None, faculty_uid: str = None) -> list[dict]:
    all_marks = []
    try:
        students = list_students(faculty_uid)
        db = get_db()
        for s in students:
            sid = s.get("uid") or s.get("id")
            if not sid: continue
            
            query = db.collection("students").document(sid).collection("marks")
            if subject:
                query = query.where("subject", "==", subject)
            if exam_type:
                query = query.where("examType", "==", exam_type)
            if date:
                query = query.where("date", "==", date)
                
            docs = query.stream()
            for d in docs:
                data = d.to_dict()
                data["id"] = d.id
                data["studentId"] = sid
                if "studentName" not in data:
                    data["studentName"] = s.get("name", "Student")
                all_marks.append(data)
    except Exception as e:
        print(f"FAILED TO LIST MARKS: {str(e)}")
        return []
        
    return all_marks

def update_mark(student_id: str, old_record_id: str, new_data: dict) -> dict:
    db = get_db()
    ref_col = db.collection("students").document(student_id).collection("marks")
    old_ref = ref_col.document(old_record_id)
    old_snap = old_ref.get()
    
    if not old_snap.exists:
        raise Exception("Marks record not found.")
        
    current_data = old_snap.to_dict()
    updated_data = {**current_data, **new_data}
    
    subject = updated_data.get("subject", "").replace(" ", "_")
    exam_type = updated_data.get("examType", "").replace(" ", "_")
    date = updated_data.get("date", "")
    new_compound_id = f"{subject}_{exam_type}_{date}"
    
    if new_compound_id != old_record_id:
        if ref_col.document(new_compound_id).get().exists:
            raise Exception("Conflict: A mark entry already exists for this subject, exam type, and date.")
        old_ref.delete()
        ref_col.document(new_compound_id).set(updated_data)
    else:
        old_ref.update(new_data)
        
    return {**updated_data, "id": new_compound_id}

def delete_mark(student_id: str, record_id: str) -> None:
    get_db().collection("students").document(student_id).collection("marks").document(record_id).delete()


# ── Announcements ─────────────────────────────────────────────────────────────

def add_announcement(data: dict) -> dict:
    db = get_db()
    ref = db.collection("announcements").document()
    data["id"] = ref.id
    if "createdAt" not in data:
        data["createdAt"] = datetime.now().isoformat()
    ref.set(data)
    return data

def list_all_announcements() -> list[dict]:
    db = get_db()
    docs = db.collection("announcements").stream()
    all_ann = []
    for d in docs:
        all_ann.append({**d.to_dict(), "id": d.id})
    
    priority_map = {"High": 3, "Medium": 2, "Low": 1}
    all_ann.sort(key=lambda x: (priority_map.get(x.get("priority"), 0), x.get("createdAt", "")), reverse=True)
    return all_ann

def list_student_announcements(student_uid: str) -> list[dict]:
    db = get_db()
    student = get_student(student_uid)
    course = student.get("course") if student else None
    
    docs = db.collection("announcements").where("isActive", "==", True).stream()
    relevant = []
    now = datetime.now().isoformat()
    
    for d in docs:
        ann = d.to_dict()
        ann["id"] = d.id
        
        # Expiry Check
        if ann.get("expiryDate") and ann.get("expiryDate") < now:
            continue
            
        target = ann.get("targetAudience", "all")
        if target == "all":
            relevant.append(ann)
        elif target == "students":
            relevant.append(ann)
        elif target == "specificCourse" and ann.get("course") == course:
            relevant.append(ann)
            
    priority_map = {"High": 3, "Medium": 2, "Low": 1}
    relevant.sort(key=lambda x: (priority_map.get(x.get("priority"), 0), x.get("createdAt", "")), reverse=True)
    return relevant

def get_announcement(ann_id: str) -> dict:
    doc = get_db().collection("announcements").document(ann_id).get()
    if doc.exists:
        return {**doc.to_dict(), "id": doc.id}
    return None

def update_announcement(ann_id: str, data: dict, updated_by: str) -> dict:
    db = get_db()
    ref = db.collection("announcements").document(ann_id)
    doc = ref.get()
    if not doc.exists: raise Exception("Announcement not found")
    old_data = doc.to_dict()
    
    data["lastUpdatedAt"] = datetime.now().isoformat()
    data["updatedBy"] = updated_by
    
    ref.update(data)
    
    # Audit History
    ref.collection("history").add({
        "old": {k: old_data.get(k) for k in data.keys() if k in old_data},
        "new": data,
        "updatedBy": updated_by,
        "timestamp": datetime.now().isoformat()
    })
    
    return {**data, "id": ann_id}

def delete_announcement_record(ann_id: str):
    get_db().collection("announcements").document(ann_id).delete()

# ── Courses, Semesters & Subjects ─────────────────────────────────────────────

def add_course(data: dict) -> dict:
    db = get_db()
    # Check uniqueness
    existing = db.collection("courses").where("courseName", "==", data["courseName"]).get()
    if existing: raise Exception(f"Course '{data['courseName']}' already exists")
    
    ref = db.collection("courses").document()
    data["id"] = ref.id
    data["createdAt"] = datetime.now().isoformat()
    ref.set(data)
    
    # Auto-sync semesters after creation
    sync_semesters(ref.id, data.get("admin_uid", "system"))
    return data

def list_courses() -> list[dict]:
    docs = get_db().collection("courses").stream()
    return [{**d.to_dict(), "id": d.id} for d in docs]

def add_semester(course_id: str, sem_num: int) -> dict:
    db = get_db()
    # Check if exists
    existing = db.collection("courses").document(course_id).collection("semesters").where("semesterNumber", "==", sem_num).get()
    if existing: raise Exception(f"Semester {sem_num} already exists for this course")
    
    ref = db.collection("courses").document(course_id).collection("semesters").document(str(sem_num))
    data = {
        "semesterNumber": sem_num,
        "createdAt": datetime.now().isoformat()
    }
    ref.set(data)
    return {**data, "id": ref.id}

def list_semesters(course_id: str) -> list[dict]:
    docs = get_db().collection("courses").document(course_id).collection("semesters").stream()
    return sorted([{**d.to_dict(), "id": d.id} for d in docs], key=lambda x: int(x["semesterNumber"]))

def add_subject(course_id: str, sem_id: str, data: dict) -> dict:
    db = get_db()
    # Check subjectCode uniqueness within a course
    # (Simplified: check globally within course for now)
    # Correct structure: subjects are under semesters
    ref = db.collection("courses").document(course_id).collection("semesters").document(sem_id).collection("subjects").document()
    data["id"] = ref.id
    data["createdAt"] = datetime.now().isoformat()
    ref.set(data)
    return data

def list_subjects(course_id: str, sem_id: str) -> list[dict]:
    docs = get_db().collection("courses").document(course_id).collection("semesters").document(sem_id).collection("subjects").stream()
    return [{**d.to_dict(), "id": d.id} for d in docs]

def assign_faculty_to_subject(course_id: str, sem_id: str, subject_id: str, faculty_id: str, faculty_name: str):
    db = get_db()
    ref = db.collection("courses").document(course_id).collection("semesters").document(sem_id).collection("subjects").document(subject_id)
    ref.update({
        "facultyId": faculty_id,
        "facultyName": faculty_name,
        "updatedAt": datetime.now().isoformat()
    })

def get_full_course_structure() -> list[dict]:
    db = get_db()
    courses = list_courses()
    full_structure = []
    
    for c in courses:
        cid = c["id"]
        semesters = list_semesters(cid)
        c["semesters"] = []
        for s in semesters:
            sid = s["id"]
            subjects = list_subjects(cid, sid)
            s["subjects"] = subjects
            c["semesters"].append(s)
        full_structure.append(c)
        
    return full_structure

def get_user_courses(uid: str) -> list[dict]:
    db = get_db()
    user = db.collection("users").document(uid).get()
    if not user.exists: return []
    userdata = user.to_dict()
    role = userdata.get("role")
    
    if role == "admin":
        return get_full_course_structure()
    
    elif role == "faculty":
        assigned_cids = userdata.get("assignedCourses", [])
        if not assigned_cids: return []
        
        all_courses = get_full_course_structure()
        return [c for c in all_courses if c["id"] in assigned_cids]
    
    elif role == "student":
        cid = userdata.get("courseId")
        current_sem = userdata.get("semester")
        if not cid: return []
        
        c_doc = db.collection("courses").document(cid).get()
        if not c_doc.exists: return []
        c = {**c_doc.to_dict(), "id": c_doc.id, "semesters": []}
        
        semesters = list_semesters(cid)
        for s in semesters:
            sid = s["id"]
            if str(s.get("semesterNumber")) == str(current_sem):
                s["currentSemester"] = True
            subjects = list_subjects(cid, sid)
            s["subjects"] = subjects
            c["semesters"].append(s)
            
        return [c]
    
    return []

def get_user_current_structure(uid: str) -> list[dict]:
    db = get_db()
    user = db.collection("users").document(uid).get()
    if not user.exists: return []
    userdata = user.to_dict()
    role = userdata.get("role")
    
    if role == "admin":
        return get_full_course_structure()
        
    if role == "student":
        cid = userdata.get("courseId")
        cur_sem = userdata.get("semester")
        if not cid or not cur_sem: return []
        
        c_doc = db.collection("courses").document(cid).get()
        if not c_doc.exists: return []
        c = {**c_doc.to_dict(), "id": c_doc.id, "semesters": []}
        
        s_doc = db.collection("courses").document(cid).collection("semesters").document(str(cur_sem)).get()
        if s_doc.exists:
            s = {**s_doc.to_dict(), "id": s_doc.id, "currentSemester": True}
            s["subjects"] = list_subjects(cid, s_doc.id)
            c["semesters"].append(s)
            
        return [c]
        
    elif role == "faculty":
        assigned_cids = userdata.get("assignedCourses", [])
        assigned_sems = userdata.get("assignedSemesters", []) # Optional filter
        if not assigned_cids: return []
        
        results = []
        for cid in assigned_cids:
            c_doc = db.collection("courses").document(cid).get()
            if not c_doc.exists: continue
            c = {**c_doc.to_dict(), "id": c_doc.id, "semesters": []}
            
            sems = list_semesters(cid)
            for s in sems:
                # If assignedSemesters exists, only show those. Else show all? 
                # User: "else show all semesters"
                if assigned_sems and str(s.get("semesterNumber")) not in [str(x) for x in assigned_sems]:
                    continue
                s["subjects"] = list_subjects(cid, s["id"])
                c["semesters"].append(s)
            results.append(c)
        return results
        
    return []

def delete_course_item(path: str):
    """
    path: 'courses/CID' or 'courses/CID/semesters/SID' or 'courses/CID/semesters/SID/subjects/SUBID'
    Note: Firestore doesn't delete subcollections automatically. 
    (Manual cleanup or recursive delete required)
    """
    db = get_db()
    parts = path.split('/')
    if len(parts) == 2: # Course
        db.collection("courses").document(parts[1]).delete()
    elif len(parts) == 4: # Semester
        db.collection("courses").document(parts[1]).collection("semesters").document(parts[3]).delete()
    elif len(parts) == 6: # Subject
        db.collection("courses").document(parts[1]).collection("semesters").document(parts[3]).collection("subjects").document(parts[5]).delete()

def get_subject_by_id(course_id: str, sem_id: str, subject_id: str) -> dict:
    doc = get_db().collection("courses").document(course_id).collection("semesters").document(sem_id).collection("subjects").document(subject_id).get()
    return {**doc.to_dict(), "id": doc.id} if doc.exists else None

def update_course(course_id: str, data: dict, admin_uid: str) -> dict:
    db = get_db()
    ref = db.collection("courses").document(course_id)
    old_doc = ref.get()
    if not old_doc.exists: raise Exception("Course not found")
    old_data = old_doc.to_dict()

    if "courseName" in data and data["courseName"] != old_data.get("courseName"):
        existing = db.collection("courses").where("courseName", "==", data["courseName"]).get()
        if existing: raise Exception(f"Course name '{data['courseName']}' already exists")

    data["lastUpdatedAt"] = datetime.now().isoformat()
    data["updatedBy"] = admin_uid
    ref.update(data)
    
    # Trigger semester sync if totalSemesters changed
    if "totalSemesters" in data:
        sync_semesters(course_id, admin_uid)
    
    # Audit Trail
    ref.collection("history").add({
        "old": {k: old_data.get(k) for k in data.keys() if k in old_data},
        "new": data,
        "updatedBy": admin_uid,
        "timestamp": datetime.now().isoformat()
    })
    return {**data, "id": course_id}

def sync_semesters(course_id: str, admin_uid: str):
    """
    Ensures the number of semester documents matches course.totalSemesters.
    Adds missing semesters and deletes extra ones (with validation).
    """
    db = get_db()
    course_ref = db.collection("courses").document(course_id)
    course_doc = course_ref.get()
    if not course_doc.exists: return
    
    course_data = course_doc.to_dict()
    course_name = course_data.get("courseName")
    total_sems = int(course_data.get("totalSemesters", 0))
    
    # 1. Fetch existing semesters
    sem_docs = list_semesters(course_id)
    existing_nums = [int(s["semesterNumber"]) for s in sem_docs]
    existing_map = {int(s["semesterNumber"]): s["id"] for s in sem_docs}
    
    # 2. Add missing semesters
    for i in range(1, total_sems + 1):
        if i not in existing_nums:
            # We use str(i) as ID to keep it consistent
            ref = db.collection("courses").document(course_id).collection("semesters").document(str(i))
            ref.set({
                "semesterNumber": i,
                "createdAt": datetime.now().isoformat(),
                "createdBy": admin_uid,
                "autoGenerated": True
            })
            
    # 3. Delete extra semesters
    # We only delete from the end to maintain continuity
    for num in existing_nums:
        if num > total_sems:
            sid = existing_map[num]
            
            # Validation: Check Subjects
            subs = list_subjects(course_id, sid)
            if subs:
                raise Exception(f"Cannot reduce semesters to {total_sems}: Semester {num} already has {len(subs)} subjects. Delete them first.")
            
            # Validation: Check Timetable
            tt_query = db.collection("timetables").where("course", "==", course_name).where("semester", "==", str(num)).limit(1).get()
            if tt_query:
                raise Exception(f"Cannot reduce semesters to {total_sems}: Semester {num} has timetable entries.")
                
            # Validation: Check Students
            students_query = db.collection("users").where("role", "==", "student").where("courseId", "==", course_id).where("semester", "==", str(num)).limit(1).get()
            if students_query:
                raise Exception(f"Cannot reduce semesters to {total_sems}: Students are currently enrolled in Semester {num}.")

            # SAFE TO DELETE
            db.collection("courses").document(course_id).collection("semesters").document(sid).delete()

def update_semester(course_id: str, sem_id: str, sem_num: int, admin_uid: str) -> dict:
    db = get_db()
    ref = db.collection("courses").document(course_id).collection("semesters").document(sem_id)
    old_doc = ref.get()
    if not old_doc.exists: raise Exception("Semester not found")
    old_data = old_doc.to_dict()

    if sem_num != old_data.get("semesterNumber"):
        existing = db.collection("courses").document(course_id).collection("semesters").where("semesterNumber", "==", sem_num).get()
        if existing: raise Exception(f"Semester {sem_num} already exists for this course")

    update_data = {
        "semesterNumber": sem_num,
        "lastUpdatedAt": datetime.now().isoformat(),
        "updatedBy": admin_uid
    }
    ref.update(update_data)
    return {**update_data, "id": sem_id}

def update_subject(course_id: str, sem_id: str, sub_id: str, data: dict, admin_uid: str) -> dict:
    db = get_db()
    ref = db.collection("courses").document(course_id).collection("semesters").document(sem_id).collection("subjects").document(sub_id)
    old_doc = ref.get()
    if not old_doc.exists: raise Exception("Subject not found")
    old_data = old_doc.to_dict()

    data["lastUpdatedAt"] = datetime.now().isoformat()
    data["updatedBy"] = admin_uid
    ref.update(data)
    
    # Audit Trail
    ref.collection("history").add({
        "old": {k: old_data.get(k) for k in data.keys() if k in old_data},
        "new": data,
        "updatedBy": admin_uid,
        "timestamp": datetime.now().isoformat()
    })
    return {**data, "id": sub_id}


# ── Fees ──────────────────────────────────────────────────────────────────────

# ── Fees ──────────────────────────────────────────────────────────────────────

def get_student_fees(student_id: str) -> dict:
    """
    Returns student fee summary and list of transactions.
    """
    student = get_student(student_id)
    if not student:
        return {"error": "Student not found"}
        
    transactions = (get_db()
                    .collection("students").document(student_id)
                    .collection("fees")
                    .order_by("paymentDate", direction=firestore.Query.DESCENDING)
                    .stream())
    
    payment_list = [{**d.to_dict(), "id": d.id} for d in transactions]
    
    return {
        "studentId": student_id,
        "name": student.get("name"),
        "totalFees": student.get("totalFees", 0),
        "feesPaid": student.get("feesPaid", False),
        "pendingAmount": student.get("pendingAmount", 0),
        "transactions": payment_list
    }


def add_fee_payment(student_id: str, record: dict) -> dict:
    """
    Adds a payment record and updates the student's aggregate fee stats.
    """
    db = get_db()
    student_ref = db.collection("students").document(student_id)
    student_snap = student_ref.get()
    
    if not student_snap.exists:
        raise Exception("Student not found")
        
    student_data = student_snap.to_dict()
    total_fees = float(student_data.get("totalFees", 0))
    amount_paid = float(record.get("amountPaid", 0))
    
    # 1. Save Transaction
    fee_ref = student_ref.collection("fees").document()
    now = datetime.now().isoformat()
    record["id"] = fee_ref.id
    record["createdAt"] = firestore.SERVER_TIMESTAMP
    fee_ref.set(record)
    
    # 2. Recalculate Sum
    all_payments = student_ref.collection("fees").stream()
    sum_paid = sum(float(p.to_dict().get("amountPaid", 0)) for p in all_payments)
    
    # 3. Update Student Record
    pending = max(0, total_fees - sum_paid)
    is_fully_paid = pending == 0
    
    student_ref.update({
        "pendingAmount": pending,
        "feesPaid": is_fully_paid
    })
    
    return {**record, "createdAt": now, "pendingAmount": pending, "feesPaid": is_fully_paid}


def submit_fee_payment(student_id: str, data: dict) -> dict:
    """
    Workflow Step 1: Student submits a payment request (status: pending)
    Ensures studentName and courseId are fetched from students collection.
    """
    db = get_db()
    student = db.collection("students").document(student_id).get()
    if not student.exists: raise Exception("Student not found")
    
    s_data = student.to_dict()
    student_name = s_data.get("name")
    course_id = s_data.get("course")
    
    now = datetime.now()
    
    # Prevent duplicate pending payments
    existing_pending = db.collection("fees_requests")\
        .where("studentId", "==", student_id)\
        .where("status", "==", "pending").get()
    if len(existing_pending) > 0:
        raise Exception("You already have a pending payment request. Please wait for approval.")

    fee_ref = db.collection("fees_requests").document()
    data["id"] = fee_ref.id
    data["studentId"] = student_id
    data["studentName"] = student_name
    data["courseId"] = course_id
    data["status"] = "pending"
    data["paidAt"] = now.isoformat()
    data["createdAt"] = firestore.SERVER_TIMESTAMP # For Firestore
    
    fee_ref.set(data)
    
    # Replace Sentinel with serializable string for the API response
    response_data = {**data, "createdAt": now.isoformat()}
    return response_data

def list_all_fee_requests(status=None) -> list[dict]:
    """
    Workflow Step 2: Admin views all fee requests
    """
    db = get_db()
    query = db.collection("fees_requests")
    if status:
        query = query.where("status", "==", status)
    
    docs = query.order_by("paidAt", direction=firestore.Query.DESCENDING).get()
    return [{**d.to_dict(), "id": d.id} for d in docs]

def get_student_fee_requests(student_id: str) -> list[dict]:
    """
    Workflow Step 3: Student views their own request history
    """
    db = get_db()
    docs = db.collection("fees_requests").where("studentId", "==", student_id).order_by("paidAt", direction=firestore.Query.DESCENDING).get()
    return [{**d.to_dict(), "id": d.id} for d in docs]

def update_fee_status(fee_id, status, admin_uid):
    """
    Workflow Step 4: Admin approves/rejects a payment
    """
    db = get_db()
    ref = db.collection("fees_requests").document(fee_id)
    fee_doc = ref.get()
    if not fee_doc.exists: raise Exception("Fee record not found")
    
    fee_data = fee_doc.to_dict()
    student_id = fee_data.get("studentId")
    amount = float(fee_data.get("amount", 0))

    update_data = {
        "status": status,
        "approvedAt": datetime.now().isoformat(),
        "approvedBy": admin_uid
    }

    # If approved, calculate nextDueDate (30 days from now)
    if status == "approved":
        next_due = (datetime.now() + timedelta(days=30)).isoformat()
        update_data["nextDueDate"] = next_due
        
        # Update aggregating student record
        add_fee_payment(student_id, {
            "amountPaid": amount,
            "paymentDate": fee_data.get("paidAt"),
            "paymentMode": fee_data.get("paymentMode", "Online (Approval)"),
            "receivedBy": admin_uid,
            "refId": fee_id
        })
        
        # Sync nextDueDate to student record for easy fetching
        db.collection("students").document(student_id).update({
            "nextDueDate": next_due
        })
    
    ref.update(update_data)
    return {**fee_data, **update_data}


def list_all_student_fees() -> list[dict]:
    """
    Returns broad fee summary for all students, including their latest request status.
    FIX 5: Return ALL students with status and amount.
    """
    db = get_db()
    students = list_students()
    all_summaries = []
    
    # Pre-fetch all fee requests to map status and due dates
    requests = db.collection("fees_requests").order_by("createdAt", direction=firestore.Query.DESCENDING).get()
    status_map = {}
    due_map = {}
    for r in requests:
        r_dict = r.to_dict()
        rid = r_dict.get("studentId")
        if rid not in status_map:
            status_map[rid] = r_dict.get("status")
            due_map[rid] = r_dict.get("nextDueDate")

    for s in students:
        sid = s.get("uid") or s.get("studentId") # Handle both uid/studentId keys
        all_summaries.append({
            "studentId": sid,
            "studentName": s.get("name"),
            "email": s.get("email"),
            "courseId": s.get("course"),
            "amount": s.get("totalFees", 0), # Master amount
            "pendingAmount": s.get("pendingAmount", 0),
            "status": status_map.get(sid, "unpaid"), 
            "nextDueDate": due_map.get(sid) or s.get("nextDueDate"), # Check map then student record
            "feesPaid": s.get("feesPaid", False)
        })
    return all_summaries


def update_student_total_fees(student_id: str, new_total: float) -> dict:
    """
    Updates the master fee amount for a student and recalculates pending.
    """
    db = get_db()
    student_ref = db.collection("students").document(student_id)
    student_snap = student_ref.get()
    
    if not student_snap.exists:
        raise Exception("Student not found")
        
    # Get current sum of payments
    all_payments = student_ref.collection("fees").stream()
    sum_paid = sum(float(p.to_dict().get("amountPaid", 0)) for p in all_payments)
    
    pending = max(0, new_total - sum_paid)
    is_fully_paid = pending == 0
    
    update_data = {
        "totalFees": new_total,
        "pendingAmount": pending,
        "feesPaid": is_fully_paid
    }
    
    student_ref.update(update_data)
    return update_data


def delete_fee_transaction(student_id: str, transaction_id: str) -> dict:
    """
    Deletes a transaction and updates student pending status.
    """
    db = get_db()
    student_ref = db.collection("students").document(student_id)
    trans_ref = student_ref.collection("fees").document(transaction_id)
    
    if not trans_ref.get().exists:
        raise Exception("Transaction not found")
        
    trans_ref.delete()
    
    # Recalculate everything
    student_snap = student_ref.get()
    student_data = student_snap.to_dict()
    total_fees = float(student_data.get("totalFees", 0))
    
    all_payments = student_ref.collection("fees").stream()
    sum_paid = sum(float(p.to_dict().get("amountPaid", 0)) for p in all_payments)
    
    pending = max(0, total_fees - sum_paid)
    is_fully_paid = pending == 0
    
    student_ref.update({
        "pendingAmount": pending,
        "feesPaid": is_fully_paid
    })
    
# ── Dashboard Aggregations ──────────────────────────────────────────────────

def get_admin_dashboard_data() -> dict:
    db = get_db()
    students = list_students()
    faculty = list_users_by_role("faculty")
    
    total_rev = 0
    total_pending = 0
    
    # ── AGGREGATE LEDGER TOTALS ───────────────────────────────────────────
    # Use collection_group to efficiently scan all student fee records
    all_fee_records = db.collection_group("feeRecords").stream()
    for rec in all_fee_records:
        r_data = rec.to_dict()
        total_rev += float(r_data.get("paidAmount", 0))
        total_pending += float(r_data.get("pendingAmount", 0))
        
    # Stats from collection groups
    all_attendance = db.collection_group("attendance").stream()
    att_list = [d.to_dict() for d in all_attendance]
    total_att = len(att_list)
    present_att = len([a for a in att_list if a.get("status") == "present"])
    att_perc = (present_att / total_att * 100) if total_att > 0 else 0
    
    all_marks = db.collection_group("marks").stream()
    marks_list = [d.to_dict() for d in all_marks]
    avg_marks = sum(m.get("score", 0) for m in marks_list) / len(marks_list) if marks_list else 0
    
    # Subject wise avg
    subject_marks = {}
    for m in marks_list:
        sub = m.get("subject")
        if sub not in subject_marks: subject_marks[sub] = []
        subject_marks[sub].append(m.get("score", 0))
    
    subject_perf = {s: sum(v)/len(v) for s, v in subject_marks.items()}
    
    # Top 5 Students (by avg marks)
    student_scores = {}
    for m in marks_list:
        sid = m.get("studentId")
        if not sid: continue
        if sid not in student_scores: student_scores[sid] = []
        student_scores[sid].append(m.get("score", 0))
    
    top_students = []
    for sid, scores in student_scores.items():
        s_obj = next((s for s in students if s["uid"] == sid), None)
        if s_obj:
            top_students.append({
                "name": s_obj["name"],
                "avg": sum(scores)/len(scores)
            })
    top_students.sort(key=lambda x: x["avg"], reverse=True)
    
    return {
        "totalStudents": len(students),
        "totalFaculty": len(faculty),
        "totalRevenue": total_rev,
        "pendingFees": total_pending,
        "overallAttendance": round(att_perc, 1),
        "averageMarks": round(avg_marks, 1),
        "subjectPerformance": subject_perf,
        "topStudents": top_students[:5]
    }


def get_faculty_dashboard_data(faculty_uid: str) -> dict:
    db = get_db()
    students = list_students(faculty_uid)
    sids = [s["uid"] for s in students]
    
    if not sids:
        # Return empty summary if no students assigned
        return {
            "totalStudents": 0,
            "averageClassMarks": 0,
            "attendancePercentage": 0,
            "subjectPerformance": {},
            "lowPerformers": [],
            "recentActivity": []
        }
        
    relevant_marks = []
    relevant_att = []
    
    # Fetch specifically for assigned students (more efficient than filtering collection groups)
    for sid in sids:
        student_marks = db.collection("students").document(sid).collection("marks").stream()
        for m in student_marks:
            relevant_marks.append(m.to_dict())
            
        student_att = db.collection("students").document(sid).collection("attendance").stream()
        for a in student_att:
            relevant_att.append(a.to_dict())
    
    avg_marks = sum(m.get("score", 0) for m in relevant_marks) / len(relevant_marks) if relevant_marks else 0
    
    # Group by student to find low performers
    student_avgs = {}
    for m in relevant_marks:
        sid = m.get("studentId")
        if not sid: continue
        if sid not in student_avgs: student_avgs[sid] = []
        student_avgs[sid].append(m.get("score", 0))
    
    low_performers = []
    for sid, scores in student_avgs.items():
        avg = sum(scores)/len(scores)
        if avg < 60: # Threshold
            s_obj = next((s for s in students if s["uid"] == sid), None)
            low_performers.append({"name": s_obj["name"] if s_obj else sid, "avg": round(avg, 1)})
            
    # Attendance %
    present_count = len([a for a in relevant_att if a.get("status") == "present"])
    att_perc = (present_count / len(relevant_att) * 100) if relevant_att else 0
    
    # Subject wise performance for this faculty's students
    subject_marks = {}
    for m in relevant_marks:
        sub = m.get("subject")
        if sub not in subject_marks: subject_marks[sub] = []
        subject_marks[sub].append(m.get("score", 0))
    subject_perf = {s: round(sum(v)/len(v), 1) for s, v in subject_marks.items()}
    
    return {
        "totalStudents": len(students),
        "averageClassMarks": round(avg_marks, 1),
        "attendancePercentage": round(att_perc, 1),
        "subjectPerformance": subject_perf,
        "lowPerformers": low_performers,
        "recentActivity": relevant_att[:10]
    }


def get_student_dashboard_data(student_uid: str) -> dict:
    ledger = get_fee_ledger(student_uid)
    attendance = get_attendance(student_uid)
    marks = get_marks(student_uid)
    
    # Calculate global fee status from ledger
    total_pending = sum(f.get("pendingAmount", 0) for f in ledger)
    fee_status = "Paid" if total_pending <= 0 else f"₹{int(total_pending)} Pending"
    
    att_perc = (len([a for a in attendance if a["status"] == "present"]) / len(attendance) * 100) if attendance else 0
    avg_marks = sum(m.get("score", 0) for m in marks) / len(marks) if marks else 0
    
    # Subject wise breakdown
    sub_marks = {}
    for m in marks:
        sub = m.get("subject", "General")
        sub_marks[sub] = m.get("score", 0)
        
    return {
        "attendancePercentage": round(att_perc, 1),
        "averageMarks": round(avg_marks, 1),
        "subjectMarks": sub_marks,
        "feeStatus": fee_status,
        "recentMarks": marks[:5]
    }

# ── Timetable ─────────────────────────────────────────────────────────────────

def add_timetable_entry(data: dict) -> dict:
    """
    Timetable Step 1: Strict relational validation
    """
    db = get_db()
    
    # 1. Enforce relations
    course_id = data.get("courseId")
    sem_id = data.get("semId")
    subject_id = data.get("subjectId")
    faculty_id = data.get("facultyId")
    
    if not all([course_id, sem_id, subject_id, faculty_id]):
        raise Exception("Relational IDs (courseId, semId, subjectId, facultyId) are required")

    # 2. Validation: Subject exists in Course structure
    course_ref = db.collection("courses").document(course_id)
    course_doc = course_ref.get()
    if not course_doc.exists: raise Exception("Course not found")
    course_data = course_doc.to_dict()

    sem_ref = course_ref.collection("semesters").document(sem_id)
    sem_doc = sem_ref.get()
    if not sem_doc.exists: raise Exception("Semester not found")
    sem_data = sem_doc.to_dict()

    sub_ref = sem_ref.collection("subjects").document(subject_id)
    sub_doc = sub_ref.get()
    if not sub_doc.exists:
        raise Exception(f"Subject {subject_id} not found in Course {course_id} | Semester {sem_id}")
    
    sub_data = sub_doc.to_dict()
    
    # 3. Validation: Faculty is assigned to the subject
    if sub_data.get("facultyId") != faculty_id:
        raise Exception(f"Faculty {faculty_id} is not assigned to teach {sub_data.get('subjectName') or subject_id}")

    # Set display names for easy table rendering and backward compatibility
    data["course"] = course_data.get("courseName")
    data["semester"] = str(sem_data.get("semesterNumber"))
    data["subject"] = sub_data.get("subjectName")
    data["subjectName"] = sub_data.get("subjectName")
    data["facultyName"] = sub_data.get("facultyName")
    
    ref = db.collection("timetables").document()
    data["id"] = ref.id
    data["createdAt"] = datetime.now().isoformat()
    ref.set(data)
    return data

def list_all_timetable() -> list[dict]:
    db = get_db()
    docs = db.collection("timetables").stream()
    return [{**d.to_dict(), "id": d.id} for d in docs]

def list_faculty_timetable(faculty_uid: str) -> list[dict]:
    db = get_db()
    docs = db.collection("timetables").where("facultyId", "==", faculty_uid).stream()
    return [{**d.to_dict(), "id": d.id} for d in docs]

def list_student_timetable(course: str, semester: str) -> list[dict]:
    db = get_db()
    docs = db.collection("timetables").where("course", "==", course).where("semester", "==", semester).stream()
    return [{**d.to_dict(), "id": d.id} for d in docs]

def update_timetable_entry(tid: str, data: dict, admin_uid: str) -> dict:
    db = get_db()
    ref = db.collection("timetables").document(tid)
    old_doc = ref.get()
    if not old_doc.exists: raise Exception("Timetable entry not found")
    old_data = old_doc.to_dict()
    
    # Validate changes if relational IDs are present in update
    new_data = {**old_data, **data}
    
    course_id = new_data.get("courseId")
    sem_id = new_data.get("semId")
    subject_id = new_data.get("subjectId")
    faculty_id = new_data.get("facultyId")
    
    # If any relational ID is changing, re-validate the chain
    if any(k in data for k in ["courseId", "semId", "subjectId", "facultyId"]):
        # Perform same validation as add_timetable_entry
        sub_doc = db.collection("courses").document(course_id)\
                    .collection("semesters").document(sem_id)\
                    .collection("subjects").document(subject_id).get()
        if not sub_doc.exists:
            raise Exception("Invalid subject/course mapping")
        
        sub_data = sub_doc.to_dict()
        if sub_data.get("facultyId") != faculty_id:
            raise Exception("Faculty mismatch for this subject")
            
        data["subjectName"] = sub_data.get("subjectName")
        data["facultyName"] = sub_data.get("facultyName")

    data["lastUpdatedAt"] = datetime.now().isoformat()
    data["updatedBy"] = admin_uid
    
    ref.update(data)
    # Save History
    ref.collection("history").add({
        "old": {k: old_data.get(k) for k in data.keys() if k in old_data},
        "new": data,
        "updatedBy": admin_uid,
        "timestamp": datetime.now().isoformat()
    })
    
    return {**data, "id": tid}

def delete_timetable_entry(tid: str):
    get_db().collection("timetables").document(tid).delete()

def check_timetable_conflicts(data: dict, exclude_id: str = None) -> list[str]:
    db = get_db()
    day = data.get("day")
    slot = data.get("timeSlot")
    faculty_id = data.get("facultyId")
    room = data.get("room")
    course = data.get("course")
    semester = data.get("semester")
    
    conflicts = []
    
    # Fetch all entries for the same day and slot
    query = db.collection("timetables").where("day", "==", day).where("timeSlot", "==", slot).stream()
    
    for d in query:
        entry = d.to_dict()
        if exclude_id and d.id == exclude_id: continue
        
        # 1. Faculty Conflict
        if entry.get("facultyId") == faculty_id:
            conflicts.append(f"Faculty {entry.get('facultyName')} already has a class in {slot}")
            
        # 2. Room Conflict
        if room and entry.get("room") == room:
            conflicts.append(f"Room {room} is already booked for {entry.get('subject')} ({entry.get('course')})")
            
        # 3. Course/Semester Conflict
        if entry.get("course") == course and entry.get("semester") == semester:
            conflicts.append(f"Course {course} (Sem {semester}) already has {entry.get('subject')} scheduled in this slot")
            
    return list(set(conflicts)) # Unique conflicts

# ── Materials & Assignments ───────────────────────────────────────────────────

def add_material(data: dict) -> dict:
    db = get_db()
    ref = db.collection("materials").document()
    data["id"] = ref.id
    ref.set(data)
    return data

def list_materials() -> list[dict]:
    docs = get_db().collection("materials").order_by("createdAt", direction=firestore.Query.DESCENDING).stream()
    return [d.to_dict() for d in docs]

def add_assignment(data: dict) -> dict:
    db = get_db()
    ref = db.collection("assignments").document()
    data["id"] = ref.id
    ref.set(data)
    return data

def list_assignments() -> list[dict]:
    db = get_db()
    docs = db.collection("assignments").order_by("createdAt", direction=firestore.Query.DESCENDING).get()
    
    # ── UID TO NAME CACHE ───────────────────────────────────────────────────
    # We cache user names to avoid repeated Firestore lookups for the same UID
    user_cache = {}
    assignments = []
    
    for d in docs:
        data = d.to_dict()
        uid = data.get("createdBy")
        
        if uid:
            if uid not in user_cache:
                u_doc = db.collection("users").document(uid).get()
                user_cache[uid] = u_doc.to_dict().get("name", "System") if u_doc.exists else "Unknown"
            
            data["ownerName"] = user_cache[uid]
        else:
            data["ownerName"] = "System"
            
        assignments.append(data)
        
    return assignments

def get_assignment(assignment_id: str) -> dict | None:
    doc = get_db().collection("assignments").document(assignment_id).get()
    return doc.to_dict() if doc.exists else None

def submit_assignment(assignment_id: str, data: dict) -> dict:
    db = get_db()
    ref = db.collection("assignments").document(assignment_id).collection("submissions").document(data["studentId"])
    data["id"] = data["studentId"]
    ref.set(data)
    return data

def list_submissions(assignment_id: str) -> list[dict]:
    docs = get_db().collection("assignments").document(assignment_id).collection("submissions").stream()
    return [{**d.to_dict(), "studentId": d.id} for d in docs]

def grade_submission(assignment_id: str, student_id: str, marks: float, feedback: str, graded_by: str) -> dict:
    db = get_db()
    ref = db.collection("assignments").document(assignment_id).collection("submissions").document(student_id)
    doc = ref.get()
    if not doc.exists:
        raise Exception("Submission not found")
        
    data = {"marksAwarded": marks, "feedback": feedback, "gradedBy": graded_by, "gradedAt": datetime.now().isoformat(), "status": "graded"}
    ref.update(data)
    
    # ── SYNC WITH MARKS REGISTRY ──────────────────────────────────────────────
    # We also add this to the student's general marks list for global reporting
    assignment = db.collection("assignments").document(assignment_id).get().to_dict()
    student = db.collection("students").document(student_id).get().to_dict()
    
    mark_record = {
        "studentId": student_id,
        "studentName": student.get("name", "Student"),
        "subject": assignment.get("subjectName", "General"),
        "examType": f"Assignment: {assignment.get('title', 'Task')}",
        "score": float(marks),
        "maxMarks": float(assignment.get("maxMarks", 100)),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "uploadedBy": graded_by,
        "timestamp": datetime.now().isoformat()
    }
    
    # Use existing add_mark function logic
    db.collection("marks").document(student_id).collection("studentMarks").document().set(mark_record)
    
    return {**data, "id": student_id}

# ── NEW LEDGER-BASED FEES SYSTEM ──────────────────────────────────────────────

def create_fee_record(student_id: str, data: dict) -> dict:
    """
    Admin: Creates a new semester/year fee record.
    fees/{studentId}/feeRecords/{recordId}
    """
    db = get_db()
    student = db.collection("students").document(student_id).get()
    if not student.exists: raise Exception("Student not found")
    
    s_data = student.to_dict()
    
    # Root doc (ensure it exists)
    root_ref = db.collection("fees").document(student_id)
    if not root_ref.get().exists:
        root_ref.set({
            "studentId": student_id,
            "studentName": s_data.get("name"),
            "courseId": s_data.get("course")
        })

    record_ref = root_ref.collection("feeRecords").document()
    
    record = {
        "recordId": record_ref.id,
        "semester": int(data.get("semester", 1)),
        "academicYear": data.get("academicYear"),
        "totalAmount": float(data.get("totalAmount", 0)),
        "paidAmount": 0.0,
        "pendingAmount": float(data.get("totalAmount", 0)),
        "status": "unpaid",
        "dueDate": data.get("dueDate"),
        "lastUpdatedDueDate": data.get("dueDate"),
        "gracePeriodDays": int(data.get("gracePeriodDays", 0)),
        "penaltyAmount": 0.0,
        "penaltyApplied": False,
        "penaltyType": data.get("penaltyType", "fixed"), # "fixed" | "per-day"
        "penaltyRate": float(data.get("penaltyRate", 0)),
        "createdAt": datetime.now().isoformat()
    }
    
    record_ref.set(record)
    return record

def submit_fee_transaction(student_id: str, record_id: str, data: dict) -> dict:
    """
    Student: Adds a transaction entry to a specific fee record.
    fees/{studentId}/feeRecords/{recordId}/transactions/{txnId}
    """
    db = get_db()
    txn_ref = db.collection("fees").document(student_id)\
                .collection("feeRecords").document(record_id)\
                .collection("transactions").document()
    
    txn = {
        "txnId": txn_ref.id,
        "amountPaid": float(data.get("amount", 0)),
        "paymentDate": datetime.now().isoformat(),
        "paymentMethod": data.get("paymentMethod", "Online"),
        "status": "pending",
        "notes": data.get("notes", ""),
        "proofUrl": data.get("proofUrl", "")
    }
    
    txn_ref.set(txn)
    
    # Optionally update record status to pending
    db.collection("fees").document(student_id)\
      .collection("feeRecords").document(record_id)\
      .update({"status": "pending"})
      
    return txn

def approve_fee_transaction(student_id: str, record_id: str, txn_id: str, admin_uid: str):
    """
    Admin: Approves a transaction. Updates parent record totals.
    """
    db = get_db()
    record_ref = db.collection("fees").document(student_id)\
                   .collection("feeRecords").document(record_id)
    txn_ref = record_ref.collection("transactions").document(txn_id)
    
    txn_doc = txn_ref.get()
    if not txn_doc.exists: raise Exception("Transaction not found")
    
    txn_data = txn_doc.to_dict()
    if txn_data.get("status") == "approved": return # Already done

    # 1. Update Transaction
    txn_ref.update({
        "status": "approved",
        "approvedBy": admin_uid,
        "approvedAt": datetime.now().isoformat()
    })
    
    # 2. Update Record Totals
    record_doc = record_ref.get()
    rec_data = record_doc.to_dict()
    
    new_paid = rec_data.get("paidAmount", 0) + txn_data.get("amountPaid", 0)
    new_pending = max(0, (rec_data.get("totalAmount", 0) + rec_data.get("penaltyAmount", 0)) - new_paid)
    
    status = "partial" if new_pending > 0 else "paid"
    
    record_ref.update({
        "paidAmount": new_paid,
        "pendingAmount": new_pending,
        "status": status
    })
    
    return {"paidAmount": new_paid, "pendingAmount": new_pending, "status": status}

def get_fee_ledger(student_id: str) -> list[dict]:
    """
    Returns FULL structure including records and their nested transactions.
    Also runs the penalty engine on the fly.
    """
    db = get_db()
    records = db.collection("fees").document(student_id)\
                .collection("feeRecords").order_by("createdAt", direction=firestore.Query.DESCENDING).get()
    
    ledger = []
    now = datetime.now()
    
    for rec in records:
        r_data = rec.to_dict()
        rid = rec.id
        
        # PENALTY ENGINE
        # If overdue and not fully paid, calculate penalty
        due_date_str = r_data.get("dueDate")
        if due_date_str and r_data.get("status") != "paid":
            try:
                due_date = datetime.fromisoformat(due_date_str)
                grace_period = r_data.get("gracePeriodDays", 0)
                penalty_start = due_date + timedelta(days=grace_period)
                
                if now > penalty_start:
                    days_late = (now - penalty_start).days
                    penalty = 0.0
                    if r_data.get("penaltyType") == "fixed":
                        penalty = float(r_data.get("penaltyRate", 0))
                    else: # per-day
                        penalty = days_late * float(r_data.get("penaltyRate", 0))
                    
                    if penalty > r_data.get("penaltyAmount", 0):
                        r_data["penaltyAmount"] = penalty
                        r_data["penaltyApplied"] = True
                        r_data["status"] = "overdue"
                        r_data["pendingAmount"] = (r_data["totalAmount"] + penalty) - r_data["paidAmount"]
                        # Update DB
                        rec.reference.update({
                            "penaltyAmount": penalty,
                            "penaltyApplied": True,
                            "status": "overdue",
                            "pendingAmount": r_data["pendingAmount"]
                        })
            except Exception as e:
                print(f"DEBUG: Penalty calc failed for {rid}: {e}")

        txns = db.collection("fees").document(student_id)\
                 .collection("feeRecords").document(rid)\
                 .collection("transactions").get()
        
        r_data["transactions"] = [t.to_dict() for t in txns]
        ledger.append(r_data)
        
    return ledger

def list_all_overdue_records():
    """
    Scans across all students for overdue records.
    """
    db = get_db()
    all_fees = db.collection("fees").get()
    overdue = []
    
    for f in all_fees:
        sid = f.id
        ledger = get_fee_ledger(sid)
        for item in ledger:
            if item.get("status") == "overdue":
                overdue.append({**item, "studentId": sid})
                
    return overdue

def update_assignment(aid, data, user_uid):
    db = get_db()
    ref = db.collection("assignments").document(aid)
    if not ref.get().exists: raise Exception("Assignment not found")
    data["lastUpdatedAt"] = datetime.now().isoformat()
    data["updatedBy"] = user_uid
    ref.update(data)
    return {**data, "id": aid}

def update_material(mid, data, user_uid):
    db = get_db()
    ref = db.collection("materials").document(mid)
    if not ref.get().exists: raise Exception("Material not found")
    data["lastUpdatedAt"] = datetime.now().isoformat()
    data["updatedBy"] = user_uid
    ref.update(data)
    return {**data, "id": mid}
