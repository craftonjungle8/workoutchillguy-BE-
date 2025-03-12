from flask import Flask, request, render_template, redirect, url_for, make_response
from flask_pymongo import PyMongo
import bcrypt
import jwt
import datetime
from bson import ObjectId

app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key"  # 실제 환경에서는 안전하게 보관(.env 등)
app.config["MONGO_URI"] = "mongodb://localhost:27017/1weekmini"

mongo = PyMongo(app)
users_collection = mongo.db.users
boards_collection = mongo.db.boards      # 게시판 글
exercises_collection = mongo.db.exercises  # 운동일기

@app.route("/")
def home():
    current_user = get_current_user()
    if current_user:
        # 로그인된 경우 메인페이지로
        return redirect(url_for("mainpage"))
    else:
        # 로그인되지 않은 경우 로그인페이지로
        return redirect(url_for("login_page"))

# ----------------------------------------
# JWT 쿠키 검증 헬퍼 함수
# ----------------------------------------
def get_current_user():
    """JWT 쿠키('jwt_token')에서 사용자 정보 추출 & DB 조회."""
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

# -------------------------
# 회원가입 페이지 (GET)
# -------------------------
@app.route("/signup", methods=["GET"])
def signup_page():
    return render_template("signup/signup.html")

# -------------------------
# 회원가입 처리 (POST)
# -------------------------
@app.route("/signup", methods=["POST"])
def signup():
    nickname = request.form.get("nickname")
    email = request.form.get("email")
    password = request.form.get("password")

    # 이메일 중복 확인
    if users_collection.find_one({"email": email}):
        return render_template("signup/signup.html", error="이미 가입된 이메일입니다.")

    # 비밀번호 해싱
    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    # DB에 저장
    users_collection.insert_one({
        "nickname": nickname,
        "email": email,
        "password": hashed_pw
    })

    # 회원가입 완료 후 → 로그인 페이지로
    return redirect(url_for("login_page"))

# -------------------------
# 로그인 페이지 (GET)
# -------------------------
@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login/login.html")

# -------------------------
# 로그인 처리 (POST)
# -------------------------
@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    user = users_collection.find_one({"email": email})
    if not user:
        return render_template("login/login.html", error="이메일/비밀번호가 잘못되었습니다.")

    if not bcrypt.checkpw(password.encode("utf-8"), user["password"]):
        return render_template("login/login.html", error="이메일/비밀번호가 잘못되었습니다.")

    # JWT 생성 (1시간 유효)
    token = jwt.encode(
        {
            "user_id": str(user["_id"]),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        },
        app.config["SECRET_KEY"],
        algorithm="HS256"
    )

    # 쿠키에 JWT를 심어서 반환
    resp = make_response(redirect(url_for("mainpage")))
    resp.set_cookie("jwt_token", token, httponly=True, samesite="Strict")
    return resp

# -------------------------
# 로그아웃 (쿠키 제거)
# -------------------------
@app.route("/logout", methods=["GET"])
def logout():
    resp = make_response(redirect(url_for("login_page")))
    resp.set_cookie("jwt_token", "", expires=0)
    return resp

# -------------------------
# 마이페이지 (GET)
# -------------------------
@app.route("/mypage", methods=["GET"])  
def mypage():
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))

    # 닉네임
    nickname = current_user.get("nickname", "")

    # 내가 쓴 글 목록 (boards_collection에서 user_id = current_user["_id"] 인 것들)
    posts_cursor = boards_collection.find({"user_id": current_user["_id"]}).sort("created_at", -1)
    my_posts = []
    for p in posts_cursor:
        my_posts.append({
            "id": str(p["_id"]),
            "title": p["title"],
            "content": p["content"],
            "created_at": (p["created_at"] + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M") if "created_at" in p else ""
        })

    # 템플릿 렌더
    return render_template(
        "mypage/mypage.html",
        nickname=nickname,
        my_posts=my_posts
    )

@app.route("/mypage/update", methods=["POST"])
def update_mypage():
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))

    new_nickname = request.form.get("nickname")
    new_password = request.form.get("password")

    # 새 닉네임 업데이트
    update_fields = {"nickname": new_nickname}

    # 새 비밀번호가 입력되었으면 해싱 후 업데이트
    if new_password:
        hashed_pw = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
        update_fields["password"] = hashed_pw

    # DB 업데이트
    users_collection.update_one(
        {"_id": current_user["_id"]},
        {"$set": update_fields}
    )

    return redirect(url_for("mypage"))

