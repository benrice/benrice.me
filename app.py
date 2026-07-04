from flask import Flask, render_template
import serverless_wsgi
import requests
import os
import base64

app = Flask(__name__)

@app.route("/")
def home():
    return render_template(
        "index.html",
        title="Ben Rice",
        active_page="home"
    )


@app.route("/about")
def about():
    return render_template(
        "about.html",
        title="About | Ben Rice",
        active_page="about"
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