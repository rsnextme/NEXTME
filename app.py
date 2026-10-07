
import os, json, sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, session
from openai import OpenAI
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder="static", static_url_path="")

app.secret_key = os.getenv("NEXTME_SECRET_KEY", "dev-only-change-me-before-production")
DATA_DIR = os.getenv("NEXTME_DATA_DIR", os.path.join(os.path.expanduser("~"), "NEXTME_DATA"))
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "nextme.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS saved_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_type TEXT NOT NULL,
            title TEXT,
            payload_json TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            expires_at DATETIME NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=45.0, max_retries=1)

MODEL = os.getenv("OPENAI_MODEL", "gpt-6-luna")

SYSTEM_PROMPT = """You are NEXTME, an AI future-scenario coach.
Your job is not to predict the future with certainty. Create realistic possible future scenarios from the user's current situation, goals, habits, constraints and choices.
Be optimistic but realistic. Never guarantee future events, income, health, relationships, or outcomes.
Always distinguish scenario from fact. Avoid fear-based or manipulative language.
Return ONLY valid JSON.

Create:
- Path A: Current Direction
- Path B: Better Version
- Path C: Bold Future

For each path include:
title, summary, career, money, health_lifestyle, relationships, personal_growth,
biggest_opportunity, biggest_risk, actions_now (3 items), assumptions (2 items).

Also include:
next_30_days (4 items), habits_to_build (3 items), things_to_reduce (3 items),
future_message, why_this_future (3 concise reasons).

Keep language clear, warm and concise.
"""

def user_prompt(profile):
    return f"""Create NEXTME scenarios for this user profile:

{json.dumps(profile, ensure_ascii=False, indent=2)}

Use the user's own goals and concerns. If information is uncertain, state assumptions instead of inventing facts.
Return JSON with keys:
path_a, path_b, path_c, next_30_days, habits_to_build, things_to_reduce, future_message, why_this_future.
"""

@app.get("/")
def index():
    return send_from_directory("static", "index.html")

@app.post("/api/generate")
def generate():
    payload = request.get_json(force=True)
    profile = payload.get("profile", {})
    language = payload.get("language", "en")
    language_name = payload.get("language_name", "English")

    if not os.getenv("OPENAI_API_KEY"):
        return jsonify({"error":"OPENAI_API_KEY is not configured on the server."}), 500

    instructions = SYSTEM_PROMPT + f"""
Respond completely in {language_name}.
Use the natural native script for that language, except Hinglish should use Roman script.
Keep labels, headings, advice, opportunities, risks and action steps in the selected language.
"""

    prompt = user_prompt(profile)
    try:
        response = client.responses.create(
            model=MODEL,
            instructions=instructions,
            input=prompt,
        )
        text = response.output_text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        data = json.loads(text)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.post("/api/chat")
