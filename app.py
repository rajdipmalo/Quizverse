import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from flask import Flask, session, redirect, url_for
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user, logout_user
from models.models import db, User
from datetime import datetime, timedelta
import urllib.parse
import os

bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'login'

app = None

def create_database_and_user_if_not_exists():
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",               
            password="712503",  
            host="localhost",
            port="5433"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM pg_database WHERE datname='quizverse'")
        exists = cur.fetchone()
        if not exists:
            cur.execute("CREATE DATABASE quizverse")
            print("Database 'quizverse' created.")

        cur.execute("SELECT 1 FROM pg_roles WHERE rolname='quizverse'")
        user_exists = cur.fetchone()
        if not user_exists:
            cur.execute("CREATE USER quizverse WITH PASSWORD 'Quizverse@712503'")
            print("User 'quizverse' created.")

        # Connect to the new database to grant schema privileges
        cur.close()
        conn.close()

        conn = psycopg2.connect(
            dbname="quizverse",
            user="postgres",               
            password="712503",
            host="localhost",
            port="5433"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        cur.execute("GRANT ALL PRIVILEGES ON DATABASE quizverse TO quizverse")
        cur.execute("GRANT USAGE, CREATE ON SCHEMA public TO quizverse")
        cur.execute("ALTER SCHEMA public OWNER TO quizverse")
        print("Privileges on schema 'public' granted to 'quizverse'.")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error creating database or user: {str(e)}")
        exit(1)



def new_app():
    global app
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "your_secret_key"

    # Use env vars or fallback
    DB_USER = os.getenv("DB_USER", "quizverse")
    DB_PASS_RAW = os.getenv("DB_PASSWORD", "Quizverse@712503")
    DB_PASS = urllib.parse.quote_plus(DB_PASS_RAW)

    app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{DB_USER}:{DB_PASS}@localhost:5433/quizverse"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    app.app_context().push()

    try:
        with app.app_context():
            db.create_all()
            new_admin()
    except Exception as e:
        print(f"Database initialization failed: {str(e)}")
        print("Please verify your PostgreSQL credentials and database settings")
        exit(1)

    @app.before_request
    def session_timeout_check():
        session.permanent = True
        if current_user.is_authenticated and current_user.type != 'admin':
            now = datetime.utcnow()
            last_activity = session.get('last_activity')

            if last_activity:
                elapsed = (now - datetime.strptime(last_activity, "%Y-%m-%d %H:%M:%S")).total_seconds()
                if elapsed > 1800:  # 30 minutes
                    logout_user()
                    session.clear()
                    return redirect(url_for("login"))

            session['last_activity'] = now.strftime("%Y-%m-%d %H:%M:%S")

    return app


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def new_admin():
    admin = User.query.filter_by(type='admin').first()
    if not admin:
        hashed_password = bcrypt.generate_password_hash("Quizverse@712503").decode("utf-8")
        admin = User(
            username="Quizverse",
            email="Quizverse@gmail.com",
            password=hashed_password,
            full_name="Quizverse",
            qualification="Admin",
            dob=datetime.strptime("2025-03-20", "%Y-%m-%d").date(),
            type="admin"
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully")


if __name__ == "__main__":
    create_database_and_user_if_not_exists()
    app = new_app()

    from controllers.controllers import *

    app.run(debug=True)
