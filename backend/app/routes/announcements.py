from flask import Blueprint, request, jsonify, g
from app.middleware.auth import verify_token, require_role
from app.services.firestore_service import (
    add_announcement,
    list_all_announcements,
    list_student_announcements,
    update_announcement,
    get_announcement,
    delete_announcement_record
)
from datetime import datetime

announcements_bp = Blueprint("announcements", __name__)

@announcements_bp.route("/", methods=["POST"]) # create
@verify_token
@require_role("admin", "faculty")
def create_ann():
    data = request.json
    data["createdBy"] = g.uid
    data["createdByRole"] = g.user_data.get("role")
    
    # Defaults
    if "isActive" not in data: data["isActive"] = True
    if "priority" not in data: data["priority"] = "Low"
    if "createdAt" not in data: data["createdAt"] = datetime.now().isoformat()
    
    try:
        res = add_announcement(data)
        return jsonify(res), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@announcements_bp.route("/", methods=["GET"]) # list (role-based)
@verify_token
def get_ann_list():
    try:
        role = g.user_data.get("role")
        if role == "student":
            res = list_student_announcements(g.uid)
        else:
            res = list_all_announcements()
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@announcements_bp.route("/view", methods=["GET"]) # single retrieve
@verify_token
@require_role("admin", "faculty")
def get_single():
    ann_id = request.args.get("id")
    if not ann_id: return jsonify({"error": "id required"}), 400
    try:
        res = get_announcement(ann_id)
        if not res: return jsonify({"error": "Not found"}), 404
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Combined into '/'

@announcements_bp.route("/", methods=["PUT"]) # edit
@verify_token
@require_role("admin", "faculty")
def edit_ann():
    data = request.json
    ann_id = data.get("id")
    if not ann_id: return jsonify({"error": "id required"}), 400
    
    # Ownership Check for Faculty
    if g.user_data.get("role") == "faculty":
        existing = get_announcement(ann_id)
        if not existing: return jsonify({"error": "Not found"}), 404
        if existing.get("createdBy") != g.uid:
            return jsonify({"error": "Unauthorized: You can only edit your own announcements"}), 403

    try:
        data.pop('id', None) # Don't update internal ID field if sent
        res = update_announcement(ann_id, data, g.uid)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@announcements_bp.route("/", methods=["DELETE"]) # delete
@verify_token
@require_role("admin")
def delete_ann():
    ann_id = request.args.get("id")
    if not ann_id: return jsonify({"error": "id required"}), 400
    try:
        delete_announcement_record(ann_id)
        return jsonify({"message": "Announcement deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@announcements_bp.route("/seed", methods=["POST"])
@verify_token
@require_role("admin")
def seed_ann():
    mock_data = [
        {"title": "Welcome to Semester 2", "message": "Good luck to all students for the upcoming term!", "targetAudience": "all", "priority": "Medium", "isActive": True},
        {"title": "CS Exam Postponed", "message": "The CS midterm is moved to next Monday.", "targetAudience": "specificCourse", "course": "B.Tech CS", "priority": "High", "isActive": True},
        {"title": "Fee Deadline Extended", "message": "You now have until the end of the month.", "targetAudience": "students", "priority": "High", "isActive": True},
        {"title": "Library Closure", "message": "Library will be closed this Sunday.", "targetAudience": "all", "priority": "Low", "isActive": True},
        {"title": "Old Event", "message": "This event is over.", "targetAudience": "all", "priority": "Low", "isActive": True, "expiryDate": "2024-01-01T00:00:00"}
    ]
    count = 0
    for ann in mock_data:
        ann["createdBy"] = g.uid
        ann["createdByRole"] = "admin"
        add_announcement(ann)
        count += 1
    return jsonify({"message": f"Seeded {count} announcements"})