def chat():
    payload = request.get_json(force=True)
    profile = payload.get("profile", {})
    selected_path = payload.get("selected_path", {})
    history = payload.get("history", [])
    message = payload.get("message", "").strip()
    language_name = payload.get("language_name", "English")

    if not message:
        return jsonify({"error":"Message is required"}), 400
    if not os.getenv("OPENAI_API_KEY"):
        return jsonify({"error":"OPENAI_API_KEY is not configured on the server."}), 500

    instructions = f"""You are the user's possible 5-year Future Self inside NEXTME.
Do not pretend you truly know the future.
Speak as a reflection from the selected scenario.
Give one clear recommendation first, then why, then one action the user can take today.
Never invent unsupported achievements, health outcomes, relationships or income.
Be warm, practical and concise.
Respond completely in {language_name}.
Use the natural native script for that language, except Hinglish should use Roman script.
Use short paragraphs and bullets where helpful.
"""
    context = {
        "profile": profile,
        "selected_scenario": selected_path,
        "recent_history": history[-8:],
        "user_message": message
    }
    try:
        response = client.responses.create(
            model=MODEL,
            instructions=instructions,
            input=json.dumps(context, ensure_ascii=False)
        )
        return jsonify({"reply": response.output_text.strip()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/api/decision")
def decision():
    payload = request.get_json(force=True)
    profile = payload.get("profile", {})
    language_name = payload.get("language_name", "English")
    decision_text = payload.get("decision", "").strip()
    options = [x.strip() for x in payload.get("options", []) if str(x).strip()]
    priorities = payload.get("priorities", [])
    horizon = payload.get("horizon", "5 years")

    if not decision_text or len(options) < 2:
        return jsonify({"error":"Decision and at least two options are required."}), 400
    if not os.getenv("OPENAI_API_KEY"):
        return jsonify({"error":"OPENAI_API_KEY is not configured on the server."}), 500

    instructions = f"""You are NEXTME Decision Simulator.
You do not predict the future with certainty and you do not make the user's decision for them.
You compare realistic scenarios, identify assumptions, risks, trade-offs, reversibility and missing information.
Be practical, balanced and transparent.
Respond completely in {language_name}. Use natural native script for that language, except Hinglish should use Roman script.
Return ONLY valid JSON.

Required JSON:
{{
  "decision_title": "",
  "best_fit_option": "",
  "confidence": "Low|Moderate|High",
  "recommendation_summary": "",
  "why_best_fit": ["", "", ""],
  "biggest_uncertainty": "",
  "option_analysis": [
    {{
      "option": "",
      "overall_score": 0,
      "money": 0,
      "stability": 0,
      "growth": 0,
      "family_lifestyle": 0,
      "time_flexibility": 0,
      "reversibility": 0,
      "summary": "",
      "year_1": "",
      "year_3": "",
      "year_5": "",
      "top_risks": ["", ""],
      "best_case": "",
      "worst_case": ""
    }}
  ],
  "what_to_verify": ["", "", ""],
  "next_7_days": ["", "", ""],
  "decision_rule": ""
}}

Scores are 0-100 and are comparative scenario scores, not objective facts.
Do not fabricate exact income, health, legal, investment, or relationship outcomes.
If information is missing, lower confidence and say what must be verified.
"""

    context = {
        "profile": profile,
        "decision": decision_text,
        "options": options,
        "priorities": priorities,
        "time_horizon": horizon
    }

    try:
        response = client.responses.create(
            model=MODEL,
            instructions=instructions,
            input=json.dumps(context, ensure_ascii=False)
        )
        text = response.output_text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        return jsonify(json.loads(text))
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if len(name) < 2:
        return jsonify({"error": "Please enter your name."}), 400
    if "@" not in email or "." not in email:
        return jsonify({"error": "Please enter a valid email."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password))
        )
        conn.commit()
        uid = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "An account with this email already exists."}), 409
    conn.close()

    session["user_id"] = uid
    session["user_name"] = name
    session["user_email"] = email
    return jsonify({"ok": True, "user": {"id": uid, "name": name, "email": email}})

@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    conn = get_db()
    user = conn.execute(
        "SELECT id, name, email, password_hash FROM users WHERE email=?",
        (email,)
    ).fetchone()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]
    return jsonify({"ok": True, "user": {"id": user["id"], "name": user["name"], "email": user["email"]}})

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})

@app.get("/api/me")
def me():
    if not session.get("user_id"):
        return jsonify({"logged_in": False})
    return jsonify({
        "logged_in": True,
        "user": {
            "id": session["user_id"],
            "name": session["user_name"],
            "email": session["user_email"]
        }
    })


@app.get("/api/history")
def history_list():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Login required."}), 401

    conn = get_db()
    rows = conn.execute(
        "SELECT id, item_type, title, payload_json, created_at FROM saved_items WHERE user_id=? ORDER BY id DESC",
        (uid,)
    ).fetchall()
    conn.close()

    items = []
    for row in rows:
        try:
            payload = json.loads(row["payload_json"])
        except Exception:
            payload = {}
        items.append({
            "id": row["id"],
            "item_type": row["item_type"],
            "title": row["title"],
            "payload": payload,
            "created_at": row["created_at"]
        })
    return jsonify({"items": items})

