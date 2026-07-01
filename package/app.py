from flask import Flask, render_template
import serverless_wsgi

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


def lambda_handler(event, context):
    return serverless_wsgi.handle_request(app, event, context)


if __name__ == "__main__":
    app.run(debug=True)