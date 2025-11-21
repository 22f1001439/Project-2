from flask import Flask, request, jsonify
import time
import traceback
from quiz_solver import solve_full_quiz

app = Flask(__name__)

EXPECTED_SECRET = "iitm"


@app.route("/")
def home():
    return jsonify({
        "message": "Quiz Solver API - UPDATED",
        "status": "running",
        "version": "2.0",
        "endpoints": {
            "POST /quiz": "Submit a quiz solving request",
            "GET /health": "Health check endpoint"
        }
    })


@app.route("/health")
def health():
    """Health check endpoint for deployment monitoring"""
    try:
        # Test if playwright is available
        from playwright.sync_api import sync_playwright
        return jsonify({
            "status": "healthy",
            "playwright": "available",
            "timestamp": time.time()
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": time.time()
        }), 500


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
        print(f"DEBUG: Starting quiz solving for {email} at {quiz_url}")
        quiz_results = solve_full_quiz(quiz_url, email, EXPECTED_SECRET)
        print(f"DEBUG: Quiz solving completed successfully")
        
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
        print(f"ERROR: Quiz solving failed: {e}")
        print(f"ERROR: Traceback: {traceback.format_exc()}")
        return jsonify({
            "error": "Failed to solve quiz",
            "details": str(e),
            "type": type(e).__name__,
            "email": email,
            "url": quiz_url,
            "received_at": start_time
        }), 500


if __name__ == "__main__":
    # Debug server for local testing
    app.run(host="0.0.0.0", port=5000, debug=True)