@app.post("/api/history")
def history_save():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Login required."}), 401

    data = request.get_json(silent=True) or {}
    item_type = str(data.get("item_type", "")).strip()
    title = str(data.get("title", "")).strip()
    payload = data.get("payload")

    if item_type not in ("future", "decision"):
        return jsonify({"error": "Invalid item type."}), 400
    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid payload."}), 400

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO saved_items (user_id, item_type, title, payload_json) VALUES (?, ?, ?, ?)",
        (uid, item_type, title, json.dumps(payload, ensure_ascii=False))
    )
    conn.commit()
    item_id = cur.lastrowid
    conn.close()
    return jsonify({"ok": True, "id": item_id})

@app.delete("/api/history/<int:item_id>")
def history_delete(item_id):
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Login required."}), 401

    conn = get_db()
    cur = conn.execute(
        "DELETE FROM saved_items WHERE id=? AND user_id=?",
        (item_id, uid)
    )
    conn.commit()
    deleted = cur.rowcount
    conn.close()

    if not deleted:
        return jsonify({"error": "Item not found."}), 404
    return jsonify({"ok": True})


@app.post("/api/forgot-password")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()

    if not email:
        return jsonify({"error": "Please enter your email."}), 400

    conn = get_db()
    user = conn.execute("SELECT id, email FROM users WHERE email=?", (email,)).fetchone()

    # Avoid leaking account existence in production-style wording.
    if not user:
        conn.close()
        return jsonify({
            "ok": True,
            "message": "If this email is registered, a reset code will be created."
        })

    code = f"{secrets.randbelow(1000000):06d}"
    expires = (datetime.utcnow() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")

    conn.execute("UPDATE password_resets SET used=1 WHERE user_id=? AND used=0", (user["id"],))
    conn.execute(
        "INSERT INTO password_resets (user_id, code, expires_at) VALUES (?, ?, ?)",
        (user["id"], code, expires)
    )
    conn.commit()
    conn.close()

    # LOCAL MVP ONLY: return code on screen.
    # For public deployment, replace this with email delivery.
    return jsonify({
        "ok": True,
        "message": "Reset code created. Local testing me code neeche dikh raha hai.",
        "dev_code": code
    })

@app.post("/api/reset-password")
def reset_password():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    code = str(data.get("code", "")).strip()
    password = str(data.get("password", ""))

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    conn = get_db()
    user = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if not user:
        conn.close()
        return jsonify({"error": "Invalid reset request."}), 400

    row = conn.execute(
        """SELECT id, code, expires_at, used
           FROM password_resets
           WHERE user_id=?
           ORDER BY id DESC LIMIT 1""",
        (user["id"],)
    ).fetchone()

    if not row or row["used"] or row["code"] != code:
        conn.close()
        return jsonify({"error": "Invalid or expired reset code."}), 400

    try:
        expires_at = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
    except Exception:
        conn.close()
        return jsonify({"error": "Invalid or expired reset code."}), 400

    if datetime.utcnow() > expires_at:
        conn.execute("UPDATE password_resets SET used=1 WHERE id=?", (row["id"],))
        conn.commit()
        conn.close()
        return jsonify({"error": "Reset code expired. Please request a new one."}), 400

    conn.execute(
        "UPDATE users SET password_hash=? WHERE id=?",
        (generate_password_hash(password), user["id"])
    )
    conn.execute("UPDATE password_resets SET used=1 WHERE id=?", (row["id"],))
    conn.commit()
    conn.close()

    return jsonify({"ok": True, "message": "Password reset successful. Ab login kijiye."})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
