from flask import Blueprint, request, jsonify, g
from app.middleware.auth import verify_token, require_role
from app.services.firestore_service import add_material, list_materials
from datetime import datetime

materials_bp = Blueprint("materials", __name__)

@materials_bp.route("/add", methods=["POST"])
@verify_token
@require_role("admin", "faculty")
def create_material():
    data = request.json
    try:
        material_record = {
            "title": data.get("title"),
            "description": data.get("description", ""),
            "subjectId": data.get("subjectId"),
            "subjectName": data.get("subjectName"),
            "courseId": data.get("courseId"),
            "semester": data.get("semester"),
            "uploadedBy": g.uid,
            "fileUrl": data.get("fileUrl"),
            "createdAt": datetime.now().isoformat()
        }
        res = add_material(material_record)
        return jsonify(res), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@materials_bp.route("/", methods=["GET"])
@verify_token
def get_materials():
    try:
        data = list_materials()
        return jsonify(data), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@materials_bp.route("/delete", methods=["DELETE"])
@verify_token
@require_role("admin", "faculty")
def delete_material_route():
    try:
        mat_id = request.args.get("id")
        if not mat_id: return jsonify({"error": "id required"}), 400
        
        from app.services.firestore_service import get_db
        db = get_db()
        db.collection("materials").document(mat_id).delete()
        
        return jsonify({"message": "Material deleted"}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
@materials_bp.route("/edit", methods=["PUT"])
@verify_token
@require_role("admin", "faculty")
def edit_material_route():
    data = request.json
    mid = data.get("id")
    if not mid: return jsonify({"error": "id required"}), 400
    try:
        from app.services.firestore_service import update_material
        data.pop('id', None)
        update_material(mid, data, g.uid)
        return jsonify({"message": "Material updated"}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
