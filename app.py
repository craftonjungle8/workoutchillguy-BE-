from flask import Flask, request, render_template, redirect, url_for, make_response, jsonify
from flask_pymongo import PyMongo
import bcrypt
import jwt
import datetime
from bson import ObjectId

app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key"  # 실제 환경에서는 안전하게 보관 (.env 등)
app.config["MONGO_URI"] = "mongodb://localhost:27017/1weekmini"

mongo = PyMongo(app)
users_collection = mongo.db.users
boards_collection = mongo.db.boards      # 게시판 글
exercises_collection = mongo.db.exercises  # 운동일기

@app.route("/")
def home():
    current_user = get_current_user()
    if current_user:
        return redirect(url_for("mainpage"))
    else:
        return redirect(url_for("login_page"))

# JWT 쿠키 검증 헬퍼 함수
def get_current_user():
    token = request.cookies.get("jwt_token")
    if not token:
        return None
    try:
        data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        user_id = data["user_id"]
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        return user
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

# 회원가입 페이지 및 처리
@app.route("/signup", methods=["GET"])
def signup_page():
    return render_template("signup/signup.html")

@app.route("/signup", methods=["POST"])
def signup():
    nickname = request.form.get("nickname")
    email = request.form.get("email")
    password = request.form.get("password")
    if users_collection.find_one({"email": email}):
        return render_template("signup/signup.html", error="이미 가입된 이메일입니다.")
    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    users_collection.insert_one({
        "nickname": nickname,
        "email": email,
        "password": hashed_pw
    })
    return redirect(url_for("login_page"))

# 로그인 페이지 및 처리
@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login/login.html")

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")
    user = users_collection.find_one({"email": email})
    if not user or not bcrypt.checkpw(password.encode("utf-8"), user["password"]):
        return render_template("login/login.html", error="이메일/비밀번호가 잘못되었습니다.")
    token = jwt.encode(
        {
            "user_id": str(user["_id"]),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        },
        app.config["SECRET_KEY"],
        algorithm="HS256"
    )
    resp = make_response(redirect(url_for("mainpage")))
    resp.set_cookie("jwt_token", token, httponly=True, samesite="Strict")
    return resp

# 로그아웃
@app.route("/logout", methods=["GET"])
def logout():
    resp = make_response(redirect(url_for("login_page")))
    resp.set_cookie("jwt_token", "", expires=0)
    return resp

# 마이페이지
@app.route("/mypage", methods=["GET"])
def mypage():
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))
    nickname = current_user.get("nickname", "")
    posts_cursor = boards_collection.find({"user_id": current_user["_id"]}).sort("created_at", -1)
    my_posts = []
    for p in posts_cursor:
        my_posts.append({
            "id": str(p["_id"]),
            "title": p["title"],
            "content": p["content"],
            "created_at": (p["created_at"] + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M") if "created_at" in p else ""
        })
    return render_template("mypage/mypage.html", nickname=nickname, my_posts=my_posts)

@app.route("/mypage/update", methods=["POST"])
def update_mypage():
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))
    new_nickname = request.form.get("nickname")
    new_password = request.form.get("password")
    update_fields = {"nickname": new_nickname}
    if new_password:
        hashed_pw = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
        update_fields["password"] = hashed_pw
    users_collection.update_one({"_id": current_user["_id"]}, {"$set": update_fields})
    return redirect(url_for("mypage"))

# 메인페이지 – 달력 및 차트 (UI는 클라이언트에서 렌더링)
@app.route("/mainpage", methods=["GET"])
def mainpage():
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))
    nickname = current_user.get("nickname", "")
    email = current_user["email"]
    return render_template("mainpage/mainpage.html", nickname=nickname, email=email)