# -------------------------
# 메인페이지 (GET) - 달력
# -------------------------
@app.route("/mainpage", methods=["GET"])
def mainpage():
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))

    nickname = current_user.get("nickname", "")
    email = current_user["email"]

    # 오늘 기준 연/월 계산
    now = datetime.datetime.now()
    year = now.year
    month = now.month

    # 이번 달 1일, 말일 구하기
    first_day = datetime.date(year, month, 1)
    if month == 12:
        next_month_first_day = datetime.date(year+1, 1, 1)
    else:
        next_month_first_day = datetime.date(year, month+1, 1)
    last_day = next_month_first_day - datetime.timedelta(days=1)

    # 이번 달 운동기록 조회
    user_id = current_user["_id"]
    month_str = f"{year:04d}-{month:02d}"  # 예: 2025-03
    exercise_docs = exercises_collection.find({
        "user_id": user_id,
        "date": {"$regex": f"^{month_str}"}
    })

    # 날짜별 운동기록 dict
    day_to_exercises = {}
    for doc in exercise_docs:
        d = doc["date"]  # ex) '2025-03-10'
        if d not in day_to_exercises:
            day_to_exercises[d] = []
        day_to_exercises[d].append(doc)

    # 달력 데이터
    calendar_data = []
    start_weekday = first_day.weekday()  # 월=0, 화=1, ... 일=6

    # (a) 첫 주의 공백
    for _ in range(start_weekday):
        calendar_data.append({
            "day": None,
            "date_str": "",
            "status": "no_records"  # 아무것도 안 출력
        })

    # (b) 1일부터 말일까지
    current_date = first_day
    while current_date <= last_day:
        iso_str = current_date.isoformat()  # 'YYYY-MM-DD'
        day_number = current_date.day
        ex_list = day_to_exercises.get(iso_str, [])

        if len(ex_list) == 0:
            # 기록 없음 => 흰색
            status = "no_records"
        else:
            # 하나라도 있으면 => 전부 checked == True 인지 확인
            all_checked = all(doc.get("checked", False) for doc in ex_list)
            if all_checked:
                # 모두 체크 => 초록
                status = "all_checked"
            else:
                # 일부나 전부 unchecked => 빨강
                status = "some_unchecked"

        calendar_data.append({
            "day": day_number,
            "date_str": iso_str,
            "status": status
        })

        current_date += datetime.timedelta(days=1)

    # 템플릿 렌더링
    return render_template(
        "mainpage/mainpage.html",
        nickname=nickname,
        email=email,
        year=year,
        month=month,
        calendar_data=calendar_data
    )

# -------------------------
# 게시판 목록 페이지 (GET) - 페이지 네이션 적용
# -------------------------
@app.route("/board", methods=["GET"])
def board_list():
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))

    # 페이지 번호와 한 페이지당 게시글 수 설정
    page = request.args.get("page", 1, type=int)
    per_page = 9

    total_posts = boards_collection.count_documents({})
    total_pages = (total_posts + per_page - 1) // per_page

    posts_cursor = boards_collection.find().sort("created_at", -1) \
                        .skip((page - 1) * per_page).limit(per_page)
    post_list = []
    for post in posts_cursor:
        created_at = ""
        if "created_at" in post:
            try:
                # Convert UTC datetime to KST (UTC+9)
                created_at = (post["created_at"] + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
            except Exception:
                created_at = str(post["created_at"])
        post_list.append({
            "id": str(post["_id"]),
            "title": post["title"],
            "content": post["content"],
            "created_at": created_at
        })

    return render_template(
        "board/board.html",
        nickname=current_user.get("nickname", ""),
        email=current_user["email"],
        posts=post_list,
        current_page=page,
        total_pages=total_pages
    )

# -------------------------
# 게시글 상세 (GET)
# -------------------------
@app.route("/board/<post_id>", methods=["GET"])
def board_detail(post_id):
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))

    post_doc = boards_collection.find_one({"_id": ObjectId(post_id)})
    if not post_doc:
        return redirect(url_for("board_list"))

    post_data = {
        "id": str(post_doc["_id"]),
        "title": post_doc["title"],
        "content": post_doc["content"],
        "created_at": (post_doc["created_at"] + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
                      if "created_at" in post_doc else ""
    }

    return render_template(
        "board/posting.html",
        nickname=current_user.get("nickname", ""),
        email=current_user["email"],
        post=post_data
    )

# -------------------------
# 글 작성 폼 페이지 (GET)
# -------------------------
@app.route("/board/new", methods=["GET"])
def new_post_page():
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))

    return render_template(
        "board/posting.html",
        nickname=current_user.get("nickname", ""),
        email=current_user["email"]
    )

