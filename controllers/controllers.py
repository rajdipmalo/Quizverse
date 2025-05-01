from flask import Flask, render_template, redirect, request
from flask import current_app as app
from datetime import datetime
from sqlalchemy import text
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import os


from models.models import *


@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method == "POST":
        u_name = request.form.get("username")
        pword = request.form.get("pass")
        my_user = User.query.filter_by(username = u_name).first()
        if my_user:
            if my_user.password == pword:
                if my_user.type == "admin":
                    return redirect("/admin")
                else:
                    return redirect(f"/home/{my_user.username}/{my_user.id}")
            else:
                return render_template("i_password.html")
        else:
            return render_template("n_exists.html")
        
    return render_template("login.html")

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
            n_user = User(username = username, email = email, password = pword, full_name = f_name , qualification = qua, dob = dob_obj)
            db.session.add(n_user)
            db.session.commit()
            return redirect("/login")
        
    return render_template("register.html")


@app.route("/admin")
def admin_dash():
    my_user = User.query.filter_by(type="admin").first()
    subjects = Subject.query.all()
    for sub in subjects:
        sub.chapters = Chapter.query.filter_by(subject_id=sub.sub_id).all()
        for chap in sub.chapters:
            chap.no_of_quizzes = Quiz.query.filter_by(chapter_id = chap.chap_id).count()
            
    return render_template("admin_dash.html",my_user = my_user, subjects=subjects)

@app.route("/home/<string:username>/<int:user_id>")
def user_dash(user_id,username):
    my_user = User.query.filter_by(id = user_id).first()
    quizzes = Quiz.query.all()
    return render_template("user_dash.html", my_user=my_user, quizzes = quizzes, user_id=user_id)

@app.route("/add_sub", methods=["GET","POST"])
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
def delete_sub(sub_id):
    subject=Subject.query.get(sub_id)
    for chapter in subject.chapters:
        for quiz in chapter.quizzes:
            for score in quiz.scores:
                db.session.delete(score)
            for question in quiz.questions:
                db.session.delete(question)
            db.session.delete(quiz)
        db.session.delete(chapter)
        
    db.session.delete(subject)
    db.session.commit()
    
    return redirect('/admin')

@app.route("/edit_sub/<int:sub_id>", methods=['GET','POST'])
def edit_sub(sub_id):
    subject = Subject.query.get(sub_id)
    
    if request.method == "POST":
        subject.sub_name = request.form.get('subject')
        subject.sub_description = request.form.get('description')
        db.session.commit()
        return redirect('/admin')
    return render_template('new_sub.html',subject=subject)

    
@app.route("/add_chap/<int:sub_id>", methods=["GET","POST"])
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
def view_chapters(sub_id):
    chapters = Chapter.query.filter_by(subject_id = sub_id).all()
    my_user = User.query.filter_by(type='admin').first()
    
    for chap in chapters:
        chap.quizzes = Quiz.query.filter_by(chapter_id = chap.chap_id).all()
        for quiz in chap.quizzes:
            quiz.no_of_ques = Question.query.filter_by(quiz_id=quiz.quiz_id).count()
            
    return render_template('chap.html', sub_id=sub_id, chapters=chapters, my_user=my_user)


@app.route("/delete_chap/<int:chap_id>", methods=['GET'])
def delete_chap(chap_id):
    chapter = Chapter.query.get(chap_id)
    
    for quiz in chapter.quizzes:
        for score in quiz.scores:
            db.session.delete(score)
        for question in quiz.questions:
            db.session.delete(question)
        db.session.delete(quiz)
        
        
    db.session.delete(chapter)
    db.session.commit()
    return redirect(f'/admin')


@app.route("/edit_chap/<int:chap_id>", methods=['GET','POST'])
def edit_chap(chap_id):
    chapter=Chapter.query.get(chap_id)
    
    if request.method == "POST":
        chapter.chap_name = request.form.get('chapter')
        chapter.chap_description = request.form.get('description')
        db.session.commit()
        return redirect("/admin")
    return render_template('new_chap.html',chapter=chapter)


