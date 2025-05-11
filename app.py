from flask import Flask, session, redirect, url_for
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user, logout_user
from flask_migrate import Migrate
from models.models import db, User
from sqlalchemy import text
from datetime import datetime, timedelta
import os

bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'login'

app = None

def new_app():
    global app
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "your_secret_key"
    
    dir = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(dir, 'models', 'instance', 'quiz.sqlite3')
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
    
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # Initialize Migrate
    migrate = Migrate(app, db)

    app.app_context().push()
    
    @app.before_request
    def enforce_foreign_keys():
        db.session.execute(text("PRAGMA foreign_keys=ON"))
    
    @app.before_request    
    def session_timeout_check():
        session.permanent = True
        if current_user.is_authenticated and current_user.type != 'admin':
            now = datetime.utcnow()
            last_activity = session.get('last_activity')
            
            if last_activity:
                elapsed = (now - datetime.strptime(last_activity, "%Y-%m-%d %H:%M:%S")).total_seconds()
                if elapsed > 1800:  
                    logout_user()
                    session.clear()
                    return redirect(url_for("login"))
                
            session['last_activity'] = now.strftime("%Y-%m-%d %H:%M:%S")
        
    if not os.path.exists(path):
        new_admin()
        
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

app = new_app()
from controllers.controllers import *

if __name__ == "__main__":
    app.run()
