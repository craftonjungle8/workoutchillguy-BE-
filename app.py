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

# ----------------------------------------
# JWT 쿠키 검증을 위한 헬퍼 함수
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

    # 회원가입 완료 후 → 로그인 페이지로 리다이렉트
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
# 마이페이지 (get)
# -------------------------
@app.route("/mypage", methods=["GET"])  
def mypage():
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))

    # 닉네임
    nickname = current_user.get("nickname", "")

    # 마이페이지 내가쓴 글 조회 현재 UI 미구현
    # 내가 쓴 글 목록 (boards_collection에서 user_id = current_user["_id"] 인 것들 찾기)
    posts_cursor = boards_collection.find({"user_id": current_user["_id"]}).sort("created_at", -1)
    my_posts = []
    for p in posts_cursor:
        my_posts.append({
            "id": str(p["_id"]),
            "title": p["title"],
            "content": p["content"],
            "created_at": p["created_at"].strftime("%Y-%m-%d %H:%M") if "created_at" in p else ""
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

    # 수정 후 다시 마이페이지로
    return redirect(url_for("mypage"))

# -------------------------
# 메인페이지 (GET)
# -------------------------
@app.route("/mainpage", methods=["GET"])
def mainpage():
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))

    # jinja2 템플릿 렌더링
    # mainpage.html 안에서 {{ nickname }}, {{ email }} 사용 가능
    return render_template(
        "mainpage/mainpage.html",
        nickname=current_user.get("nickname", ""),
        email=current_user["email"]
    )

# -------------------------
# 게시판 목록 페이지 (GET)
# -------------------------
@app.route("/board", methods=["GET"])
def board_list():
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))

    # DB에서 게시글 목록 조회 (최신순 정렬)
    all_posts = boards_collection.find().sort("created_at", -1)
    post_list = []
    for post in all_posts:
        post_list.append({
            "id": str(post["_id"]),
            "title": post["title"],
            "content": post["content"],
            "created_at": post.get("created_at", "").strftime("%Y-%m-%d %H:%M")
                          if "created_at" in post else ""
        })

    return render_template(
        "board/board.html",
        nickname=current_user.get("nickname", ""),
        email=current_user["email"],
        posts=post_list
    )

# -------------------------
# 특정 게시글 상세 페이지 (GET)
# -------------------------
@app.route("/board/<post_id>", methods=["GET"])
def board_detail(post_id):
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))

    post_doc = boards_collection.find_one({"_id": ObjectId(post_id)})
    if not post_doc:
        # 없는 게시글이면 /board 로 이동
        return redirect(url_for("board_list"))

    post_data = {
        "id": str(post_doc["_id"]),
        "title": post_doc["title"],
        "content": post_doc["content"],
        "created_at": post_doc.get("created_at", "").strftime("%Y-%m-%d %H:%M")
                      if "created_at" in post_doc else "",
    }

    return render_template(
        "board/posting.html",
        nickname=current_user.get("nickname", ""),
        email=current_user["email"],
        post=post_data
    )

# ---------------------------------
# 글 작성 폼 페이지 (GET)
# ---------------------------------
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

# ---------------------------------
# 글 작성 처리 (POST)
# ---------------------------------
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

    # 글 작성 완료 → 게시판 목록 페이지로 이동
    return redirect(url_for("board_list"))

# -------------------------
# 로그아웃 (쿠키 제거)
# -------------------------
@app.route("/logout", methods=["GET"])
def logout():
    resp = make_response(redirect(url_for("login_page")))
    resp.set_cookie("jwt_token", "", expires=0)
    return resp

# ---------------------------------
# (Diary) 날짜별 운동일기 페이지 (GET)
# 예: /diary/2025-03-10
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

    # jinja2에 넘길 리스트 변환
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

    # diary.html 템플릿 렌더
    return render_template(
        "diary/diary.html",
        nickname=current_user["nickname"],
        diary_date=date_str,
        exercises=exercise_list
    )

# ---------------------------------
# (Diary) 운동 기록 추가 (POST)
# /diary/<date_str>/add
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
        "checked": False
    }
    exercises_collection.insert_one(new_ex)

    # 추가 후 같은 날짜 diary 페이지로
    return redirect(url_for("diary_page", date_str=date_str))

# ---------------------------------
# (Diary) 운동 기록 삭제 (POST)
# /diary/<date_str>/delete/<exercise_id>
# ---------------------------------
@app.route("/diary/<date_str>/delete/<exercise_id>", methods=["POST"])
def delete_exercise(date_str, exercise_id):
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login_page"))

    user_id = current_user["_id"]

    # DB에서 해당 문서 삭제
    exercises_collection.delete_one({
        "_id": ObjectId(exercise_id),
        "user_id": user_id,
        "date": date_str
    })

    return redirect(url_for("diary_page", date_str=date_str))

# ---------------------------------
# Flask 실행
# ---------------------------------
if __name__ == "__main__":
    app.run("0.0.0.0", port=5001, debug=True)