@app.route("/add_quiz/<int:chap_id>", methods=["GET","POST"])
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
def delete_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    sub_id = quiz.chapter.subject_id
    
    for score in quiz.scores:
        db.session.delete(score)
    for question in quiz.questions:
        db.session.delete(question)
    db.session.delete(quiz)
    db.session.commit()
    
    return redirect(f'/subject/{sub_id}')


@app.route('/edit_quiz/<int:quiz_id>', methods=['GET','POST'])
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
def view_quizzes( sub_id, chapter_id):
    quizzes = Quiz.query.filter_by(chapter_id = chapter_id).all()
    my_user = User.query.filter_by(type='admin').first()
    return render_template('quiz_manage.html', quizzes=quizzes,sub_id =sub_id, chapter_id = chapter_id, my_user=my_user)
 
 
@app.route('/add_ques/<int:quiz_id>', methods=["GET","POST"])
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
def delete_ques(quiz_id,ques_id ):
    ques = Question.query.get(ques_id)
    if ques:
        db.session.delete(ques)
        db.session.commit()
        
    quiz = Quiz.query.get(quiz_id)
    chapter = quiz.chapter
    sub_id = chapter.subject_id
        
    return redirect(f'/quizzes/subject/{sub_id}/chapter/{chapter.chap_id}')

@app.route('/edit_ques/<int:quiz_id>/<int:ques_id>', methods=['GET','POST'])
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


@app.route("/users_manage")
def user_manage():
    users = User.query.filter_by(type='general').all()
    my_user = User.query.filter_by(type='admin').first()
    return render_template('user_manage.html', users=users,my_user=my_user)


@app.route('/delete_user/<int:user_id>', methods=["POST","GET"])
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        scores = Score.query.filter_by(u_id = user_id).all()
        for score in scores:
            db.session.delete(score)
            
    db.session.delete(user)
    db.session.commit()
    
    return redirect("/users_manage")

@app.route('/edit_user/<int:user_id>', methods=['GET','POST'])
def edit_user(user_id):
    user = User.query.get(user_id)
    
    if request.method == "POST":
        
        new_username = request.form.get('username')
        new_email = request.form.get('email')

        
        e_username = User.query.filter(User.username == new_username).first()
        e_email = User.query.filter(User.email == new_email).first()
        
        
        if e_username or e_email:
            return render_template("a_exists.html", url = "/users_manage", message="User already exists.")
        
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.password = request.form.get('pass')
        user.full_name = request.form.get('f_name')
        user.qualification =  request.form.get('qua')
        user.dob = request.form.get('dob')
        
        db.session.commit()
        return redirect("/users_manage")
    return render_template("edit_user.html", user=user)



@app.route('/<string:username>/<int:user_id>/view_quiz/<int:quiz_id>')
def view_quiz(quiz_id,user_id,username):
    quiz = Quiz.query.filter_by(quiz_id = quiz_id).first()
    user = User.query.filter_by(id = user_id,username=username).first()
    return render_template('view_quiz.html',quiz=quiz, my_user=user)



user_answer_store = {}

@app.route('/start_quiz/<string:username>/<int:user_id>/quiz/<int:quiz_id>/ques_index/<int:ques_index>', methods=['GET','POST'])
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
    # elif quiz.date_of_quiz.date()<curr_date:
    #     return render_template('quiz_ns.html', message=f"The quiz is over. You can no longer appempt it.", my_user=my_user)
    
    if user_id not in user_answer_store:
        user_answer_store[user_id] = {}
        
    timeout = request.args.get('timeout',False)
    if timeout:
        return redirect(f'/quiz_result/{username}/{user_id}/quiz/{quiz_id}')
        
    if request.method == 'POST':
        question = questions[ques_index]
        user_answer = request.form.get('ans')
        user_answer_store[user_id][question.ques_id] = user_answer
        
        if ques_index+1 < total_ques:
            return redirect(f'/start_quiz/{username}/{user_id}/quiz/{quiz_id}/ques_index/{ques_index+1}')
        else:
            return redirect(f'/quiz_result/{username}/{user_id}/quiz/{quiz_id}')
    
    duration = int(quiz.duration)
        
    return render_template('quiz.html',quiz=quiz, question=questions[ques_index], ques_index = ques_index, total_questions = total_ques, user_id = user_id , username =username, duration=duration)




