from flask import Flask, request, jsonify
import time

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

    # 4. If everything is OK, we ACCEPT the quiz request
    # (Later, we will actually visit data["url"] and solve the quiz)
    start_time = time.time()

    # For now, just return a dummy response so you can test
    return jsonify({
        "status": "ok",
        "message": "Quiz request accepted (solver not implemented yet).",
        "email": data["email"],
        "url": data["url"],
        "received_at": start_time
    }), 200

if __name__ == "__main__":
    # Debug server for local testing
    app.run(host="0.0.0.0", port=5000, debug=True)
