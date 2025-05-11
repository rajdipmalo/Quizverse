from flask import Flask, session, redirect, url_for, request
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user, logout_user
from models.models import db, User
from sqlalchemy import text, event, Engine
from datetime import datetime, timedelta
import os
import time
import logging

# Initialize extensions
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'login'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)

    # ======================
    # Configuration
    # ======================
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "your_fallback_secret_key")

    # PostgreSQL configuration
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is not set")

    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    app.config.update({
        "SQLALCHEMY_DATABASE_URI": DATABASE_URL,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "PERMANENT_SESSION_LIFETIME": timedelta(minutes=15),
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "pool_size": 3,
            "max_overflow": 0,
            "pool_timeout": 5
        }
    })

    # Initialize extensions
    time.sleep(2)  # Wait for DB to be ready (esp. in cloud environments)
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # Database connection health
    @event.listens_for(Engine, "engine_connect")
    def ping_connection(connection, branch):
        connection.execute(text("SELECT 1"))

    # Initialize database tables and admin user
    with app.app_context():
        def initialize_database():
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    db.create_all()
                    create_admin_user()
                    db.session.commit()
                    logger.info("Database initialized successfully")
                    break
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Database initialization attempt {attempt + 1} failed: {str(e)}")
                    if attempt == max_retries - 1:
                        logger.critical("Max retries reached for database initialization")
                    time.sleep(5)
                finally:
                    db.session.remove()

        initialize_database()

    # ======================
    # Middleware
    # ======================
    @app.before_request
    def verify_db_connection():
        try:
            db.session.execute(text("SELECT 1"))
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            db.session.rollback()
            db.session.remove()
            if "does not exist" in str(e):
                with app.app_context():
                    db.create_all()

    @app.before_request
    def session_timeout_check():
        if current_user.is_authenticated and current_user.type != 'admin':
            session.permanent = True
            last_activity = session.get('last_activity')
            if last_activity:
                elapsed = (datetime.utcnow() - 
                          datetime.strptime(last_activity, "%Y-%m-%d %H:%M:%S")).total_seconds()
                if elapsed > 900:
                    logout_user()
                    session.clear()
                    return redirect(url_for("login"))
            session['last_activity'] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    @app.after_request
    def log_response(response):
        logger.info(f"{request.method} {request.path} => {response.status}")
        return response

    # ======================
    # Health Check Endpoint
    # ======================
    @app.route('/healthcheck')
    def healthcheck():
        try:
            db.session.execute(text("SELECT 1"))
            return "OK", 200
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return f"DB Error: {str(e)}", 500

    return app

def create_admin_user():
    """Initialize admin user if none exists"""
    if not User.query.filter_by(type='admin').first():
        try:
            admin = User(
                username="Quizverse",
                email="quizverse@example.com",
                password=bcrypt.generate_password_hash("Quizverse@712503").decode('utf-8'),
                full_name="Admin User",
                type="admin",
                qualification="Admin",
                dob=datetime.strptime("2000-01-01", "%Y-%m-%d").date()
            )
            db.session.add(admin)
            logger.info("Admin user created")
        except Exception as e:
            logger.error(f"Error creating admin user: {str(e)}")
            raise

# Create the Flask application
app = create_app()

# User loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import controllers (avoid circular imports)
from controllers.controllers import *

if __name__ == "__main__":
    app.run()