# API: 지정 연/월의 날짜별 운동 기록 상태
@app.route("/api/calendar_status", methods=["GET"])
def api_calendar_status():
    current_user = get_current_user()
    if not current_user:
        return jsonify({}), 401
    try:
        year = int(request.args.get("year"))
        month = int(request.args.get("month"))
    except (TypeError, ValueError):
        return jsonify({"error": "잘못된 파라미터"}), 400
    user_id = current_user["_id"]
    first_day = datetime.date(year, month, 1)
    if month == 12:
        next_month_first_day = datetime.date(year+1, 1, 1)
    else:
        next_month_first_day = datetime.date(year, month+1, 1)
    last_day = next_month_first_day - datetime.timedelta(days=1)
    today = datetime.date.today()
    month_str = f"{year:04d}-{month:02d}-"
    exercise_docs = exercises_collection.find({
        "user_id": user_id,
        "date": {"$regex": f"^{month_str}"}
    })
    day_status = {}
    day_to_records = {}
    for doc in exercise_docs:
        d = doc["date"]
        day_to_records.setdefault(d, []).append(doc)
    for day in range(1, last_day.day + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        current_day = datetime.date(year, month, day)
        if current_day > today:
            status = "future"
        else:
            records = day_to_records.get(date_str, [])
            if not records:
                status = "no_records"
            else:
                all_checked = all(rec.get("checked", False) for rec in records)
                status = "all_checked" if all_checked else "some_unchecked"
        day_status[date_str] = status
    return jsonify(day_status)

# API: 이번달 출석률 (오늘 이전 날짜 기준)
@app.route("/api/attendance_rate", methods=["GET"])
def api_attendance_rate():
    current_user = get_current_user()
    if not current_user:
        return jsonify({}), 401
    try:
        year = int(request.args.get("year"))
        month = int(request.args.get("month"))
    except (TypeError, ValueError):
        return jsonify({"error": "잘못된 파라미터"}), 400
    user_id = current_user["_id"]
    first_day = datetime.date(year, month, 1)
    if month == 12:
        next_month_first_day = datetime.date(year+1, 1, 1)
    else:
        next_month_first_day = datetime.date(year, month+1, 1)
    last_day = next_month_first_day - datetime.timedelta(days=1)
    today = datetime.date.today()
    month_str = f"{year:04d}-{month:02d}-"
    exercise_docs = exercises_collection.find({
        "user_id": user_id,
        "date": {"$regex": f"^{month_str}"}
    })
    day_to_records = {}
    for doc in exercise_docs:
        d = doc["date"]
        day_to_records.setdefault(d, []).append(doc)
    total_days = 0
    attended_days = 0
    for day in range(1, last_day.day+1):
        current_day = datetime.date(year, month, day)
        if current_day > today:
            continue
        total_days += 1
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        records = day_to_records.get(date_str, [])
        if records and all(rec.get("checked", False) for rec in records):
            attended_days += 1
    absent_days = total_days - attended_days
    return jsonify({"present": attended_days, "absent": absent_days})

# API: 이번달 웍스아웃 – 운동별 기록 빈도 (상위 5개)
@app.route("/api/workout_stats", methods=["GET"])
def api_workout_stats():
    current_user = get_current_user()
    if not current_user:
        return jsonify({}), 401
    try:
        year = int(request.args.get("year"))
        month = int(request.args.get("month"))
    except (TypeError, ValueError):
        return jsonify({"error": "잘못된 파라미터"}), 400
    user_id = current_user["_id"]
    month_str = f"{year:04d}-{month:02d}-"
    cursor = exercises_collection.find({
        "user_id": user_id,
        "date": {"$regex": f"^{month_str}"}
    })
    counts = {}
    for doc in cursor:
        exercise = doc.get("exercise", "기타")
        counts[exercise] = counts.get(exercise, 0) + 1
    sorted_items = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:5]
    labels = [item[0] for item in sorted_items]
    data = [item[1] for item in sorted_items]
    return jsonify({"labels": labels, "data": data})

# 다이어리 페이지 – 날짜별 운동 기록
@app.route("/diary/<date_str>", methods=["GET"])
def diary_page(date_str):
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))
    user_id = current_user["_id"]
    diary_exercises = exercises_collection.find({
        "user_id": user_id,
        "date": date_str
    })
    exercise_list = []
    for e in diary_exercises:
        exercise_list.append({
            "_id": str(e["_id"]),
            "exercise": e.get("exercise", ""),
            "weight": e.get("weight", 0),
            "reps": e.get("reps", 0),
            "sets": e.get("sets", 0),
            "checked": e.get("checked", False)
        })
    return render_template("diary/diary.html", nickname=current_user["nickname"], diary_date=date_str, exercises=exercise_list)

# 다이어리 – 운동 기록 추가
@app.route("/diary/<date_str>/add", methods=["POST"])
def add_exercise(date_str):
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))
    user_id = current_user["_id"]
    exercise_name = request.form.get("exercise_name")
    weight = int(request.form.get("weight", 0))
    reps = int(request.form.get("reps", 0))
    sets = int(request.form.get("sets", 0))
    new_ex = {
        "user_id": user_id,
        "date": date_str,
        "exercise": exercise_name,
        "weight": weight,
        "reps": reps,
        "sets": sets,
        "checked": False
    }
    exercises_collection.insert_one(new_ex)
    return redirect(url_for("diary_page", date_str=date_str))

# 다이어리 – 운동 기록 삭제
@app.route("/diary/<date_str>/delete/<exercise_id>", methods=["POST"])
def delete_exercise(date_str, exercise_id):
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))
    user_id = current_user["_id"]
    exercises_collection.delete_one({
        "_id": ObjectId(exercise_id),
        "user_id": user_id,
        "date": date_str
    })
    return redirect(url_for("diary_page", date_str=date_str))

# 다이어리 – 체크박스 토글
@app.route("/diary/<date_str>/check/<exercise_id>", methods=["POST"])
def toggle_exercise_check(date_str, exercise_id):
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))
    checked_value = request.form.get("checked")
    is_checked = (checked_value == "on")
    exercises_collection.update_one(
        {
            "_id": ObjectId(exercise_id),
            "user_id": current_user["_id"],
            "date": date_str
        },
        {"$set": {"checked": is_checked}}
    )
    return redirect(url_for("diary_page", date_str=date_str))

if __name__ == "__main__":
    app.run("0.0.0.0", port=5001, debug=True)
