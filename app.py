from flask import Flask, session, redirect, url_for
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user, logout_user
from models.models import db, User
from sqlalchemy import text
from datetime import datetime, timedelta
import os
import time

# Initialize extensions outside app factory
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'login'

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config.update({
        "SECRET_KEY": os.getenv("SECRET_KEY", "fallback-secret-key"),
        "SQLALCHEMY_DATABASE_URI": os.getenv("DATABASE_URL"),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "PERMANENT_SESSION_LIFETIME": timedelta(minutes=30),
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "pool_timeout": 30
        }
    })

    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # Register database initialization
    register_database_setup(app)

    # Register middleware
    register_middleware(app)

    return app

def register_database_setup(app):
    """Register database setup commands"""
    @app.cli.command("init-db")
    def init_db():
        """Initialize the database"""
        with app.app_context():
            initialize_database(app)

    # Initialize on first request if not done
    @app.before_first_request
    def ensure_db_initialized():
        with app.app_context():
            if not db.engine.dialect.has_table(db.engine, "user"):
                initialize_database(app)

def initialize_database(app):
    """Safe database initialization"""
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            db.create_all()
            create_admin_user(db)
            app.logger.info("Database initialized successfully")
            break
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                app.logger.critical("Max retries reached")
                raise
            time.sleep(retry_delay)
        finally:
            db.session.remove()

def create_admin_user(app):
    """Create admin user if not exists"""
    with app.app_context():
        if not User.query.filter_by(type='admin').first():
            admin = User(
                username="Quizverse",
                email="quizverse@example.com",
                password=bcrypt.generate_password_hash("Quizverse@712503").decode('utf-8'),
                full_name="Admin User",
                type="admin",
                qualification="Admin",
                dob=datetime(2000, 1, 1).date()
            )
            db.session.add(admin)
            db.session.commit()

def register_middleware(app):
    """Register all middleware"""
    @app.before_request
    def session_timeout_check():
        if current_user.is_authenticated and current_user.type != 'admin':
            if 'last_activity' in session:
                elapsed = (datetime.utcnow() - session['last_activity']).total_seconds()
                if elapsed > 1800:  # 30 minutes
                    logout_user()
                    session.clear()
                    return redirect(url_for('login'))
            session['last_activity'] = datetime.utcnow()

    @app.teardown_request
    def shutdown_session(exception=None):
        db.session.remove()

# Create application instance
app = create_app()

# User loader
@login_manager.user_loader
def load_user(user_id):
    with app.app_context():
        return User.query.get(int(user_id))

# Import controllers after app creation
from controllers.controllers import *

if __name__ == '__main__':
    app.run()