@app.route('/quiz_result/<string:username>/<int:user_id>/quiz/<int:quiz_id>')
def quiz_result(username,user_id,quiz_id):
    questions = Question.query.filter_by(quiz_id = quiz_id).all()
    user_ans = user_answer_store.pop(user_id,{})
    my_user=User.query.get(user_id)
    
    correct_count = sum(user_ans.get(q.ques_id) ==q.correct_answer for q in questions)
    total_questions = len(questions)
    
    new_score = Score(u_id=user_id,q_id=quiz_id,total_score=correct_count,attempt_date=datetime.utcnow())
    db.session.add(new_score)
    db.session.commit()
    
    return render_template('results.html',questions=questions,user_ans=user_ans,score=correct_count,my_user=my_user)
    
@app.route('/<string:username>/<int:user_id>/scores')
def user_scores(user_id,username):
    scores = Score.query.filter_by(u_id= user_id).order_by(Score.attempt_date.desc()).all()
    my_user = User.query.filter_by(id=user_id,username=username).first()
    return render_template('scores.html',scores=scores,my_user=my_user)


@app.route('/admin/search', methods=['GET'])
def search():
    search = request.args.get('search')
    option = request.args.get('option')
    
    my_user = User.query.filter_by(type = 'admin').first()
    
    res=[]
    
    if search and option:
        if option == 'user':
            res = User.query.filter((User.username==search) | (User.email==search) | (User.full_name == search)).all()
        elif option == "sub":
            res = Subject.query.filter(Subject.sub_name == search).all()
        elif option == 'chap':
            res = Chapter.query.filter(Chapter.chap_name == search).all()
        elif option == 'quiz':
            res = Quiz.query.filter(Quiz.quiz_name == search).all()
            
            
        
    return render_template('admin_search.html', result = res , option=option, search = search, my_user = my_user)

@app.route('/user/search/<int:user_id>', methods=['GET'])
def user_search(user_id):
    search = request.args.get('search')
    option = request.args.get('option')
    my_user = User.query.get(user_id)
    
    res=[]
    
    if search and option:
        if option == 'quiz':
            res =  Quiz.query.filter(Quiz.quiz_name == search).all()
        elif option == 'chap':
            res = Quiz.query.filter(Quiz.chapter_id == Chapter.chap_id, Chapter.chap_name == search)
        elif option == 'sub':
            res = Quiz.query.filter(Quiz.chapter_id == Chapter.chap_id, Chapter.subject_id == Subject.sub_id, Subject.sub_name == search).all() 
            
    return render_template('user_search.html', res = res, search = search, option = option, my_user = my_user, user_id=user_id )



folder = "static"

