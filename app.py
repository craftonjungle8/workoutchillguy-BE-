from flask import Flask, request, jsonify, render_template
from flask_pymongo import PyMongo
import jwt
import datetime
import bcrypt
from functools import wraps
from bson import ObjectId

app = Flask(__name__)

# 환경 변수 설정 (SECRET_KEY 및 MongoDB 연결)
app.config["SECRET_KEY"] = "your_secret_key"
app.config["MONGO_URI"] = "mongodb://localhost:27017/1weekmini"

mongo = PyMongo(app)
users_collection = mongo.db.users
boards_collection = mongo.db.boards

# 루트 경로 -> templates/login/login.html 렌더링
@app.route("/")
def home():
    return render_template("login/login.html")

# ===================================
# JWT 토큰 검증 데코레이터
# ===================================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("x-access-token")
        if not token:
            return jsonify({"message": "토큰이 없습니다!"}), 401

        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            current_user = users_collection.find_one({"_id": ObjectId(data["user_id"])})
            if not current_user:
                return jsonify({"message": "유효하지 않은 사용자입니다!"}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "토큰이 만료되었습니다!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "유효하지 않은 토큰입니다!"}), 401

        return f(current_user, *args, **kwargs)
    return decorated

# ===================================
# 회원가입 페이지 렌더링 (GET)
# ===================================
@app.route("/signup", methods=["GET"])
def signup_page():
    return render_template("signup/signup.html")  # 회원가입 페이지 (예: templates/signup/signup.html)

# ===================================
# 회원가입 API (POST)
# ===================================
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    nickname = data.get("nickname")
    email = data.get("email")
    password = data.get("password")

    # 이미 가입된 이메일 확인
    if users_collection.find_one({"email": email}):
        return jsonify({"success": False, "message": "이미 가입된 이메일입니다."}), 400

    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    user_id = users_collection.insert_one({
        "nickname": nickname,
        "email": email,
        "password": hashed_pw,
    }).inserted_id

    return jsonify({"success": True, "message": "회원가입 성공!", "user_id": str(user_id)}), 201

# ===================================
# 로그인 API (JWT 발급)
# ===================================
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = users_collection.find_one({"email": email})
    if not user:
        return jsonify({"success": False, "message": "이메일 또는 비밀번호가 잘못되었습니다."}), 401

    if not bcrypt.checkpw(password.encode("utf-8"), user["password"]):
        return jsonify({"success": False, "message": "이메일 또는 비밀번호가 잘못되었습니다."}), 401

    # JWT 토큰 발급 (유효기간 1시간)
    token = jwt.encode(
        {
            "user_id": str(user["_id"]),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        },
        app.config["SECRET_KEY"],
        algorithm="HS256"
    )

    # 로그인 성공 시 mainpage로 이동하도록 설정
    return jsonify({
        "success": True,
        "token": token,
        "redirect": "/mainpage"
    }), 200

# ===================================
# 게시글 작성 API (JWT 인증 필요)
# ===================================
@app.route("/board", methods=["POST"])
@token_required
def create_board(current_user):
    data = request.json
    board_id = boards_collection.insert_one({
        "title": data["title"],
        "content": data["content"],
        "user_id": current_user["_id"],
        "created_at": datetime.datetime.utcnow()
    }).inserted_id

    return jsonify({"message": "게시글 등록 완료", "board_id": str(board_id)})

# ===================================
# 사용자 게시글 조회 API (JWT 인증 필요)
# ===================================
@app.route("/board", methods=["GET"])
@token_required
def get_boards(current_user):
    user_boards = boards_collection.find({"user_id": current_user["_id"]})
    result = [{"title": board["title"], "content": board["content"]} for board in user_boards]
    return jsonify(result)

# ===================================
# mainpage (로그인한 유저만 접근 가능)
# ===================================
@app.route("/mainpage", methods=["GET"])
@token_required
def mainpage(current_user):
    # 토큰이 유효하면 mainpage.html 렌더링
    # 필요하다면 current_user['nickname'] 등 정보를 템플릿에 넘길 수 있음
    return render_template("mainpage/mainpage.html")

# ===================================
# 서버 실행
# ===================================
if __name__ == '__main__':
    app.run('0.0.0.0', port=5001, debug=True)