# -------------------------
# 글 작성 처리 (POST)
# -------------------------
@app.route("/board/new", methods=["POST"])
def create_post():
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))

    title = request.form.get("title")
    content = request.form.get("content")

    new_post = {
        "title": title,
        "content": content,
        "created_at": datetime.datetime.utcnow(),
        "user_id": current_user["_id"]
    }
    boards_collection.insert_one(new_post)

    return redirect(url_for("board_list"))

# -------------------------
# 게시글 수정 페이지 (GET)
# -------------------------
@app.route("/board/<post_id>/edit", methods=["GET"])
def edit_post_page(post_id):
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))

    post_doc = boards_collection.find_one({"_id": ObjectId(post_id)})
    if not post_doc:
        return redirect(url_for("board_list"))

    # 작성자만 수정 가능
    if post_doc["user_id"] != current_user["_id"]:
        return redirect(url_for("board_list"))

    post_data = {
        "id": str(post_doc["_id"]),
        "title": post_doc["title"],
        "content": post_doc["content"]
    }

    return render_template(
        "board/edit_post.html",
        nickname=current_user.get("nickname", ""),
        email=current_user["email"],
        post=post_data
    )

# -------------------------
# 게시글 수정 처리 (POST)
# -------------------------
@app.route("/board/<post_id>/edit", methods=["POST"])
def edit_post(post_id):
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))

    post_doc = boards_collection.find_one({"_id": ObjectId(post_id)})
    if not post_doc:
        return redirect(url_for("board_list"))

    # 작성자만 수정 가능
    if post_doc["user_id"] != current_user["_id"]:
        return redirect(url_for("board_list"))

    new_title = request.form.get("title")
    new_content = request.form.get("content")

    boards_collection.update_one(
        {"_id": ObjectId(post_id)},
        {"$set": {
            "title": new_title,
            "content": new_content
        }}
    )

    return redirect(url_for("board_detail", post_id=post_id))

# -------------------------
# 게시글 삭제 (POST)
# -------------------------
@app.route("/board/<post_id>/delete", methods=["POST"])
def delete_post(post_id):
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))

    post_doc = boards_collection.find_one({"_id": ObjectId(post_id)})
    if not post_doc:
        return redirect(url_for("board_list"))

    # 작성자만 삭제 가능
    if post_doc["user_id"] != current_user["_id"]:
        return redirect(url_for("board_list"))

    boards_collection.delete_one({"_id": ObjectId(post_id)})

    return redirect(url_for("board_list"))

# ---------------------------------
# (Diary) 날짜별 운동일기 페이지 (GET)
# ---------------------------------
@app.route("/diary/<date_str>", methods=["GET"])
def diary_page(date_str):
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))

    # DB에서 (user_id + 날짜)로 운동기록 검색
    user_id = current_user["_id"]
    diary_exercises = exercises_collection.find({
        "user_id": user_id,
        "date": date_str
    })

    # 오늘 날짜와 비교해서 과거인지 확인
    diary_date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    today = datetime.date.today()
    is_past = (diary_date_obj < today)

    # jinja2에 넘길 리스트
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

    return render_template(
        "diary/diary.html",
        nickname=current_user["nickname"],
        diary_date=date_str,
        exercises=exercise_list,
        is_past=is_past
    )

# ---------------------------------
# (Diary) 운동 기록 추가 (POST)
# ---------------------------------
@app.route("/diary/<date_str>/add", methods=["POST"])
def add_exercise(date_str):
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))

    user_id = current_user["_id"]

    # 폼 데이터
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
        "checked": False  # 새로 추가 시 기본 False
    }
    exercises_collection.insert_one(new_ex)

    return redirect(url_for("diary_page", date_str=date_str))

# ---------------------------------
# (Diary) 운동기록 삭제 (POST)
# ---------------------------------
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

# ---------------------------------
# (Diary) 체크박스 토글 (POST)
# ---------------------------------
@app.route("/diary/<date_str>/check/<exercise_id>", methods=["POST"])
def toggle_exercise_check(date_str, exercise_id):
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))

    # 과거 날짜라면 업데이트 불가
    diary_date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    if diary_date_obj < datetime.date.today():
        # 그냥 리다이렉트
        return redirect(url_for("diary_page", date_str=date_str))

    # form에서 체크 여부
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

# ---------------------------------
# Flask 실행
# ---------------------------------
if __name__ == "__main__":
    app.run("0.0.0.0", port=5001, debug=True)