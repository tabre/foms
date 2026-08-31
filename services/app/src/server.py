"""Main server"""
import os
from urllib.parse import quote_plus

from flask import Flask, render_template
from sqlalchemy import create_engine, text

engine = create_engine("postgresql+psycopg://{un}:{pw}@{h}:{p}/{db}".format(
    un=os.environ.get("PG_UN"),
    pw=quote_plus(os.environ.get("PG_PW")),
    h=os.environ.get("PG_IP"),
    p=os.environ.get("PG_PORT"),
    db=os.environ.get("PG_DB")
))

app = Flask(__name__)


@app.route("/")
def hello_world() -> str:
    """Hello world"""
    # Shows basic template rendering
    # This render_template call uses ./templates/index.html
    return render_template("index.html", name="world")


@app.route("/hx__htmx")
def hx__htmx() -> str:
    """HTMX"""
    return '<span id="world" class="gradient-text">HTMX!</span>'


@app.route("/hx__rand")
def hx__rand() -> str:
    """PostgreSQL random number"""
    # Shows basic database functionality
    with engine.connect() as conn:
        random_range = {
            "low": 1,
            "high": 100
        }

        result = conn.execute(
            # text("SELECT 69"),
            text("SELECT floor(random() * (:high - :low + 1) + :low)::int"),
            random_range
        )

    return f"""
    <div id="rand" class="gradient-text" hx-swap="outerHTML" hx-get="/hx__rand">
        {str(result.scalar())}
    </div>
    """
