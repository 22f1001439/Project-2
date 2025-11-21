from flask import Flask, request, jsonify
import time
from quiz_solver import solve_full_quiz

app = Flask(__name__)

EXPECTED_SECRET = "iitm"


@app.route("/")
def home():
    return jsonify({
        "message": "Quiz Solver API",
        "status": "running",
        "endpoints": {
            "POST /quiz": "Submit a quiz solving request"
        }
    })


@app.route("/quiz", methods=["POST"])
def quiz():
    # 1. Try to parse JSON
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    # 2. Check required fields
    required = ["email", "secret", "url"]
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({
            "error": "Missing fields",
            "missing": missing
        }), 400

    # 3. Verify secret
    if data["secret"] != EXPECTED_SECRET:
        return jsonify({"error": "Forbidden: invalid secret"}), 403

    # ================================
    # START QUIZ PROCESSING  
    # ================================

    start_time = time.time()
    quiz_url = data["url"]
    email = data["email"]

    # Solve the complete quiz chain
    try:
        quiz_results = solve_full_quiz(quiz_url, email, EXPECTED_SECRET)
        
        return jsonify({
            "status": "completed",
            "message": "Quiz solving completed",
            "email": email,
            "url": quiz_url,
            "received_at": start_time,
            "processing_time": time.time() - start_time,
            "results": quiz_results
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Failed to solve quiz",
            "details": str(e),
            "email": email,
            "url": quiz_url,
            "received_at": start_time
        }), 500


if __name__ == "__main__":
    # Debug server for local testing
    app.run(host="0.0.0.0", port=5000, debug=True)
