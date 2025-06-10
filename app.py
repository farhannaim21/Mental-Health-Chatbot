from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import LoginManager, login_required, UserMixin, login_user, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import pymysql
import ollama
import re
from tensorflow.keras.models import load_model

# Fix MySQL for Mac/Linux
pymysql.install_as_MySQLdb()

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Load your ML model
model = load_model("mental_health_chatbot.h5")

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:%40fa21@localhost:3306/mental_health'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize DB
db = SQLAlchemy(app)

# Login manager
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# ---------------------------------------
# Models
# ---------------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# ---------------------------------------
# Helper Functions
# ---------------------------------------
def build_context_prompt(user_message):
    context_parts = []
    if 'gender' in session:
        context_parts.append(f"User's gender: {session['gender']}")
    if 'age' in session:
        context_parts.append(f"User's age: {session['age']}")
    if 'menstrual_cycle' in session:
        context_parts.append(f"Menstrual cycle: {session['menstrual_cycle']}")
    if 'occupation' in session:
        context_parts.append(f"Occupation: {session['occupation']}")
    
    context = "\n".join(context_parts) if context_parts else "No context yet"
    return f"""Conversation context:
{context}

Current user message: {user_message}

Please respond appropriately as a mental health support chatbot, maintaining a professional yet compassionate tone. If this is early in the conversation and you need specific information, ask for it naturally.
"""

def llama_response(user_message):
    try:
        code_keywords = ["code", "program", "develop", "build an app", "write a script", "python", "java", "c++", "html", "javascript"]
        if any(keyword in user_message.lower() for keyword in code_keywords):
            return "I'm here to offer mental health support, not programming or technical assistance. Let's focus on your well-being. 💬"

        prompt = build_context_prompt(user_message)

        system_prompt = (
    "You are Euphorix Sync, a mental health support chatbot. "
    "Greet the user only once, avoid repeating greetings like 'Hello'. "
    "Do not repeat questions that have already been asked. "
    "If age, gender, or occupation have been provided earlier, do not ask them again. "
    "Respond in short, empathetic sentences, and remember conversation history as best you can."
    "Suggest a follow-up question if the user seems to be in distress. "
    "If the user is in crisis, suggest they seek immediate help from a professional. "
    "If the user is not in crisis, suggest they take a break or engage in a relaxing activity. "
    "Suggest engaging in a hobby or activity they enjoy. "
    "If the user is feeling overwhelmed, suggest they take a moment to breathe and relax. "
    "Be supportive and understanding."
    "Suggest solutions to common mental health issues, such as stress, anxiety, and depression. "
    "If the user is feeling anxious, suggest they try deep breathing exercises. "
    "If the user is feeling sad, suggest they talk to a friend or family member. " 
    "Provide some psychological tips and tricks to help the user cope with their feelings. " 
        )

        stream = ollama.chat(
            model='llama3',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            stream=True
        )

        full_response = ""
        for chunk in stream:
            if 'message' in chunk:
                full_response += chunk['message']['content']

        return full_response

    except Exception as e:
        return f"Sorry, there was an issue: {str(e)}"

def get_response(user_message):
    user_message = user_message.lower()

    # Restart logic
    if "restart" in user_message or "start over" in user_message:
        session.clear()
        return "Chatbot restarted! How can I help you today?"

    # Session info gathering
    if "gender" not in session:
        if any(gender in user_message for gender in ["male", "female", "other"]):
            session["gender"] = user_message.capitalize()
    if "age" not in session and user_message.isdigit():
        session["age"] = int(user_message)
    if session.get("gender") == "Female" and "menstrual" in user_message:
        if "regular" in user_message:
            session["menstrual_cycle"] = "Regular"
        elif "irregular" in user_message:
            session["menstrual_cycle"] = "Irregular"
    if any(occ in user_message for occ in ["school", "college", "working"]):
        session["occupation"] = user_message.capitalize()

    return llama_response(user_message)

# ---------------------------------------
# Routes
# ---------------------------------------

@app.route("/")
@login_required
def home():
    session.clear()
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    if not request.is_json:
        return jsonify({"response": "Invalid request format"}), 400

    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"response": "Please provide a message."}), 400

    bot_response = get_response(user_message)
    return jsonify({"response": bot_response})

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

        if User.query.filter_by(username=username).first():
            flash("Username already exists. Please choose a different one.")
            return redirect(url_for("signup"))

        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("Sign-up successful! Please log in.")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            session["user_id"] = user.id
            session["username"] = user.username
            flash("Login successful!")
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password. Please try again.")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))

# ---------------------------------------
# Login Manager Loader
# ---------------------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------------------------------
# Main
# ---------------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
