from flask import Flask, request, render_template, redirect, url_for, make_response
from flask_pymongo import PyMongo
import bcrypt
import jwt
import datetime
from bson import ObjectId

app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key"          # 실제 환경에서는 안전하게 보관
app.config["MONGO_URI"] = "mongodb://localhost:27017/1weekmini"

mongo = PyMongo(app)
users_collection = mongo.db.users
boards_collection = mongo.db.boards  # 게시글 저장용 컬렉션

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
# 메인페이지 (GET)
# -------------------------
@app.route("/mainpage", methods=["GET"])
def mainpage():
    token = request.cookies.get("jwt_token")
    if not token:
        # 토큰이 없으면 로그인 페이지로
        return redirect(url_for("login_page"))

    try:
        data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        user_id = data["user_id"]
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return redirect(url_for("login_page"))

    # DB에서 사용자 정보 가져오기
    current_user = users_collection.find_one({"_id": ObjectId(user_id)})
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
    token = request.cookies.get("jwt_token")
    if not token:
        return redirect(url_for("login_page"))

    try:
        data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        user_id = data["user_id"]
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return redirect(url_for("login_page"))

    current_user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not current_user:
        return redirect(url_for("login_page"))

    # DB에서 게시글 목록 조회 (최신순 정렬 예시)
    all_posts = boards_collection.find().sort("created_at", -1)
    post_list = []
    for post in all_posts:
        post_list.append({
            "id": str(post["_id"]),
            "title": post["title"],
            "content": post["content"],
            "created_at": post["created_at"].strftime("%Y-%m-%d %H:%M") if "created_at" in post else ""
        })

    # board/board.html 템플릿에 posts 전달
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
    token = request.cookies.get("jwt_token")
    if not token:
        return redirect(url_for("login_page"))

    try:
        data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        user_id = data["user_id"]
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return redirect(url_for("login_page"))

    current_user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not current_user:
        return redirect(url_for("login_page"))

    # DB에서 해당 게시글 찾기
    post_doc = boards_collection.find_one({"_id": ObjectId(post_id)})
    if not post_doc:
        # 없는 게시글이면 /board 로 이동
        return redirect(url_for("board_list"))

    # jinja2에 넘길 데이터 구성
    post_data = {
        "id": str(post_doc["_id"]),
        "title": post_doc["title"],
        "content": post_doc["content"],
        "created_at": post_doc["created_at"].strftime("%Y-%m-%d %H:%M") if "created_at" in post_doc else "",
    }

    # board/posting.html 템플릿에 post 전달
    return render_template(
        "board/posting.html",
        nickname=current_user.get("nickname", ""),
        email=current_user["email"],
        post=post_data
    )

# -------------------------
# 로그아웃 (쿠키 제거)
# -------------------------
@app.route("/logout", methods=["GET"])
def logout():
    resp = make_response(redirect(url_for("login_page")))
    resp.set_cookie("jwt_token", "", expires=0)
    return resp

# ---------------------------------
# 글 작성 폼 페이지 (GET)
# ---------------------------------
@app.route("/board/new", methods=["GET"])
def new_post_page():
    # JWT 쿠키 확인 (로그인 여부)
    token = request.cookies.get("jwt_token")
    if not token:
        return redirect(url_for("login_page"))

    try:
        data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        user_id = data["user_id"]
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return redirect(url_for("login_page"))

    current_user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not current_user:
        return redirect(url_for("login_page"))

    # jinja2 템플릿: posting.html 렌더
    # 필요하다면 nickname, email 넘길 수도 있음
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
    token = request.cookies.get("jwt_token")
    if not token:
        return redirect(url_for("login_page"))

    try:
        data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        user_id = data["user_id"]
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return redirect(url_for("login_page"))

    current_user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not current_user:
        return redirect(url_for("login_page"))

    # 폼 데이터 받기
    title = request.form.get("title")
    content = request.form.get("content")

    # DB에 새 게시글 저장
    new_post = {
        "title": title,
        "content": content,
        "created_at": datetime.datetime.utcnow(),
        "user_id": current_user["_id"]
    }
    boards_collection.insert_one(new_post)

    # 글 작성 완료 → 게시판 목록 페이지로 이동
    return redirect(url_for("board_list"))

if __name__ == "__main__":
    app.run("0.0.0.0", port=5001, debug=True)
