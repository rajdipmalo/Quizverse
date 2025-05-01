from .database import db
from datetime import datetime



class User(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(), unique=True, nullable = False)
    email = db.Column(db.String(), unique=True, nullable = False)
    password = db.Column(db.String(), nullable = False)
    full_name = db.Column(db.String(), nullable = False)
    qualification = db.Column(db.String(), nullable = False)
    dob = db.Column(db.String(), nullable = False)
    type = db.Column(db.String(), default="general")
    
    
class Subject(db.Model):
    sub_id = db.Column(db.Integer(), primary_key = True)
    sub_name = db.Column(db.String(), nullable = False)
    sub_description = db.Column(db.String(), nullable= True)
    chapters = db.relationship('Chapter', backref = 'subject')
     
     
class Chapter(db.Model):
    chap_id = db.Column(db.Integer(), primary_key = True)
    chap_name = db.Column(db.String(), nullable = False)
    chap_description = db.Column(db.String(), nullable = True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.sub_id'), nullable = False)
    quizzes = db.relationship('Quiz', backref = 'chapter')
    
    
class Quiz(db.Model):
    quiz_id = db.Column(db.Integer(), primary_key = True)
    quiz_name = db.Column(db.String(), nullable =False)
    chapter_id = db.Column(db.Integer(), db.ForeignKey('chapter.chap_id'), nullable = False)
    date_of_quiz =  db.Column(db.DateTime(), default = datetime.utcnow)
    duration = db.Column(db.Integer(), nullable = False)
    questions = db.relationship('Question',backref='quiz')
    
    
    
class Question(db.Model):
    ques_id = db.Column(db.Integer(), primary_key = True)
    quiz_id = db.Column(db.Integer(), db.ForeignKey('quiz.quiz_id'), nullable = False)
    ques_title = db.Column(db.String(), nullable = False)
    ques_text = db.Column(db.String(), nullable = False)
    option1 = db.Column(db.String(), nullable = False)
    option2 = db.Column(db.String(), nullable = False)
    option3 = db.Column(db.String(), nullable = False)
    option4 = db.Column(db.String(), nullable = False)
    correct_answer = db.Column(db.String(), nullable = False)
    
class Score(db.Model):
    id = db.Column(db.Integer(), primary_key = True)
    u_id = db.Column(db.Integer(), db.ForeignKey('user.id'), nullable = False)
    q_id = db.Column(db.Integer(), db.ForeignKey('quiz.quiz_id'), nullable = False )
    total_score = db.Column(db.Integer(), nullable = False, default = 0)
    attempt_date = db.Column(db.DateTime, default=datetime.utcnow)
    quiz=db.relationship('Quiz',backref=db.backref('scores'))