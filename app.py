from flask import Flask
from models.models import db, User
import os


app = None
def new_app():
    app = Flask(__name__)
    dir = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(dir,'models','instance','quiz.sqlite3')
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{path}"
    db.init_app(app)
    app.app_context().push()
    
    if not os.path.exists(path):
        
        db.create_all()
        new_admin()
    return app


def new_admin():
    from models.models import User
    admin = User.query.filter_by(type='admin').first()
    if not admin:
        admin = User(
            username="quiz master",
            email="quiz_master@gmail.com",
            password="1234",
            full_name = "Quiz Master",
            qualification="Admin",
            dob = "2025-03-20",
            type="admin"
            
        )
        db.session.add(admin)
        db.session.commit()
        
    

app = new_app()
from controllers.controllers import *

if __name__ == "__main__":
    app.run()