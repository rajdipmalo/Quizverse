from flask import Flask, session, redirect, url_for
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user, logout_user
from models.models import db, User
from datetime import datetime, timedelta
import os

bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'login'

app = None

def new_app():
    global app
    app = Flask(__name__)
    
    # Configuration
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "your_secret_key_here")  # Use env var in production
    
    # PostgreSQL configuration (Render automatically provides DATABASE_URL)
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # SQLAlchemy requires postgresql:// instead of postgres://
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
    
    # Database connection pooling for production
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 20,
        "max_overflow": 30
    }

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    
    # Create app context
    app.app_context().push()
    
    # Create tables and admin user
    db.create_all()
    new_admin()
    
    # Session timeout check
    @app.before_request    
    def session_timeout_check():
        session.permanent = True
        if current_user.is_authenticated and current_user.type != 'admin':
            now = datetime.utcnow()
            last_activity = session.get('last_activity')
            
            if last_activity:
                elapsed = (now - datetime.strptime(last_activity, "%Y-%m-%d %H:%M:%S")).total_seconds()
                if elapsed > 1800:  # 30 minutes timeout
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

# Initialize app
app = new_app()

# Import controllers after app is created to avoid circular imports
from controllers.controllers import *

if __name__ == "__main__":
    app.run()