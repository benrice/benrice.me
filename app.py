from flask import Flask, render_template, request, redirect, jsonify, abort
from pathlib import Path
from dotenv import load_dotenv

import serverless_wsgi
import requests
import os
import base64
import urllib.parse
import markdown
import yaml

load_dotenv()

app = Flask(__name__)


SPOTIFY_SCOPE = "user-read-currently-playing user-read-recently-played"
SPOTIFY_REDIRECT_URI = os.environ.get(
    "SPOTIFY_REDIRECT_URI",
    "http://127.0.0.1:5000/spotify/callback"
)

TOPICS_DIR = Path(__file__).parent / "content" / "topics"

def load_topic(topic_slug):
    topic_path = TOPICS_DIR / f"{topic_slug}.md"

    if not topic_path.exists():
        return None

    raw_content = topic_path.read_text(encoding="utf-8")

    # Separate YAML front matter from Markdown body
    if raw_content.startswith("---"):
        _, front_matter, markdown_content = raw_content.split("---", 2)
        metadata = yaml.safe_load(front_matter) or {}
    else:
        metadata = {}
        markdown_content = raw_content

    html_content = markdown.markdown(
        markdown_content,
        extensions=[
            "extra",
            "sane_lists"
        ]
    )

    return {
        "slug": topic_slug,
        "title": metadata.get("title", topic_slug.replace("-", " ").title()),
        "content": html_content
    }

@app.route("/about/more/<topic_slug>")
def more_topic(topic_slug):
    topic = load_topic(topic_slug)

    if topic is None:
        abort(404)

    return render_template("topic.html", topic=topic)

@app.route("/")
def home():
    return render_template(
        "index.html",
        title="Ben Rice",
        active_page="home"
    )


@app.route("/spotify/login")
def spotify_login():
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")

    if not client_id:
        return "Missing SPOTIFY_CLIENT_ID environment variable.", 500

    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "scope": SPOTIFY_SCOPE,
    }

    auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)

    return redirect(auth_url)

@app.route("/spotify/callback")
def spotify_callback():
    error = request.args.get("error")
    if error:
        return f"Spotify authorization failed: {error}", 400

    code = request.args.get("code")
    if not code:
        return "Missing authorization code from Spotify.", 400

    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        return "Missing Spotify client ID or client secret.", 500

    auth_string = f"{client_id}:{client_secret}"
    auth_base64 = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {auth_base64}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": SPOTIFY_REDIRECT_URI,
        },
        timeout=10,
    )

    token_data = response.json()

    if response.status_code != 200:
        return jsonify({
            "message": "Spotify token exchange failed",
            "status_code": response.status_code,
            "details": token_data,
        }), response.status_code

    refresh_token = token_data.get("refresh_token")

    if not refresh_token:
        return jsonify({
            "message": "Spotify authorized, but no refresh token was returned.",
            "details": token_data,
        }), 500

    return f"""
    <h1>Spotify authorization worked</h1>

    <p>Copy this value into your <code>SPOTIFY_REFRESH_TOKEN</code> environment variable:</p>

    <pre>{refresh_token}</pre>

    <p>This token includes these scopes:</p>

    <pre>{token_data.get("scope")}</pre>
    """

@app.route("/about")
def about():
    return render_template(
        "about.html",
        title="About | Ben Rice",
        active_page="about"
    )

@app.route("/about/more")
def about_more():
    return render_template(
        "about_more.html",
        title="More About | Ben Rice"
    )

@app.route("/projects")
def projects():
    return render_template(
        "projects.html",
        title="Projects | Ben Rice",
        active_page="projects"
    )


@app.route("/contact")
def contact():
    return render_template(
        "contact.html",
        title="Contact | Ben Rice",
        active_page="contact"
    )

@app.route("/api/now-playing")
def now_playing():
    access_token = get_spotify_token()

    response = requests.get(
        "https://api.spotify.com/v1/me/player/currently-playing",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if response.status_code == 204:
        return {"is_playing": False, "message": "Nothing playing"}

    data = response.json()
    item = data.get("item")

    return {
        "is_playing": data.get("is_playing"),
        "title": item.get("name"),
        "artist": ", ".join(a["name"] for a in item.get("artists", [])),
        "album": item.get("album", {}).get("name"),
        "album_art": item.get("album", {}).get("images", [{}])[0].get("url"),
        "spotify_url": item.get("external_urls", {}).get("spotify"),
    }



def get_spotify_token():
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    refresh_token = os.environ.get("SPOTIFY_REFRESH_TOKEN")

    if not client_id or not client_secret or not refresh_token:
        raise RuntimeError(
            "Missing Spotify environment variables. "
            "Set SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and SPOTIFY_REFRESH_TOKEN."
        )

    auth_string = f"{client_id}:{client_secret}"
    auth_base64 = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {auth_base64}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=10,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Spotify token refresh failed: {response.status_code} {response.text}"
        )

    return response.json()["access_token"]

def lambda_handler(event, context):
    return serverless_wsgi.handle_request(app, event, context)


if __name__ == "__main__":
    app.run(debug=True)