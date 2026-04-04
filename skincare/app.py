from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import os
import sqlite3
from datetime import datetime
from werkzeug.utils import secure_filename
import random

app = Flask(__name__)
app.secret_key = "secret123"

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        email TEXT,
        password TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS analysis_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        image TEXT,
        skin_score INTEGER,
        skin_type TEXT,
        skin_profile TEXT,
        analysis_date TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= CONFIG =================
UPLOAD_FOLDER = os.path.join("static", "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= HOME =================
@app.route("/")
def home():
    return render_template("login.html")

# ================= REGISTER =================
@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")
    confirm = request.form.get("confirm_password")

    if password != confirm:
        return "Passwords do not match ❌"

    try:
        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                    (name, email, password))
        conn.commit()
        conn.close()
        session["user"] = name
        return redirect(url_for("dashboard"))
    except:
        return "User already exists ❌"

# ================= LOGIN =================
@app.route("/login_user", methods=["POST"])
def login_user():
    name = request.form.get("name")
    password = request.form.get("password")

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE name=?", (name,))
    user = cur.fetchone()
    conn.close()

    if user and user[3] == password:
        session["user"] = name
        return redirect(url_for("dashboard"))

    return "Invalid login ❌"

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("home"))
    return render_template("dashboard.html", user=session["user"])

# ================= HISTORY JSON =================
@app.route("/history")
def history():
    if "user" not in session:
        return jsonify([])

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE name=?", (session["user"],))
    user_id = cur.fetchone()[0]

    cur.execute("""
        SELECT image, skin_score, skin_type, skin_profile, analysis_date
        FROM analysis_history
        WHERE user_id=?
        ORDER BY id DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()

    history_list = []
    for row in rows:
        history_list.append({
            "image": row[0],
            "score": row[1],
            "type": row[2],
            "profile": row[3][:100] + "..." if len(row[3]) > 100 else row[3],
            "time": row[4]
        })

    return jsonify(history_list)

# ================= ANALYZE PAGE =================
@app.route("/analyze_page")
def analyze_page():
    if "user" not in session:
        return redirect(url_for("home"))
    return render_template("analyze.html")

# ================= INGREDIENT LOGIC =================
def recommend_ingredients(skin_type, skin_report):
    ingredients = []

    if "Dry" in skin_type:
        ingredients += ["Hyaluronic Acid", "Glycerin", "Ceramides"]

    if "Oily" in skin_type:
        ingredients += ["Salicylic Acid", "Niacinamide", "Clay"]

    if "Combination" in skin_type:
        ingredients += ["Niacinamide", "Aloe Vera", "Hyaluronic Acid"]

    # Based on issues
    if "Acne" in str(skin_report):
        ingredients += ["Benzoyl Peroxide", "Tea Tree Oil"]

    if "Dullness" in str(skin_report):
        ingredients += ["Vitamin C"]

    if "Dehydration" in str(skin_report):
        ingredients += ["Hyaluronic Acid"]

    # Remove duplicates
    return list(set(ingredients))

# ================= HELPER FUNCTION =================
def analyze_skin(file_path):
    skin_score = random.randint(50, 95)

    if skin_score < 60:
        skin_type = "Dry Skin"
        skin_profile = "Skin is dry, rough and needs hydration."
        skin_report = ["Dehydration", "Flakiness"]

    elif skin_score < 80:
        skin_type = "Combination Skin"
        skin_profile = "Mixed oily and dry areas."
        skin_report = ["Dullness", "Uneven Tone"]

    else:
        skin_type = "Oily Skin"
        skin_profile = "Excess oil and acne-prone."
        skin_report = ["Excess Oil", "Acne"]

    return skin_score, skin_type, skin_profile, skin_report

# ================= ANALYZE =================
@app.route("/analyze", methods=["POST"])
def analyze():
    if "user" not in session:
        return redirect(url_for("home"))

    file = request.files.get("image")
    if not file:
        return "No image uploaded ❌"

    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    save_name = f"{timestamp}_{filename}"
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], save_name)
    file.save(save_path)

    # Analyze
    skin_score, skin_type, skin_profile, skin_report = analyze_skin(save_path)

    # ✅ NEW: Ingredient Recommendation
    ingredients = recommend_ingredients(skin_type, skin_report)

    # Routine
    morning_routine = ["Cleanser", "Toner", "Serum", "Moisturizer", "Sunscreen"]
    evening_routine = ["Cleanser", "Serum", "Moisturizer", "Night Cream"]

    # Save DB
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE name=?", (session["user"],))
    user_id = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO analysis_history (user_id, image, skin_score, skin_type, skin_profile, analysis_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, save_name, skin_score, skin_type, skin_profile,
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

    return render_template(
        "result.html",
        skin_score=skin_score,
        skin_type=skin_type,
        skin_profile=skin_profile,
        skin_report=skin_report,
        ingredients=ingredients,   # ✅ NEW
        morning_routine=morning_routine,
        evening_routine=evening_routine
    )

# ================= ALL HISTORY =================
@app.route("/all_history")
def all_history():
    if "user" not in session:
        return redirect(url_for("home"))

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE name=?", (session["user"],))
    user_id = cur.fetchone()[0]

    cur.execute("""
        SELECT skin_score, skin_type, skin_profile, analysis_date
        FROM analysis_history
        WHERE user_id=?
        ORDER BY id DESC
    """, (user_id,))
    history = cur.fetchall()
    conn.close()

    return render_template("all_history.html", user=session["user"], history=history)

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)