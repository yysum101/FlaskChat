from flask import (
    Flask, render_template_string, request, redirect, url_for, session, flash, abort
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from urllib import parse as up
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

# Parse DATABASE_URL env var for PostgreSQL connection, handle missing port
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable NOT set")

up.uses_netloc.append("postgres")
url = up.urlparse(DATABASE_URL)
port = url.port or 5432  # Default postgres port if missing
app.config[
    "SQLALCHEMY_DATABASE_URI"
] = f"postgresql://{url.username}:{url.password}@{url.hostname}:{port}{url.path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    about = db.Column(db.String(300), default="")
    posts = db.relationship("Post", backref="author", lazy=True)
    messages = db.relationship("Message", backref="author", lazy=True)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(150), nullable=False)
    body = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


# Helpers
def current_user():
    uid = session.get("user_id")
    if uid:
        return User.query.get(uid)
    return None


def login_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user():
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated


# Templates (using render_template_string for single-file app)
base_template = """
<!doctype html>
<html lang="en" data-bs-theme="light">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{{ title or 'FriendBook' }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
    <style>
        body {
            background: #d0f0f7;
            color: #003300;
        }
        .card {
            border-radius: 0.75rem;
            box-shadow: 0 4px 8px rgba(20, 120, 100, 0.15);
        }
        .navbar, .footer {
            background: #a0d8b3;
        }
        .btn-primary {
            background-color: #339966;
            border-color: #2d7a4b;
        }
        .btn-primary:hover {
            background-color: #2d7a4b;
            border-color: #255f3a;
        }
        .chat-message {
            max-width: 70%;
            padding: 10px 15px;
            margin-bottom: 8px;
            border-radius: 15px;
            word-wrap: break-word;
        }
        .chat-message.user {
            background-color: #339966;
            color: white;
            margin-left: auto;
            border-bottom-right-radius: 0;
        }
        .chat-message.other {
            background-color: #d0f0f7;
            color: #003300;
            margin-right: auto;
            border-bottom-left-radius: 0;
        }
        .flash-message {
            margin-top: 10px;
        }
        a.nav-link.active {
            font-weight: 600;
            color: #004d26 !important;
        }
    </style>
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-light mb-4">
  <div class="container">
    <a class="navbar-brand fw-bold text-dark" href="{{ url_for('dashboard') }}">FriendBook</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMenu" aria-controls="navMenu" aria-expanded="false" aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navMenu">
      <ul class="navbar-nav ms-auto">
        {% if current_user %}
          <li class="nav-item"><a class="nav-link {% if request.endpoint == 'dashboard' %}active{% endif %}" href="{{ url_for('dashboard') }}">Dashboard</a></li>
          <li class="nav-item"><a class="nav-link {% if request.endpoint == 'chat' %}active{% endif %}" href="{{ url_for('chat') }}">Chat</a></li>
          <li class="nav-item"><a class="nav-link {% if request.endpoint == 'profile' %}active{% endif %}" href="{{ url_for('profile') }}">Profile</a></li>
          <li class="nav-item"><a class="nav-link {% if request.endpoint == 'settings' %}active{% endif %}" href="{{ url_for('settings') }}">Settings</a></li>
          <li class="nav-item"><a class="nav-link" href="{{ url_for('logout') }}">Logout</a></li>
        {% else %}
          <li class="nav-item"><a class="nav-link {% if request.endpoint == 'login' %}active{% endif %}" href="{{ url_for('login') }}">Login</a></li>
          <li class="nav-item"><a class="nav-link {% if request.endpoint == 'register' %}active{% endif %}" href="{{ url_for('register') }}">Register</a></li>
        {% endif %}
      </ul>
    </div>
  </div>
</nav>

<div class="container">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      <div class="flash-message">
      {% for category, message in messages %}
        <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
          {{ message }}
          <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
      {% endfor %}
      </div>
    {% endif %}
  {% endwith %}
  {% block content %}{% endblock %}
</div>

<footer class="footer text-center py-3 mt-5">
  <small>FriendBook &copy; 2025</small>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# ROUTES

@app.route("/")
def home():
    if current_user():
        return redirect(url_for("dashboard"))
    else:
        return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        about = request.form.get("about", "").strip()

        if not username or not password or not confirm:
            flash("Please fill in all required fields.", "warning")
            return redirect(url_for("register"))

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
            return redirect(url_for("register"))

        user = User(username=username, about=about)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template_string(
        "{% extends base_template %}{% block content %}"
        """
        <div class="card p-4 mx-auto" style="max-width: 450px;">
          <h3 class="mb-3">Register</h3>
          <form method="POST" novalidate>
            <div class="mb-3">
              <label for="username" class="form-label">Username *</label>
              <input type="text" class="form-control" id="username" name="username" required minlength="3" maxlength="80" />
            </div>
            <div class="mb-3">
              <label for="about" class="form-label">Tell us more about yourself</label>
              <textarea class="form-control" id="about" name="about" rows="2" maxlength="300"></textarea>
            </div>
            <div class="mb-3">
              <label for="password" class="form-label">Password *</label>
              <input type="password" class="form-control" id="password" name="password" required minlength="6" />
            </div>
            <div class="mb-3">
              <label for="confirm_password" class="form-label">Confirm Password *</label>
              <input type="password" class="form-control" id="confirm_password" name="confirm_password" required minlength="6" />
            </div>
            <button type="submit" class="btn btn-primary w-100">Register</button>
          </form>
          <p class="mt-3 mb-0 text-center">Already have an account? <a href="{{ url_for('login') }}">Login here</a>.</p>
        </div>
        """
        + "{% endblock %}",
        base_template=base_template,
        title="Register",
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash("Invalid username or password.", "danger")
            return redirect(url_for("login"))

        session["user_id"] = user.id
        flash("Logged in successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template_string(
        "{% extends base_template %}{% block content %}"
        """
        <div class="card p-4 mx-auto" style="max-width: 400px;">
          <h3 class="mb-3">Login</h3>
          <form method="POST" novalidate>
            <div class="mb-3">
              <label for="username" class="form-label">Username</label>
              <input type="text" class="form-control" id="username" name="username" required minlength="3" maxlength="80" />
            </div>
            <div class="mb-3">
              <label for="password" class="form-label">Password</label>
              <input type="password" class="form-control" id="password" name="password" required minlength="6" />
            </div>
            <button type="submit" class="btn btn-primary w-100">Login</button>
          </form>
          <p class="mt-3 mb-0 text-center">Don't have an account? <a href="{{ url_for('register') }}">Register here</a>.</p>
        </div>
        """
        + "{% endblock %}",
        base_template=base_template,
        title="Login",
    )


@app.route("/logout")
@login_required
def logout():
    session.pop("user_id", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    user = current_user()

    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        body = request.form.get("body", "").strip()
        if not subject or not body:
            flash("Subject and body cannot be empty.", "warning")
        else:
            post = Post(subject=subject, body=body, author=user)
            db.session.add(post)
            db.session.commit()
            flash("Post created successfully!", "success")
            return redirect(url_for("dashboard"))

    posts = Post.query.order_by(Post.id.desc()).all()

    return render_template_string(
        "{% extends base_template %}{% block content %}"
        """
        <div class="row">
          <div class="col-md-6 mx-auto">
            <div class="card p-4 mb-4">
              <h4>Create Post</h4>
              <form method="POST" novalidate>
                <div class="mb-3">
                  <input type="text" class="form-control" name="subject" placeholder="Subject" maxlength="150" required />
                </div>
                <div class="mb-3">
                  <textarea class="form-control" name="body" placeholder="Write your post here..." rows="4" required maxlength="2000"></textarea>
                </div>
                <button class="btn btn-primary w-100" type="submit">Post</button>
              </form>
            </div>

            <h4 class="mb-3">Recent Posts</h4>
            {% for post in posts %}
              <div class="card p-3 mb-3">
                <h5>{{ post.subject }}</h5>
                <p>{{ post.body }}</p>
                <small class="text-muted">By {{ post.author.username }}</small>
              </div>
            {% else %}
              <p>No posts yet.</p>
            {% endfor %}
          </div>
        </div>
        """
        + "{% endblock %}",
        base_template=base_template,
        title="Dashboard",
        posts=posts,
    )


@app.route("/profile")
@login_required
def profile():
    user = current_user()
    return render_template_string(
        "{% extends base_template %}{% block content %}"
        """
        <div class="card mx-auto" style="max-width: 450px; padding: 20px;">
          <h3>Profile</h3>
          <p><strong>Username:</strong> {{ user.username }}</p>
          <p><strong>About Me:</strong> {{ user.about or "No information provided." }}</p>
        </div>
        """
        + "{% endblock %}",
        base_template=base_template,
        title="Profile",
        user=user,
    )


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user = current_user()

    if request.method == "POST":
        new_username = request.form.get("username", "").strip()
        about = request.form.get("about", "").strip()
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_new_password = request.form.get("confirm_new_password", "")

        if new_username and new_username != user.username:
            if User.query.filter_by(username=new_username).first():
                flash("Username already taken.", "danger")
                return redirect(url_for("settings"))
            else:
                user.username = new_username

        user.about = about

        if current_password or new_password or confirm_new_password:
            if not current_password:
                flash("Please enter your current password to change password.", "warning")
                return redirect(url_for("settings"))
            if not user.check_password(current_password):
                flash("Current password is incorrect.", "danger")
                return redirect(url_for("settings"))
            if new_password != confirm_new_password:
                flash("New passwords do not match.", "danger")
                return redirect(url_for("settings"))
            if len(new_password) < 6:
                flash("New password must be at least 6 characters.", "warning")
                return redirect(url_for("settings"))
            user.set_password(new_password)

        db.session.commit()
        flash("Settings updated successfully.", "success")
        return redirect(url_for("settings"))

    return render_template_string(
        "{% extends base_template %}{% block content %}"
        """
        <div class="card mx-auto" style="max-width: 450px; padding: 20px;">
          <h3>Settings</h3>
          <form method="POST" novalidate>
            <div class="mb-3">
              <label for="username" class="form-label">Change Username</label>
              <input type="text" class="form-control" id="username" name="username" value="{{ user.username }}" minlength="3" maxlength="80" />
            </div>
            <div class="mb-3">
              <label for="about" class="form-label">About Me</label>
              <textarea class="form-control" id="about" name="about" rows="3" maxlength="300">{{ user.about }}</textarea>
            </div>
            <hr />
            <h5>Change Password</h5>
            <div class="mb-3">
              <label for="current_password" class="form-label">Current Password</label>
              <input type="password" class="form-control" id="current_password" name="current_password" />
            </div>
            <div class="mb-3">
              <label for="new_password" class="form-label">New Password</label>
              <input type="password" class="form-control" id="new_password" name="new_password" minlength="6" />
            </div>
            <div class="mb-3">
              <label for="confirm_new_password" class="form-label">Confirm New Password</label>
              <input type="password" class="form-control" id="confirm_new_password" name="confirm_new_password" minlength="6" />
            </div>
            <button class="btn btn-primary w-100" type="submit">Save Changes</button>
          </form>
        </div>
        """
        + "{% endblock %}",
        base_template=base_template,
        title="Settings",
        user=user,
    )


@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    user = current_user()
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        if content:
            msg = Message(content=content, author=user)
            db.session.add(msg)
            db.session.commit()
            flash("Message sent!", "success")
            return redirect(url_for("chat"))

    messages = Message.query.order_by(Message.id).all()
    return render_template_string(
        "{% extends base_template %}{% block content %}"
        """
        <h3 class="mb-4">Chat Room</h3>
        <div style="max-width: 700px; margin: auto;">
          <div class="border rounded p-3 mb-3" style="height: 350px; overflow-y: auto; background: #e6f2e6;">
            {% for msg in messages %}
              {% if msg.author.id == user.id %}
                <div class="chat-message user">{{ msg.content }}</div>
              {% else %}
                <div class="chat-message other"><strong>{{ msg.author.username }}:</strong> {{ msg.content }}</div>
              {% endif %}
            {% endfor %}
          </div>
          <form method="POST" class="d-flex">
            <input type="text" name="content" class="form-control me-2" placeholder="Write a message..." required maxlength="500" />
            <button type="submit" class="btn btn-primary">Send</button>
          </form>
        </div>
        """
        + "{% endblock %}",
        base_template=base_template,
        title="Chat",
        messages=messages,
        user=user,
    )


# Run app
if __name__ == "__main__":
    # Create tables if not exist (run once)
    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
