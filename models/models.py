from .database import db
from datetime import datetime
from flask_login import UserMixin



class User(db.Model, UserMixin):
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(), unique=True, nullable = False)
    email = db.Column(db.String(), unique=True, nullable = False)
    password = db.Column(db.String(), nullable = False)
    full_name = db.Column(db.String(), nullable = False)
    qualification = db.Column(db.String(), nullable = False)
    dob = db.Column(db.Date(), nullable = False)
    type = db.Column(db.String(), default="general")
    failed_attempts = db.Column(db.Integer, default=0)
    last_failed_attempt = db.Column(db.DateTime)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    scores = db.relationship('Score', backref='user', cascade='all, delete-orphan', passive_deletes=True)
    
    
class Subject(db.Model):
    sub_id = db.Column(db.Integer(), primary_key = True)
    sub_name = db.Column(db.String(), nullable = False)
    sub_description = db.Column(db.String(), nullable= True)
    chapters = db.relationship('Chapter', backref = 'subject', cascade='all, delete-orphan', passive_deletes=True)
     
     
class Chapter(db.Model):
    chap_id = db.Column(db.Integer(), primary_key = True)
    chap_name = db.Column(db.String(), nullable = False)
    chap_description = db.Column(db.String(), nullable = True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.sub_id', ondelete='CASCADE'), nullable = False)
    quizzes = db.relationship('Quiz', backref = 'chapter', cascade='all, delete-orphan', passive_deletes=True)
    
    
class Quiz(db.Model):
    quiz_id = db.Column(db.Integer(), primary_key = True)
    quiz_name = db.Column(db.String(), nullable =False)
    chapter_id = db.Column(db.Integer(), db.ForeignKey('chapter.chap_id', ondelete='CASCADE'), nullable = False)
    date_of_quiz =  db.Column(db.DateTime(), default = datetime.utcnow)
    duration = db.Column(db.Integer(), nullable = False)
    questions = db.relationship('Question',backref='quiz', cascade='all, delete-orphan', passive_deletes=True)
    scores = db.relationship('Score', backref='quiz', cascade='all, delete-orphan', passive_deletes=True)
    
    
    
class Question(db.Model):
    ques_id = db.Column(db.Integer(), primary_key = True)
    quiz_id = db.Column(db.Integer(), db.ForeignKey('quiz.quiz_id', ondelete='CASCADE'), nullable = False)
    ques_title = db.Column(db.String(), nullable = False)
    ques_text = db.Column(db.String(), nullable = False)
    option1 = db.Column(db.String(), nullable = False)
    option2 = db.Column(db.String(), nullable = False)
    option3 = db.Column(db.String(), nullable = False)
    option4 = db.Column(db.String(), nullable = False)
    correct_answer = db.Column(db.String(), nullable = False)
    
class Score(db.Model):
    id = db.Column(db.Integer(), primary_key = True)
    u_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'), nullable = False)
    q_id = db.Column(db.Integer(), db.ForeignKey('quiz.quiz_id', ondelete='CASCADE'), nullable = False )
    attempt_id = db.Column(db.Integer(), db.ForeignKey('quiz_attempt.attempt_id', ondelete='CASCADE'), nullable=False)
    total_score = db.Column(db.Integer(), nullable = False, default = 0)
    attempt_date = db.Column(db.DateTime(), default=datetime.utcnow)


class QuizAttempt(db.Model):
    attempt_id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    quiz_id = db.Column(db.Integer(), db.ForeignKey('quiz.quiz_id', ondelete='CASCADE'), nullable=False)
    attempt_time = db.Column(db.DateTime(), default=datetime.utcnow)
    answers = db.relationship('Answer', backref='attempt', cascade='all, delete-orphan', passive_deletes=True)
    
class Answer(db.Model):
    answer_id = db.Column(db.Integer(), primary_key=True)
    attempt_id = db.Column(db.Integer(), db.ForeignKey('quiz_attempt.attempt_id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer(), db.ForeignKey('question.ques_id', ondelete='CASCADE'), nullable=False)
    selected_option = db.Column(db.String(), nullable=False)
    is_correct = db.Column(db.Boolean(), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('attempt_id', 'question_id', name='uix_attempt_question'),
    )