import random
import uuid
from datetime import datetime, timedelta
from firebase_admin import firestore, auth
from app.services import firestore_service

class SeederService:
    def __init__(self):
        self._db = firestore.client()
        self.password = "Password123"

    def clear_all_data(self):
        """Clears all relevant collections and subcollections."""
        # 1. Students (includes attendance, marks, fees subcollections)
        student_docs = self._db.collection("students").stream()
        for doc in student_docs:
            firestore_service.delete_student(doc.id)

        # 2. Users (excluding any core system users if needed, but here we clear all)
        user_docs = self._db.collection("users").stream()
        for doc in user_docs:
            self._db.collection("users").document(doc.id).delete()

        # 3. Courses (need to clear subcollections semesters -> subjects)
        course_docs = self._db.collection("courses").stream()
        for doc in course_docs:
            # Manually clear subcollections
            sems = self._db.collection("courses").document(doc.id).collection("semesters").stream()
            for sem in sems:
                subs = self._db.collection("courses").document(doc.id).collection("semesters").document(sem.id).collection("subjects").stream()
                for sub in subs:
                    sub.reference.delete()
                sem.reference.delete()
            doc.reference.delete()

        # 4. Timetable
        tt_docs = self._db.collection("timetable").stream()
        for doc in tt_docs:
            doc.reference.delete()

        # 5. Announcements
        ann_docs = self._db.collection("announcements").stream()
        for doc in ann_docs:
            doc.reference.delete()

        # 6. Assignments & Materials
        asgn_docs = self._db.collection("assignments").stream()
        for doc in asgn_docs:
            # Clear submissions
            subs = doc.reference.collection("submissions").stream()
            for s in subs: s.reference.delete()
            doc.reference.delete()

        mat_docs = self._db.collection("materials").stream()
        for doc in mat_docs:
            doc.reference.delete()

    def _get_or_create_user(self, email, name, role):
        try:
            user = auth.get_user_by_email(email)
            uid = user.uid
        except auth.UserNotFoundError:
            user = auth.create_user(email=email, display_name=name, password=self.password)
            uid = user.uid
        
        user_data = {
            "uid": uid,
            "name": name,
            "email": email,
            "role": role,
            "createdAt": firestore.SERVER_TIMESTAMP
        }
        self._db.collection("users").document(uid).set(user_data)
        return uid

    def seed_all(self, mode="full", progress_callback=None):
        """Main seeding logic."""
        steps = []
        def report(msg):
            steps.append(msg)
            if progress_callback: progress_callback(msg)
            print(f"[SEEDER] {msg}")

        # Config based on mode
        num_faculty = 8 if mode == "full" else 3
        num_students = 30 if mode == "full" else 10
        attendance_days = 15 if mode == "full" else 5

        # 1. USERS
        report("Creating Users (Admin, Faculty, Students)...")
        # Admin
        admin_uid = self._get_or_create_user("admin@acadex.com", "System Admin", "admin")
        
        # Faculty
        faculty_names = [
            "Dr. Alan Turing", "Prof. Grace Hopper", "Dr. Richard Feynman", 
            "Prof. Marie Curie", "Dr. Ada Lovelace", "Prof. Nikola Tesla",
            "Dr. Albert Einstein", "Prof. Stephen Hawking"
        ][:num_faculty]
        faculty_ids = []
        for name in faculty_names:
            email = f"{name.lower().replace(' ', '.').replace('.', '', 1)}@acadex.edu"
            uid = self._get_or_create_user(email, name, "faculty")
            faculty_ids.append(uid)
        
        # 2. COURSES, SEMESTERS, SUBJECTS
        report("Building Courses, Semesters, and Subjects...")
        courses_config = {
            "BCA": {"name": "Bachelor of Computer Applications", "sems": 6},
            "BBA": {"name": "Bachelor of Business Administration", "sems": 6}
        }
        
        course_map = {} # {short_name: {id: cid, semesters: {num: {id: sid, subjects: [subids]}}}}
        
        subjects_pool = {
            "BCA": ["Data Structures", "Web Development", "Database Systems", "Operating Systems", "Networking", "Software Engineering", "AI Basics", "Python Programming", "Java Core", "Cloud Computing"],
            "BBA": ["Principles of Management", "Business Economics", "Financial Accounting", "Marketing", "Organizational Behavior", "Human Resource", "Business Law", "Statistics", "Entrepreneurship", "Strategic Management"]
        }

        for code, info in courses_config.items():
            c_data = {
                "courseName": info["name"],
                "courseCode": code,
                "description": f"Standard {code} undergraduate program.",
                "durationYears": info["sems"] // 2
            }
            course_ref = firestore_service.add_course(c_data)
            cid = course_ref["id"]
            course_map[code] = {"id": cid, "semesters": {}}
            
            for s_num in range(1, info["sems"] + 1):
                sem_ref = firestore_service.add_semester(cid, s_num)
                sid = sem_ref["id"]
                course_map[code]["semesters"][s_num] = {"id": sid, "subjects": []}
                
                # Add 4-6 subjects per semester
                num_subs = random.randint(4, 6)
                chosen_subs = random.sample(subjects_pool[code], min(num_subs, len(subjects_pool[code])))
                for sub_name in chosen_subs:
                    sub_code = f"{code}{s_num}0{chosen_subs.index(sub_name)+1}"
                    # Assign a random faculty
                    f_id = random.choice(faculty_ids)
                    f_name = next(name for name, fid in zip(faculty_names, faculty_ids) if fid == f_id)
                    
                    sub_data = {
                        "subjectName": sub_name,
                        "subjectCode": sub_code,
                        "credits": random.choice([3, 4]),
                        "facultyId": f_id,
                        "facultyName": f_name
                    }
                    sub_ref = firestore_service.add_subject(cid, sid, sub_data)
                    course_map[code]["semesters"][s_num]["subjects"].append({
                        "id": sub_ref["id"],
                        "name": sub_name,
                        "code": sub_code,
                        "facultyId": f_id,
                        "facultyName": f_name
                    })

        # 3. STUDENTS
        report(f"Seeding {num_students} Students and assigning courses...")
        student_names = [
            "Alice Johnson", "Bob Smith", "Charlie Brown", "Diana Prince", "Ethan Hunt",
            "Fiona Gallagher", "George Weasley", "Hannah Montana", "Ian Somerhalder", "Jenny Plaza",
            "Kevin Hart", "Lara Croft", "Michael Scott", "Nina Dobrev", "Oscar Isaac",
            "Peter Parker", "Quinn Fabray", "Riley Reid", "Sarah Connor", "Tony Stark",
            "Ursula Corbero", "Victor Stone", "Wanda Maximoff", "Xavier Renegade", "Yara Shahidi", "Zane Malik",
            "Arthur Morgan", "Billie Eilish", "Casper Ghost", "Daisy Ridley", "Elliot Page"
        ][:num_students]

        student_ids = []
        for name in student_names:
            email = f"{name.lower().replace(' ', '.')}@student.acadex.edu"
            uid = self._get_or_create_user(email, name, "student")
            
            # Select random course and semester
            c_code = random.choice(list(course_map.keys()))
            c_info = course_map[c_code]
            s_num = random.randint(1, 6)
            s_info = c_info["semesters"][s_num]
            
            s_record = {
                "uid": uid,
                "name": name,
                "email": email,
                "course": c_info["id"], # Store Course ID
                "courseName": c_code,
                "semester": s_num,
                "section": random.choice(["A", "B"]),
                "rollNumber": f"{c_code}2024{num_students+student_names.index(name)}",
                "totalFees": random.choice([45000, 55000, 65000]),
                "pendingAmount": 0,
                "feesPaid": False,
                "facultyAssigned": faculty_ids[0] # Default
            }
            firestore_service.create_student(uid, s_record)
            # Update user record with role-specific fields
            self._db.collection("users").document(uid).update({
                "courseId": c_info["id"],
                "semester": s_num
            })
            student_ids.append({"uid": uid, "course": c_code, "sem": s_num, "cid": c_info["id"], "sid": s_info["id"]})

        # 4. FACULTY ASSIGNMENTS
        report("Finalizing Faculty Assignments...")
        # (Subjects already have faculty assigned, but users collection might need 'assignedCourses')
        for fid in faculty_ids:
            # Find what courses this faculty is teaching
            assigned_cids = set()
            for c_code, c_data in course_map.items():
                for s_num, s_data in c_data["semesters"].items():
                    for sub in s_data["subjects"]:
                        if sub["facultyId"] == fid:
                            assigned_cids.add(c_data["id"])
            
            self._db.collection("users").document(fid).update({
                "assignedCourses": list(assigned_cids),
                "department": random.choice(["Applied Sciences", "Information Technology", "Business Studies"])
            })

        # 5. TIMETABLE
        report("Generating conflict-free Timetable...")
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        slots = ["09:00 - 10:00", "10:00 - 11:00", "11:15 - 12:15", "12:15 - 01:15", "02:00 - 03:00"]
        rooms = ["L-101", "L-102", "L-201", "L-202", "Lab-A", "Lab-B"]
        
        # We need to create a timetable for each (Course + Semester)
        for c_code, c_data in course_map.items():
            for s_num, s_data in c_data["semesters"].items():
                subjects = s_data["subjects"]
                if not subjects: continue
                
                for day in days:
                    # Fill 4 slots per day
                    chosen_subs = random.sample(subjects * 2, len(slots)-1) # allow repeat
                    for i, slot in enumerate(slots[:-1]):
                        sub = chosen_subs[i]
                        tt_entry = {
                            "course": c_code,
                            "courseId": c_data["id"],
                            "semester": s_num,
                            "subject": sub["name"],
                            "subjectId": sub["id"],
                            "faculty": sub["facultyName"],
                            "facultyId": sub["facultyId"],
                            "day": day,
                            "timeSlot": slot,
                            "room": random.choice(rooms)
                        }
                        self._db.collection("timetable").add(tt_entry)

        # 6. ATTENDANCE
        report(f"Seeding Attendance for the last {attendance_days} days...")
        today = datetime.now()
        for d_offset in range(attendance_days):
            date_str = (today - timedelta(days=d_offset)).strftime("%Y-%m-%d")
            # Skip Sundays
            if (today - timedelta(days=d_offset)).weekday() == 6: continue
            
            for s_info in student_ids:
                # Get subjects for this student's sem
                subjects = course_map[s_info["course"]]["semesters"][s_info["sem"]]["subjects"]
                for sub in subjects[:3]: # Mark 3 subjects per day
                    status = random.choices(["present", "absent"], weights=[0.85, 0.15])[0]
                    record = {
                        "date": date_str,
                        "subject": sub["name"],
                        "status": status,
                        "markedBy": sub["facultyId"],
                        "teacherName": sub["facultyName"],
                        "timestamp": datetime.now().isoformat()
                    }
                    firestore_service.mark_attendance(s_info["uid"], record)

        # 7. MARKS
        report("Populating student Marks...")
        exams = ["Sessional 1", "Sessional 2", "Final Exam"]
        for s_info in student_ids:
            subjects = course_map[s_info["course"]]["semesters"][s_info["sem"]]["subjects"]
            for sub in subjects:
                for exam in exams:
                    score = random.randint(55, 98) if exam != "Final Exam" else random.randint(45, 95)
                    mark_data = {
                        "subject": sub["name"],
                        "subjectId": sub["id"],
                        "examType": exam,
                        "score": float(score),
                        "maxMarks": 100.0,
                        "date": (today - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
                        "teacherName": sub["facultyName"]
                    }
                    firestore_service.add_mark(s_info["uid"], mark_data)

        # 8. FEES
        report("Simulating Fee transactions...")
        for s_info in student_ids:
            s_ref = self._db.collection("students").document(s_info["uid"])
            s_data = s_ref.get().to_dict()
            total = s_data.get("totalFees", 50000)
            
            # 70% chance they paid something
            if random.random() < 0.7:
                paid_amount = random.choice([total, total * 0.5, total * 0.8, 15000])
                payment = {
                    "amountPaid": float(paid_amount),
                    "paymentDate": (today - timedelta(days=random.randint(5, 60))).isoformat(),
                    "paymentMode": random.choice(["UPI", "Net Banking", "Cash"]),
                    "remarks": "Term Fees"
                }
                firestore_service.add_fee_payment(s_info["uid"], payment)

        # 9. ANNOUNCEMENTS
        report("Creating Announcements...")
        ann_titles = [
            ("Holiday Notice", "All students", "High"),
            ("Exam Schedule Out", "students", "High"),
            ("New Library Timings", "all", "Medium"),
            ("Workshop on AI", "BCA", "Medium"),
            ("Guest Lecture: Business Ethics", "BBA", "Medium"),
            ("Annual Sports Meet", "all", "Low")
        ]
        for title, target, prio in ann_titles:
            ann_data = {
                "title": title,
                "content": f"Important announcement regarding {title}. Please check the notice board.",
                "priority": prio,
                "targetAudience": "specificCourse" if target in courses_config else target,
                "course": target if target in courses_config else None,
                "isActive": True,
                "expiryDate": (today + timedelta(days=30)).isoformat(),
                "author": "Admin",
                "createdAt": today.isoformat()
            }
            firestore_service.add_announcement(ann_data)

        # 10. ASSIGNMENTS + MATERIALS
        report("Adding Materials and Assignments...")
        for c_code, c_data in course_map.items():
            for s_num, s_data in c_data["semesters"].items():
                for sub in s_data["subjects"]:
                    # 1 Material
                    mat_data = {
                        "title": f"{sub['name']} Lecture Notes",
                        "description": f"Complete notes for Unit 1 and 2 of {sub['name']}.",
                        "course": c_code,
                        "courseId": c_data["id"],
                        "semester": s_num,
                        "subject": sub["name"],
                        "subjectId": sub["id"],
                        "fileUrl": "https://example.com/notes.pdf",
                        "uploadedBy": sub["facultyId"],
                        "facultyName": sub["facultyName"],
                        "createdAt": today.isoformat()
                    }
                    self._db.collection("materials").add(mat_data)
                    
                    # 1 Assignment
                    asgn_ref = self._db.collection("assignments").document()
                    asgn_data = {
                        "title": f"{sub['name']} Assignment 1",
                        "description": f"Submit questions 1-5 from chapter 2.",
                        "course": c_code,
                        "courseId": c_data["id"],
                        "semester": s_num,
                        "subject": sub["name"],
                        "subjectId": sub["id"],
                        "dueDate": (today + timedelta(days=7)).strftime("%Y-%m-%d"),
                        "maxMarks": 20,
                        "uploadedBy": sub["facultyId"],
                        "facultyName": sub["facultyName"],
                        "createdAt": today.isoformat(),
                        "id": asgn_ref.id
                    }
                    asgn_ref.set(asgn_data)
                    
                    # Random submissions for this assignment
                    relevant_students = [s for s in student_ids if s["course"] == c_code and s["sem"] == s_num]
                    for r_stud in relevant_students[:3]: # Only a few submitted
                        sub_data = {
                            "studentId": r_stud["uid"],
                            "studentName": next(name for name, uid in zip(student_names, [s["uid"] for s in student_ids]) if uid == r_stud["uid"]),
                            "submittedAt": today.isoformat(),
                            "fileUrl": "https://example.com/submission.pdf",
                            "status": "Submitted",
                            "marksObtained": None
                        }
                        asgn_ref.collection("submissions").document(r_stud["uid"]).set(sub_data)

        report("✨ SEEDING COMPLETE!")
        return steps
