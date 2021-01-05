from flask import Flask, render_template, redirect, url_for, session, request
from flask import flash
from flask_dance.contrib.github import make_github_blueprint, github
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import functools
import gspread
import os
import pandas as pd


load_dotenv()
gc = gspread.service_account("service_account.json")
rosters = gc.open_by_key(os.environ.get("SHEETID", ""))


app = Flask(__name__)
# otherwise flask dance thinks it is http
app.wsgi_app = ProxyFix(app.wsgi_app)

if os.environ.get("FLASK_ENV", "development") == "development":
    app.secret_key = "local testing"
    os.environ['FLASK_ENV'] = "development"
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    host = "localhost"
    github_blueprint = make_github_blueprint(
        client_id=os.environ.get("GITHUB_CLIENT_ID_DEVELOP"),
        client_secret=os.environ.get("GITHUB_CLIENT_SECRET_DEVELOP"),
        redirect_to="getlogin",
        scope="")
else:
    app.secret_key = os.urandom(20).hex()
    host = "0.0.0.0"
    github_blueprint = make_github_blueprint(
        client_id=os.environ.get("GITHUB_CLIENT_ID"),
        client_secret=os.environ.get("GITHUB_CLIENT_SECRET"),
        redirect_to="getlogin",
        scope="")

app.register_blueprint(github_blueprint, url_prefix='/login')


def login_required(func):
    @functools.wraps(func)
    def _(*args, **kwargs):
        if not github.authorized:
            session["previous_url"] = request.path
            return(redirect(url_for("github.login")))

        return func(*args, **kwargs)

    return _


@app.route("/login")
def login():
    course = request.args.get("course", "").strip()
    if course != "":
        session["previous_url"] = url_for(course)
    return redirect(url_for("github.login"))


@app.route("/logout")
def logout():
    if github.authorized:
        session.clear()
    course = request.args.get("course", "").strip()
    if course != "":
        return redirect(url_for(course))
    else:
        return redirect(url_for("home"))


@app.route("/getlogin")
def getlogin():
    if github.authorized:
        if "login" not in session:
            # try three times before we gave up
            for i in range(3):
                resp = github.get("/user")
                if resp.ok:
                    break
            if not resp.ok:
                session.clear()
                return redirect(url_for("home"))

            session["login"] = resp.json()["login"]

    if "previous_url" in session:
        previous_url = session["previous_url"]
        session.pop("previous_url", None)
        if github.authorized:
            return redirect(previous_url)

    return redirect(url_for("home"))


@app.route("/submit")
@login_required
def submit():
    course = request.args.get("course", "").strip()
    email = request.args.get("email", "").strip()
    session["email"] = email
    studentid = int(request.args.get("studentid", "").strip())
    session["studentid"] = studentid

    login = session.get("login", None)

    if not email.endswith("@ucdavis.edu"):
        email = email + "@ucdavis.edu"

    # TODO, cache data frame
    ws = rosters.worksheet(course)
    roster = pd.DataFrame(ws.get_all_records())

    matched = roster[roster['SIS User ID'] == studentid]

    if len(matched) == 0:
        flash(
            """
            Error: Student ID not found in roster. Double check it.
            Try again later if you were enrolled recently.
            """,
            "danger")
    elif len(matched) == 1:
        if email != matched["Email"].values[0]:
            flash("Error: Email not found in roster. Double check the Email.", "danger")
        else:
            if len(matched) == 1 and matched["GitHub"].values[0] != "":
                flash("Resubmission", "warning")

            # roster.loc[roster['SIS User ID'] == studentid, "GitHub"] = login
            # ws.update([roster.columns.values.tolist()] + roster.values.tolist())
            cell = ws.find(str(studentid))
            ws.update_cell(cell.row, 5, login)

            flash("Submission successful.", "success")

    return redirect(url_for(course))


@app.route("/sta141b/")
def sta141b():
    return render_template(
        "signin.html",
        course="sta141b",
        authorized=github.authorized,
        login=session.get("login", None),
        client_id=github_blueprint.client_id,
        email=session.get("email", ""),
        studentid=session.get("studentid", "")
        )

@app.route("/sta141c/")
def sta141c():
    return render_template(
        "signin.html",
        course="sta141c",
        authorized=github.authorized,
        login=session.get("login", None),
        client_id=github_blueprint.client_id,
        email=session.get("email", ""),
        studentid=session.get("studentid", "")
        )


@app.route("/")
def home():
    return render_template(
        "index.html",
        authorized=github.authorized,
        login=session.get("login", None),
        client_id=github_blueprint.client_id
        )


if __name__ == "__main__":

    app.run(host=host, port=8080)
