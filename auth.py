import os
import json
import hashlib
from flask import session, redirect, url_for
from authlib.integrations.flask_client import OAuth

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Use environment variables for security
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

USER_DB = "users.json"

oauth = OAuth()
google = None


# ================= USER DATABASE =================
def load_users():
    if os.path.exists(USER_DB):
        with open(USER_DB, "r") as f:
            return json.load(f)
    return {"users": []}


def save_users(data):
    with open(USER_DB, "w") as f:
        json.dump(data, f, indent=4)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ================= INITIALIZE GOOGLE OAUTH =================
def init_oauth(app):
    global google

    oauth.init_app(app)

    google = oauth.register(
        name="google",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid email profile"
        }
    )


# ================= START GOOGLE LOGIN =================
def google_login():
    redirect_uri = url_for("google_auth_callback", _external=True)
    return google.authorize_redirect(redirect_uri)


# ================= GOOGLE CALLBACK =================
def google_authorized():

    token = google.authorize_access_token()
    user_info = google.get("https://www.googleapis.com/oauth2/v2/userinfo").json()

    email = user_info.get("email")
    name = user_info.get("name")

    users = load_users()

    if "users" not in users:
        users["users"] = []

    found = False

    for user in users["users"]:
        if user.get("username") == email:
            found = True
            role = user.get("role", "Student")
            break

    if not found:
        role = "Student"
        users["users"].append({
            "username": email,
            "password": "google_auth",
            "role": role,
            "login_type": "google"
        })
        save_users(users)

    session["logged_in"] = True
    session["username"] = name
    session["role"] = role

    return redirect("/dashboard")