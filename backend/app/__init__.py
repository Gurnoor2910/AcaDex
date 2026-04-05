"""
Acadex - Student ERP System
Flask Application Factory
"""

import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import HTTPException


def create_app():
    """Create and configure the Flask application."""
    backend_dir = Path(__file__).resolve().parents[1]
    project_root = backend_dir.parent
    frontend_dir = project_root / "frontend"

    app = Flask(
        __name__,
        static_folder=str(frontend_dir),
        static_url_path="",
    )

    cors_origins_env = os.environ.get("CORS_ORIGINS")
    if cors_origins_env and cors_origins_env.strip():
        allowed_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
    else:
        allowed_origins = "*"

    CORS(
        app,
        resources={
            r"/*": {
                "origins": allowed_origins,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": "*",
            }
        },
        supports_credentials=True,
    )

    if not firebase_admin._apps:
        service_account_path = os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS",
            str(backend_dir / "serviceAccountKey.json"),
        )
        print(f"DEBUG: Using credentials from: {service_account_path}")
        try:
            cred = credentials.Certificate(service_account_path)
        except Exception:
            cred = credentials.ApplicationDefault()

        firebase_admin.initialize_app(
            cred,
            {"projectId": os.environ.get("FIREBASE_PROJECT_ID", "acadex-2a0ae")},
        )

    from app.routes.admin import admin_bp
    from app.routes.announcements import announcements_bp
    from app.routes.assignments import assignments_bp
    from app.routes.attendance import attendance_bp
    from app.routes.auth import auth_bp
    from app.routes.courses import courses_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.faculty import faculty_bp
    from app.routes.fees import fees_bp
    from app.routes.materials import materials_bp
    from app.routes.marks import marks_bp
    from app.routes.seed import seed_bp
    from app.routes.student import student_bp
    from app.routes.timetable import timetable_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(faculty_bp, url_prefix="/api/faculty")
    app.register_blueprint(student_bp, url_prefix="/api/student")
    app.register_blueprint(attendance_bp, url_prefix="/api/attendance")
    app.register_blueprint(marks_bp, url_prefix="/api/marks")
    app.register_blueprint(fees_bp, url_prefix="/api/fees")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(announcements_bp, url_prefix="/api/announcements")
    app.register_blueprint(timetable_bp, url_prefix="/api/timetable")
    app.register_blueprint(courses_bp, url_prefix="/api/courses")
    app.register_blueprint(materials_bp, url_prefix="/api/materials")
    app.register_blueprint(assignments_bp, url_prefix="/api/assignments")
    app.register_blueprint(seed_bp, url_prefix="/api/seed")

    @app.route("/health")
    def health():
        return {"status": "ok", "service": "Acadex ERP"}, 200

    @app.route("/")
    def serve_index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/<path:path>")
    def serve_frontend(path):
        if path.startswith("api/") or path == "health":
            return (
                jsonify({"error": "Not Found", "message": f"Route '/{path}' does not exist"}),
                404,
            )

        target = Path(app.static_folder) / path
        if target.exists() and target.is_file():
            return send_from_directory(app.static_folder, path)

        if target.suffix:
            return jsonify({"error": "Not Found", "message": f"Asset '/{path}' does not exist"}), 404

        return send_from_directory(app.static_folder, "index.html")

    @app.errorhandler(500)
    def handle_500(e):
        import traceback

        traceback.print_exc()
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        if isinstance(e, HTTPException):
            return jsonify({"error": e.name, "message": e.description}), e.code

        import traceback

        traceback.print_exc()
        return jsonify({"error": "Unhandled Exception", "message": str(e)}), 500

    return app