@app.route('/admin/summary')
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
    
    
    user_q = text("""
                  select u.username, count(ts.q_id) as attempts
                  from user u left join score ts on u.id = ts.u_id
                  where u.type != 'admin' group by u.username order by attempts desc
                  """)
    
    user_attempts = db.session.execute(user_q).fetchall()
    user_name = [row.username for row in user_attempts]
    attempt_counts = [row.attempts for row in user_attempts]
    
    
    plt.figure()
    plt.bar(user_name,attempt_counts, color='skyblue')
    plt.xlabel("Users")
    plt.ylabel("Attempts")
    plt.title("User Quiz Attempts")
    plt.xticks(rotation=45, ha='right')
    # user_path = os.path.join(folder, "user_attempt.png")
    plt.savefig("static/user_attempt.png")
    plt.close()
    
    
    sub_q = text("""
                 select s.sub_name ,count(ts.q_id) as attempts
                 from subject s join chapter c on s.sub_id = c.subject_id
                 join quiz q on c.chap_id = q.chapter_id
                 join score ts on q.quiz_id = ts.q_id
                 group by s.sub_name order by attempts desc
                 """)
    sub_attempts = db.session.execute(sub_q).fetchall()
    subject = [row.sub_name for row in sub_attempts]
    sub_counts = [row.attempts for row in sub_attempts]
    
    plt.figure()
    plt.bar(subject, sub_counts, color='lightcoral')
    plt.xlabel("Subjects")
    plt.ylabel("Quiz Attempts")
    plt.title("Subject wise Quiz Attempts")
    plt.xticks(rotation=45, ha='right')
    plt.savefig("static/sub_attempt.png")
    plt.close()
    
    
    
    scores = db.session.query(Score).all()
    dict = {}
    
    for score in scores:
        date = score.attempt_date.strftime("%Y-%m-%d")
        if date in dict:
            dict[date] += 1
        else:
            dict[date] = 1
            
    dates = sorted(dict.keys())
    attempt = [dict[date] for date in dates]
    
    plt.figure()
    plt.plot(dates, attempt, marker="o", linestyle="-", color="r", label="Quiz Attempts")
    plt.xlabel("Date")
    plt.ylabel("Quiz Attempts")
    plt.title("Quiz Attempts vs Time")
    plt.legend()
    
    plt.savefig("static/quiz_participation.png")
    plt.close()
    
    
    scores = db.session.query(Score).all()
    score_dict = {}

    for score in scores:
        date = score.attempt_date.strftime("%Y-%m-%d")
        if date in score_dict:
            score_dict[date] += score.total_score
        else:
            score_dict[date] = score.total_score

    dates = sorted(score_dict.keys())
    total_scores = [score_dict[date] for date in dates]

    plt.figure()
    plt.plot(dates, total_scores, marker="o", linestyle="-", color="orange", label="Total Score")
    plt.xlabel("Date")
    plt.ylabel("Total Score")
    plt.title("Total Scores Over Time")
    plt.xticks(rotation=45, ha='right')
    plt.legend()

    plt.savefig("static/total_scores.png")
    plt.close()

    
    return render_template('admin_summary.html', top=top, user_data=user_data, user_chart="user_attempt.png", subject_chart = "subject_attempt.png" , participation_chart = "quiz_participation.png", p_chart="total_scores.png")



@app.route('/<username>/summary')
def user_summary(username):
    my_user = User.query.filter_by(username = username).first()
    
    scores = Score.query.filter_by(u_id = my_user.id).all()
    total = len(scores)
    avg = sum(score.total_score for score in scores)/total if total > 0 else 0
    if scores:
        best = max(score.total_score for score in scores)
        worst = min(score.total_score for score in scores)
    else:
        best=0
        worst=0
    
    sub_performance = db.session.execute(
        text("""select s.sub_name, count(ts.q_id) as quiz_attempted , avg(ts.total_score) as avg_score
    from score ts join quiz q on ts.q_id = q.quiz_id join chapter c on q.chapter_id = c.chap_id
    join subject s on c.subject_id = s.sub_id where ts.u_id = :user_id group by s.sub_name
    """), {"user_id": my_user.id}).fetchall()
    
    sub = [row[0] for row in sub_performance]
    avg_score = [row[2] for row in sub_performance]
    
    plt.figure()
    plt.bar(sub, avg_score, color='skyblue')
    plt.xlabel("Subjects")
    plt.ylabel("Average Score")
    plt.title(f"{username}'s subject wise performance")
    
    plt.savefig(f"static/{username}_performance.png")
    plt.close()
    
    
    user_performance = db.session.execute(
        text("""
             select ts.attempt_date, ts.total_score
             from score ts where ts.u_id = :user_id
             order by ts.attempt_date"""),{"user_id": my_user.id}
    ).fetchall()
    
    if user_performance:
        dates = [datetime.strptime(str(row[0]), '%Y-%m-%d %H:%M:%S.%f') for row in user_performance]
        scores = [row[1] for row in user_performance]
        
        plt.figure()
        plt.plot(dates, scores, marker='o', color='b')
        plt.xlabel("Date", fontsize=12)
        plt.ylabel("Score", fontsize=12)
        plt.title(f"{username}'s Performance Trend over Time")
        path  = f"static/{username}_trend.png"
        plt.savefig(path)
        plt.close()
    else:
        path = None
        
    
    return render_template("user_summary.html", my_user=my_user,username = username, total=total, avg=avg, best=best, worst=worst, sub_performance=sub_performance, performance_chart = "f{username}_performance.png", path=path)