from flask import Flask, session, redirect, url_for
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user, logout_user
from models.models import db, User
from sqlalchemy import text
from datetime import datetime, timedelta
import os
import time

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

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # Database initialization with proper transaction handling
    with app.app_context():
        initialize_database(app)

    # Middleware
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

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db.session.remove()

    return app

def initialize_database(app):
    """Safe database initialization with retry logic"""
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            db.create_all()
            create_admin_user()
            db.session.commit()
            app.logger.info("Database initialized successfully")
            break
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                app.logger.critical("Max retries reached for database initialization")
                raise
            time.sleep(retry_delay)
        finally:
            db.session.remove()

def create_admin_user():
    """Create admin user if not exists"""
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

app = create_app()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import controllers after app creation
from controllers.controllers import *

if __name__ == '__main__':
    app.run()