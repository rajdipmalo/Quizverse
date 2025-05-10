from flask import Flask, render_template, redirect, request, session, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask import current_app as app
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
from rapidfuzz import fuzz
from sqlalchemy import text, func
from sqlalchemy.orm import joinedload
from collections import defaultdict
from app import db
import os


from models.models import *

bcrypt = Bcrypt(app)


@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u_name = request.form.get("username")
        pword = request.form.get("pass")
        my_user = User.query.filter_by(username=u_name).first()

        if my_user:
            if my_user.failed_attempts >= 5:
                if my_user.last_failed_attempt:
                    elapsed = (datetime.utcnow() - my_user.last_failed_attempt).seconds
                    lock_duration = 900
                    lock_seconds_remaining = lock_duration - elapsed

                    if lock_seconds_remaining <= 0:
                        my_user.failed_attempts = 0
                        my_user.last_failed_attempt = None
                        db.session.commit()
                        return redirect(url_for("login"))
                    else:
                        lock_time_remaining = max(1, lock_seconds_remaining // 60)
                        return render_template("locked_user.html", lock_time_remaining=lock_time_remaining, lock_seconds_remaining=lock_seconds_remaining)

            if bcrypt.check_password_hash(my_user.password, pword):
                login_user(my_user)
                
                session.permanent = True
                session['last_activity'] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

                my_user.failed_attempts = 0
                my_user.last_failed_attempt = None
                db.session.commit()

                if my_user.type == "admin":
                    return redirect("/admin")
                else:
                    return redirect(f"/home/{my_user.username}/{my_user.id}")
            else:
                my_user.failed_attempts += 1
                my_user.last_failed_attempt = datetime.utcnow()
                db.session.commit()
                return render_template("i_password.html")
        else:
            return render_template("n_exists.html")
        
    

    return render_template("login.html")

@app.route("/admin/unlock_user/<int:user_id>", methods=["POST"])
@login_required
def unlock_user(user_id):
    if current_user.type != "admin":
        return redirect("/login")

    user = User.query.get_or_404(user_id)
    user.failed_attempts = 0
    user.last_failed_attempt = None
    db.session.commit()

    flash(f"User '{user.username}' has been unlocked.", "success")

    
    search = request.args.get("search")
    option = request.args.get("option")
    if search and option and search.strip() and option.strip():
        return redirect(url_for("admin_search", search=search, option=option))


    return redirect(url_for("users_manage"))




@app.route("/register",methods=["GET","POST"])
def register():
    if request.method  == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        pword = request.form.get("pass")
        f_name = request.form.get("f_name")
        qua = request.form.get("qua")
        dob = request.form.get("dob")
        dob_obj = datetime.strptime(dob,"%Y-%m-%d").date()
        my_name = User.query.filter_by(username = username).first()
        my_email = User.query.filter_by(email=email).first()
        if my_name or my_email:
            return render_template("a_exists.html", url="/register", message="User already exists.")
        else:
            hashed_pword = bcrypt.generate_password_hash(pword).decode('utf-8')
            n_user = User(username = username, email = email, password = hashed_pword, full_name = f_name , qualification = qua, dob = dob_obj)
            db.session.add(n_user)
            db.session.commit()
            return redirect("/login")
        
    return render_template("register.html")


@app.route("/admin")
@login_required
def admin_dash():
    if current_user.type != "admin":
        return redirect("/login")
    subjects = Subject.query.all()
    for sub in subjects:
        sub.chapters = Chapter.query.filter_by(subject_id=sub.sub_id).all()
        for chap in sub.chapters:
            chap.no_of_quizzes = Quiz.query.filter_by(chapter_id = chap.chap_id).count()
            
    return render_template("admin_dash.html",my_user = current_user, subjects=subjects)

@app.route("/home/<string:username>/<int:user_id>")
@login_required
def user_dash(user_id, username):
    if current_user.id != user_id or current_user.username != username:
        return redirect("/login")
    if request.args.get('reset') == 'true':
        session.pop('attempt_id', None)
    
    
    quizzes = Quiz.query.options(
        joinedload(Quiz.chapter).joinedload(Chapter.subject)
    ).all()
    
    return render_template("user_dash.html", my_user=current_user, quizzes=quizzes, user_id=user_id)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")


@app.route('/users_manage')
@login_required
def users_manage():
    users = User.query.filter(User.type != 'admin').all()
    lock_duration_seconds = 900

    for user in users:
        user.is_locked = False
        if user.failed_attempts >= 5 and user.last_failed_attempt:
            elapsed = (datetime.utcnow() - user.last_failed_attempt).total_seconds()
            if elapsed < lock_duration_seconds:
                user.is_locked = True
            else:
                user.failed_attempts = 0
                user.last_failed_attempt = None
                db.session.commit()

    return render_template('user_manage.html', users=users)


@app.route('/delete_user/<int:user_id>', methods=["POST", "GET"])
@login_required
def delete_user(user_id):
    if current_user.type != "admin":
        return redirect("/login")

    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()

    search = request.args.get("search")
    option = request.args.get("option")
    if search and option:
        return redirect(url_for("admin_search", search=search, option=option))

    return redirect(url_for("users_manage"))


@app.route('/edit_user/<int:user_id>', methods=['GET','POST'])
@login_required
def edit_user(user_id):
    user = User.query.get(user_id)
    next_page = request.args.get('next')
    
    if request.method == "POST":
        
        new_username = request.form.get('username')
        new_email = request.form.get('email')

         
        e_username = User.query.filter(User.username == new_username, User.id != user_id).first()
        e_email = User.query.filter(User.email == new_email, User.id != user_id).first()

        if e_username or e_email:
            return render_template("a_exists.html", url=next_page, message="User already exists.")
        
        user.username = new_username
        user.email = new_email
        user.full_name = request.form.get('f_name')
        user.qualification =  request.form.get('qua')
        
        new_dob = request.form.get('dob')
        user.dob = datetime.strptime(new_dob, "%Y-%m-%d").date()
        
        new_password = request.form.get('new_password')

        if new_password:
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            user.password = hashed_password
        
        db.session.commit()
        return redirect(url_for('user_dash', username=user.username, user_id=user.id))
    return render_template("edit_user.html", user=user)

@app.route("/add_sub", methods=["GET","POST"])
@login_required
def add_sub():
    if request.method == "POST":
        sub_name = request.form.get("subject")
        sub_description = request.form.get("description")
        
        my_sub = Subject.query.filter_by(sub_name = sub_name).first()
        if my_sub:
            return render_template("a_exists.html", message="Subject already exists.", url="/add_sub")
        else:
            new_sub = Subject(sub_name = sub_name , sub_description = sub_description)
            db.session.add(new_sub)
            db.session.commit()
            
            return redirect("/admin")
        
    return render_template("new_sub.html")

@app.route("/delete_sub/<int:sub_id>", methods=["GET"])
@login_required
def delete_sub(sub_id):
    subject=Subject.query.get(sub_id)
    if subject:
        db.session.delete(subject)
        db.session.commit()
    return redirect('/admin')

@app.route("/edit_sub/<int:sub_id>", methods=['GET','POST'])
@login_required
def edit_sub(sub_id):
    subject = Subject.query.get(sub_id)
    
    if request.method == "POST":
        subject.sub_name = request.form.get('subject')
        subject.sub_description = request.form.get('description')
        db.session.commit()
        return redirect('/admin')
    return render_template('new_sub.html',subject=subject)

    
@app.route("/add_chap/<int:sub_id>", methods=["GET","POST"])
@login_required
def add_chap(sub_id):
    if request.method == "POST":
        chap_name = request.form.get("chapter")
        chap_description = request.form.get("description")
        
        my_chap = Chapter.query.filter_by(chap_name = chap_name, subject_id = sub_id).first()
        if my_chap:
            return render_template("a_exists.html", message="Chapter already exists.", url=f"/add_chap/{sub_id}")
        else:
            new_chap = Chapter(chap_name= chap_name,chap_description = chap_description, subject_id = sub_id)
            db.session.add(new_chap)
            db.session.commit()
            return redirect("/admin")
        
    return render_template("new_chap.html", subject_id = sub_id)
            

@app.route("/subject/<int:sub_id>")
@login_required
def view_chapters(sub_id):
    chapters = Chapter.query.filter_by(subject_id = sub_id).all()
    my_user = User.query.filter_by(type='admin').first()
    
    for chap in chapters:
        chap.quizzes = Quiz.query.filter_by(chapter_id = chap.chap_id).all()
        for quiz in chap.quizzes:
            quiz.no_of_ques = Question.query.filter_by(quiz_id=quiz.quiz_id).count()
            
    return render_template('chap.html', sub_id=sub_id, chapters=chapters, my_user=my_user)


@app.route("/delete_chap/<int:chap_id>", methods=['GET'])
@login_required
def delete_chap(chap_id):
    chapter = Chapter.query.get(chap_id)
    if chapter:
        db.session.delete(chapter)
        db.session.commit()
    return redirect(f'/admin')


@app.route("/edit_chap/<int:chap_id>", methods=['GET','POST'])
@login_required
def edit_chap(chap_id):
    chapter=Chapter.query.get(chap_id)
    
    if request.method == "POST":
        chapter.chap_name = request.form.get('chapter')
        chapter.chap_description = request.form.get('description')
        db.session.commit()
        return redirect("/admin")
    return render_template('new_chap.html',chapter=chapter)


@app.route("/add_quiz/<int:chap_id>", methods=["GET","POST"])
@login_required
def add_quiz(chap_id):
    if request.method =="POST":
        
        qz_name = request.form.get("qz_name")
        qz_date = request.form.get("qz_date")
        qz_duration = request.form.get("qz_duration")
        qz_date_new = datetime.strptime(qz_date,"%Y-%m-%d")
        
        
        new_quiz = Quiz(quiz_name = qz_name, chapter_id = chap_id,duration = int(qz_duration), date_of_quiz=qz_date_new)
        db.session.add(new_quiz)
        db.session.commit()
            
        chapter = Chapter.query.get(chap_id)
        sub_id = chapter.subject_id
        return redirect(f"/subject/{sub_id}")
        
    chapter = Chapter.query.get(chap_id)
    sub_id = chapter.subject_id
        
    return render_template('new_quiz.html',chap_id = chap_id,sub_id =sub_id)



@app.route('/delete_quiz/<int:quiz_id>', methods=['Get'])
@login_required
def delete_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if quiz:
        sub_id = quiz.chapter.subject_id
        db.session.delete(quiz)
        db.session.commit()
        return redirect(f'/subject/{sub_id}')
    return redirect('/admin')


@app.route('/edit_quiz/<int:quiz_id>', methods=['GET','POST'])
@login_required
def edit_quiz(quiz_id):
    quiz=Quiz.query.get(quiz_id)
    chapter=Chapter.query.get(quiz.chapter_id)
    sub_id = chapter.subject_id
    
    if request.method == "POST":
        quiz.quiz_name = request.form.get('qz_name')
        quiz.date_of_quiz = datetime.strptime(request.form.get('qz_date'), "%Y-%m-%d")
        quiz.duration = int(request.form.get('qz_duration'))
        db.session.commit()
        
        return redirect(f'/subject/{sub_id}')
    
    return render_template('new_quiz.html', quiz=quiz,chap_id=quiz.chapter_id,sub_id = sub_id)
        
        
@app.route('/quizzes/subject/<int:sub_id>/chapter/<int:chapter_id>')
@login_required
def view_quizzes( sub_id, chapter_id):
    quizzes = Quiz.query.filter_by(chapter_id = chapter_id).all()
    my_user = User.query.filter_by(type='admin').first()
    return render_template('quiz_manage.html', quizzes=quizzes,sub_id =sub_id, chapter_id = chapter_id, my_user=my_user)
 
 
@app.route('/add_ques/<int:quiz_id>', methods=["GET","POST"])
@login_required
def add_ques(quiz_id):
    quiz = Quiz.query.filter_by(quiz_id = quiz_id).first()
    sub_id = quiz.chapter.subject_id
    if request.method == 'POST':
        ques_title = request.form.get('q_title','').strip()
        ques_text = request.form.get('q_state','').strip()
        option1 = request.form.get('opt_1','').strip()
        option2 = request.form.get('opt_2','').strip()
        option3 = request.form.get('opt_3','').strip()
        option4 = request.form.get('opt_4','').strip()
        correct_option = request.form.get('crt_opt','').strip()
        
        new_question = Question(quiz_id = quiz_id, 
                                ques_title = ques_title, 
                                ques_text =ques_text, 
                                option1 = option1, 
                                option2 = option2, 
                                option3 = option3, 
                                option4 = option4,
                                correct_answer = correct_option)
        
        db.session.add(new_question)
        db.session.commit()
        return redirect(f'/add_ques/{quiz_id}')
    
    return render_template('new_question.html',quiz = quiz, quiz_id = quiz_id, sub_id = sub_id)
        

@app.route('/delete_ques/<int:quiz_id>/<int:ques_id>', methods=['GET'])
@login_required
def delete_ques(quiz_id,ques_id ):
    ques = Question.query.get(ques_id)
    if ques:
        db.session.delete(ques)
        db.session.commit()
        
    quiz = Quiz.query.get(quiz_id)
    if quiz:
        chapter = quiz.chapter
        sub_id = chapter.subject_id
        return redirect(f'/quizzes/subject/{sub_id}/chapter/{chapter.chap_id}')
    return redirect('/admin')

@app.route('/edit_ques/<int:quiz_id>/<int:ques_id>', methods=['GET','POST'])
@login_required
def edit_ques(quiz_id , ques_id):
    quiz = Quiz.query.filter_by(quiz_id = quiz_id).first()
    ques = Question.query.filter_by(ques_id=ques_id, quiz_id = quiz_id).first()
    sub_id=quiz.chapter.subject_id 
    
    if request.method =="POST" and ques:
        ques.ques_title = request.form.get('q_title','').strip()
        ques.ques_text = request.form.get('q_state','').strip()
        ques.option1 = request.form.get('opt_1','').strip()
        ques.option2 = request.form.get('opt_2','').strip()
        ques.option3 = request.form.get('opt_3','').strip()
        ques.option4  = request.form.get('opt_4','').strip()
        ques.correct_answer = request.form.get('crt_opt','').strip()
        
        db.session.commit()
        return redirect(f'/quizzes/subject/{sub_id}/chapter/{quiz.chapter_id}')
    return render_template('new_question.html', quiz=quiz,quiz_id=quiz_id, question=ques, sub_id=sub_id)





@app.route('/<string:username>/<int:user_id>/view_quiz/<int:quiz_id>')
@login_required
def view_quiz(quiz_id,user_id,username):
    quiz = Quiz.query.filter_by(quiz_id = quiz_id).first()
    user = User.query.filter_by(id = user_id,username=username).first()
    return render_template('view_quiz.html',quiz=quiz, my_user=user)





@app.route('/start_quiz/<string:username>/<int:user_id>/quiz/<int:quiz_id>/ques_index/<int:ques_index>', methods=['GET','POST'])
@login_required
def start_quiz(username,user_id, quiz_id, ques_index=0):
    my_user=User.query.filter_by(id=user_id,username=username).first()
    quiz = Quiz.query.filter_by(quiz_id=quiz_id).first()
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    total_ques = len(questions)
    
    if total_ques == 0:
        return render_template('no_ques.html',my_user=my_user)
    
    curr_date = datetime.utcnow().date()
    if quiz.date_of_quiz.date()>curr_date:
        return render_template('quiz_ns.html', message=f"The quiz will start on {quiz.date_of_quiz.date()}. Please come later.", my_user=my_user)
    
        
    timeout = request.args.get('timeout',False)
    if timeout:
        return redirect(f'/quiz_result/{username}/{user_id}/quiz/{quiz_id}')
    
    attempt = None
    attempt_id = session.get('attempt_id')

    if attempt_id:
        attempt = QuizAttempt.query.get(attempt_id)
        if not attempt:
            session.pop('attempt_id', None)
    if not attempt:
        attempt = QuizAttempt(user_id=user_id, quiz_id=quiz_id)
        db.session.add(attempt)
        db.session.commit()
        session['attempt_id'] = attempt.attempt_id
        
    if request.method == 'POST':
        question = questions[ques_index]
        selected_option = request.form.get('ans')
        
        
        if selected_option:
            existing_answer = Answer.query.filter_by(
                attempt_id=attempt.attempt_id,
                question_id=question.ques_id
            ).first()
            
            if not existing_answer:
                is_correct = (selected_option == question.correct_answer)
                answer = Answer(
                    attempt_id=attempt.attempt_id,
                    question_id=question.ques_id,
                    selected_option=selected_option,
                    is_correct=is_correct
                )
                db.session.add(answer)
                db.session.commit()
        
        if ques_index+1 < total_ques:
            return redirect(f'/start_quiz/{username}/{user_id}/quiz/{quiz_id}/ques_index/{ques_index+1}')
        else:
            return redirect(f'/quiz_result/{username}/{user_id}/quiz/{quiz_id}')
        
        
    question = questions[ques_index]
    selected_ans = None
    if attempt:
        saved_answer = Answer.query.filter_by(
            attempt_id=attempt.attempt_id,
            question_id=question.ques_id
        ).first()
        if saved_answer:
            selected_ans = saved_answer.selected_option
    
    duration = int(quiz.duration)
        
    return render_template('quiz.html',quiz=quiz, question=questions[ques_index], ques_index = ques_index, total_questions = total_ques, user_id = user_id , username =username, duration=duration, selected_ans=selected_ans)




@app.route('/quiz_result/<string:username>/<int:user_id>/quiz/<int:quiz_id>') 
@login_required
def quiz_result(username, user_id, quiz_id):
    my_user = User.query.get_or_404(user_id)
    quiz = Quiz.query.get_or_404(quiz_id)
    attempt_id = session.pop('attempt_id', None)
    
    if attempt_id is None:
        return "Invalid access or session expired.", 403
    
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    answers = Answer.query.filter_by(attempt_id=attempt_id).all()
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    
    total_questions = len(questions)
    correct_count = sum(ans.is_correct for ans in answers)
    
    if total_questions > 0:
        percentage_score = (correct_count / total_questions) * 100
    else:
        percentage_score = 0.0 
        
    new_score = Score(
        u_id=user_id,
        q_id=quiz_id,
        total_score=round(percentage_score, 2), 
        attempt_id=attempt.attempt_id
    )
    db.session.add(new_score)
    db.session.commit()
    
    return render_template('results.html', questions=questions, answers=answers, score=round(percentage_score, 2), my_user=my_user)


@app.route('/quiz_result/<string:username>/<int:user_id>/quiz/<int:quiz_id>/score/<int:score_id>')
@login_required
def quiz_result_by_attempt(username, user_id, quiz_id, score_id):
    my_user = User.query.get_or_404(user_id)
    quiz = Quiz.query.get_or_404(quiz_id)
    score = Score.query.get_or_404(score_id)
    attempt = QuizAttempt.query.get_or_404(score.attempt_id)

    answers = Answer.query.filter_by(attempt_id=attempt.attempt_id).all()
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    
    return render_template('results.html', questions=questions, answers=answers, score=score.total_score, my_user=my_user)


    
@app.route('/<string:username>/<int:user_id>/scores')
@login_required
def user_scores(user_id,username):
    scores = Score.query.filter_by(u_id= user_id).order_by(Score.attempt_date.desc()).all()
    my_user = User.query.filter_by(id=user_id,username=username).first()
    return render_template('scores.html',scores=scores,my_user=my_user)



@app.route('/admin/search')
@login_required
def admin_search():
    if current_user.type != "admin":
        return redirect("/login")

    query = request.args.get("search", "").strip().lower()
    que = request.args.get("search")
    option = request.args.get("option", "").lower()

    if not query or option not in ["user", "sub", "chap", "quiz"]:
        return redirect("/admin")

    if option == "user":
        users = User.query.filter(User.type != 'admin').all()
        matched_users = [u for u in users if fuzz.partial_ratio(query, u.username.lower()) >= 80]


        lock_duration = 900  
        for user in matched_users:
            user.is_locked = False
            if user.failed_attempts >= 5 and user.last_failed_attempt:
                elapsed = (datetime.utcnow() - user.last_failed_attempt).total_seconds()
                if elapsed < lock_duration:
                    user.is_locked = True
                else:
                    user.failed_attempts = 0
                    user.last_failed_attempt = None
                    db.session.commit()

        return render_template("user_manage.html", users=matched_users, search=que, option=option)

    elif option == "sub":
        subjects = Subject.query.all()
        for sub in subjects:
            sub.chapters = Chapter.query.filter_by(subject_id=sub.sub_id).all()
            for chap in sub.chapters:
                chap.no_of_quizzes = Quiz.query.filter_by(chapter_id=chap.chap_id).count()

        matched_subjects = [s for s in subjects if fuzz.partial_ratio(query, s.sub_name.lower()) >= 80]
        return render_template("admin_dash.html", subjects=matched_subjects, my_user=current_user, search=que, option=option)

    elif option == "chap":
        chapters = Chapter.query.all()
        matched_chaps = [c for c in chapters if fuzz.partial_ratio(query, c.chap_name.lower()) >= 80]

        for chap in matched_chaps:
            chap.quizzes = Quiz.query.filter_by(chapter_id=chap.chap_id).all()
            for quiz in chap.quizzes:
                quiz.no_of_ques = Question.query.filter_by(quiz_id=quiz.quiz_id).count()

        sub_id = matched_chaps[0].subject_id if matched_chaps else None
        return render_template("chap.html", chapters=matched_chaps, my_user=current_user, sub_id=sub_id, search=que, option=option)

    elif option == "quiz":
        quizzes = Quiz.query.join(Chapter).join(Subject).all()
        matched_quizzes = [q for q in quizzes if fuzz.partial_ratio(query, q.quiz_name.lower()) >= 80]

        sub_id = matched_quizzes[0].chapter.subject_id if matched_quizzes else None
        chap_id = matched_quizzes[0].chapter_id if matched_quizzes else None
        return render_template("quiz_manage.html", quizzes=matched_quizzes, my_user=current_user, sub_id=sub_id, chapter_id=chap_id, search=que, option=option)

    return redirect("/admin")


@app.route("/user/search/<int:user_id>")
@login_required
def user_search(user_id):
    query = request.args.get("search", "").strip().lower()
    option = request.args.get("option", "").lower()
    
    qur = request.args.get("search")
    

    if not query or option not in ["sub", "chap", "quiz"]:
        return redirect(f"/home/{current_user.username}/{user_id}")

    quizzes = Quiz.query.join(Chapter).join(Subject).all()

    filtered_quizzes = []

    for quiz in quizzes:
        if option == "sub":
            target = quiz.chapter.subject.sub_name.strip().lower()
        elif option == "chap":
            target = quiz.chapter.chap_name.strip().lower()
        elif option == "quiz":
            target = quiz.quiz_name.strip().lower()
        else:
            continue

        if fuzz.partial_ratio(query, target) >= 80:
            filtered_quizzes.append(quiz)

    return render_template("user_dash.html", my_user=current_user, quizzes=filtered_quizzes, user_id=user_id, search_query=qur, search_option=option)



folder = "static"

@app.route('/admin/summary')
@login_required
def admin_summary():
    q1 = text("""select s.sub_name, c.chap_name, q.quiz_name, u.username, ts.total_score
        from score ts
        join quiz q on ts.q_id = q.quiz_id
        join chapter c on q.chapter_id = c.chap_id
        join subject s on c.subject_id = s.sub_id
        join user u on ts.u_id = u.id
        where  ts.total_score in (
           select distinct total_score from score ts2
           where ts2.q_id = ts.q_id order by total_score desc limit 1
        )
        order by s.sub_name, q.quiz_name, ts.total_score desc
        """)
    top = db.session.execute(q1).fetchall()
    
    q2 = text("""
              select u.username, q.quiz_name, count(ts.q_id) as quiz_attemp,
              round(avg(ts.total_score),2) as avg_score
              from user u left join score ts on u.id = ts.u_id 
              left join quiz q on ts.q_id = q.quiz_id
              where u.type != 'admin'
              group by u.username, q.quiz_name 
              order by u.username, quiz_attemp desc
              """)
    
    user_data = db.session.execute(q2).fetchall()
    
    thirty_days_ago = datetime.now() - timedelta(days=30)
    q3 = text("""
        select date(attempt_time) as attempt_date, count(*) as attempt_count
        from quiz_attempt
        where attempt_time >= :start_date
        group by date(attempt_time)
        order by attempt_date
        """)
    attempt_data = db.session.execute(q3, {'start_date': thirty_days_ago}).fetchall()
    
    # Format for Chart.js
    attempt_labels = [str(row[0]) for row in attempt_data]
    attempt_values = [row[1] for row in attempt_data]
    
    user_growth_data = db.session.query(
        func.date(User.registration_date).label('date'),
        func.count(User.id).label('count')
    ).filter(User.type != 'admin').group_by(func.date(User.registration_date)).order_by('date').all()

# Format for JavaScript
    user_growth = {
        'dates': [str(row.date) for row in user_growth_data],
        'counts': [row.count for row in user_growth_data]
    }


    
    # Quiz Participation
    quiz_participation_data = db.session.query(
        Quiz.quiz_name,
        func.count(QuizAttempt.attempt_id).label('attempt_count')
    ).join(QuizAttempt).group_by(Quiz.quiz_name).all()
    
    quiz_participation = {
        'quizzes': [row.quiz_name for row in quiz_participation_data],
        'attempts': [row.attempt_count for row in quiz_participation_data]
    }
    
    # User Participation
    user_participation_data = db.session.query(
        User.username,
        func.count(QuizAttempt.attempt_id).label('attempt_count')
    ).join(QuizAttempt).group_by(User.username)\
     .order_by(func.count(QuizAttempt.attempt_id).desc()).limit(20).all()
    
    user_participation = {
        'users': [row.username for row in user_participation_data],
        'attempts': [row.attempt_count for row in user_participation_data]
    }

    
    
    return render_template('admin_summary.html', 
                            top=top,
                            user_data=user_data,
                            attempt_labels=attempt_labels,
                            attempt_values=attempt_values,
                            user_growth=user_growth,
                            quiz_participation=quiz_participation,
                            user_participation=user_participation)
    
    



@app.route('/<username>/summary')
@login_required
def user_summary(username):
    user = User.query.filter_by(username=username).first_or_404()

    
    all_scores = Score.query.filter_by(u_id=user.id).order_by(Score.attempt_date).all()

    total_attempts = len(all_scores)
    score_values = [s.total_score for s in all_scores]
    avg_score = sum(score_values) / total_attempts if total_attempts else 0
    best_score = max(score_values) if score_values else 0
    worst_score = min(score_values) if score_values else 0

   
    sub_performance = db.session.query(
        Subject.sub_name,
        func.count(Score.id),  
        func.avg(Score.total_score),
        func.round(func.avg(Score.total_score), 2)
    ).join(Chapter, Chapter.subject_id == Subject.sub_id) \
     .join(Quiz, Quiz.chapter_id == Chapter.chap_id) \
     .join(Score, Score.q_id == Quiz.quiz_id) \
     .filter(Score.u_id == user.id) \
     .group_by(Subject.sub_name).all()

    
    bar_labels = [sub_name for sub_name, _, _, _ in sub_performance]
    bar_data = [avg_score for _, _, avg_score, _ in sub_performance]

    
    doughnut_labels = [sub_name for sub_name, count, _, _ in sub_performance]
    doughnut_data = [count for _, count, _, _ in sub_performance]

    
    score_dates = [s.attempt_date.strftime("%Y-%m-%d") for s in all_scores]
    score_data = [s.total_score for s in all_scores]

    subject_scores = defaultdict(lambda: {'dates': [], 'scores': []})

    for score in all_scores:
        quiz = Quiz.query.get(score.q_id)
        if quiz:
            chapter = Chapter.query.get(quiz.chapter_id)
            if chapter:
                subject = Subject.query.get(chapter.subject_id)
                if subject:
                    subject_scores[subject.sub_name]['dates'].append(score.attempt_date.strftime("%Y-%m-%d"))
                    subject_scores[subject.sub_name]['scores'].append(score.total_score)
    
    return render_template(
        'user_summary.html',
        my_user=user,
        total=total_attempts,
        avg=avg_score,
        best=best_score,
        worst=worst_score,
        sub_performance=sub_performance,
        score_dates=score_dates,
        score_data=score_data,
        bar_labels=bar_labels,
        bar_data=bar_data,
        doughnut_labels=doughnut_labels,
        doughnut_data=doughnut_data,
        subject_scores=subject_scores
    )