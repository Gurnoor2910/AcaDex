from flask import Blueprint, request, jsonify, g
from app.services.firestore_service import (
    create_fee_record, submit_fee_transaction, approve_fee_transaction, 
    get_fee_ledger, list_all_overdue_records
)
from app.middleware.auth import verify_token, require_role
import random
from datetime import datetime, timedelta
from flask_cors import CORS

fees_bp = Blueprint("fees", __name__)
CORS(fees_bp)

# ── New Payment Workflow ───────────────────────────────────────────────────

@fees_bp.route("/create-record", methods=["POST"])
@verify_token
@require_role("admin")
def create_record_route():
    data = request.json
    student_id = data.get("studentId")
    if not student_id: return jsonify({"error": "studentId required"}), 400
    try:
        res = create_fee_record(student_id, data)
        return jsonify(res), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@fees_bp.route("/pay", methods=["POST"])
@verify_token
@require_role("student")
def pay_ledger_fee():
    data = request.json
    record_id = data.get("recordId")
    if not record_id: return jsonify({"error": "recordId required"}), 400
    try:
        res = submit_fee_transaction(g.uid, record_id, data)
        return jsonify(res), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@fees_bp.route("/approve-transaction", methods=["PUT"])
@verify_token
@require_role("admin")
def approve_txn_route():
    data = request.json
    student_id = data.get("studentId")
    record_id = data.get("recordId")
    txn_id = data.get("txnId")
    if not all([student_id, record_id, txn_id]):
        return jsonify({"error": "studentId, recordId and txnId required"}), 400
    try:
        res = approve_fee_transaction(student_id, record_id, txn_id, g.uid)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@fees_bp.route("/history", methods=["GET"])
@verify_token
def get_ledger_history():
    student_id = request.args.get("studentId")
    if g.user_data.get("role") == "student":
        student_id = g.uid
    if not student_id: return jsonify({"error": "studentId required"}), 400
    
    try:
        res = get_fee_ledger(student_id)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@fees_bp.route("/overdue", methods=["GET"])
@verify_token
@require_role("admin")
def list_overdue():
    try:
        res = list_all_overdue_records()
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@fees_bp.route("/seed", methods=["POST"])
@verify_token
@require_role("admin")
def seed_fees():
    """
    Seed script for the Fees Module.
    Assigns total fees and 1-3 transactions for every student.
    """
    try:
        students = list_students()
        count = 0
        
        for s in students:
            sid = s["uid"]
            # 1. Assign Total Fees (50k to 1.2L)
            total = random.choice([50000, 65000, 80000, 100000, 120000])
            update_student_total_fees(sid, total)
            
            # 2. Decide payment status
            status = random.choice(["full", "partial", "none"])
            
            if status == "none":
                continue
            
            if status == "full":
                # Paid in two installments or one
                inst = random.randint(1, 2)
                if inst == 1:
                    add_fee_payment(sid, {
                        "amountPaid": total,
                        "paymentDate": (datetime.now() - timedelta(days=random.randint(30, 90))).isoformat(),
                        "paymentMode": random.choice(["UPI", "Card"]),
                        "receivedBy": g.uid
                    })
                else:
                    h1 = total / 2
                    add_fee_payment(sid, {
                        "amountPaid": h1,
                        "paymentDate": (datetime.now() - timedelta(days=90)).isoformat(),
                        "paymentMode": "Bank Transfer",
                        "receivedBy": g.uid
                    })
                    add_fee_payment(sid, {
                        "amountPaid": h1,
                        "paymentDate": (datetime.now() - timedelta(days=30)).isoformat(),
                        "paymentMode": "UPI",
                        "receivedBy": g.uid
                    })
            
            if status == "partial":
                # Paid about 40-70%
                paid = total * random.uniform(0.4, 0.7)
                add_fee_payment(sid, {
                    "amountPaid": round(paid, -2),
                    "paymentDate": (datetime.now() - timedelta(days=20)).isoformat(),
                    "paymentMode": random.choice(["Cash", "UPI"]),
                    "receivedBy": g.uid
                })
            
            count += 1
            
        return jsonify({"message": f"Successfully seeded fees for {count} students"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
