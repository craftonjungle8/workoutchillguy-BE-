from flask import Flask, request, jsonify, render_template
from flask_pymongo import PyMongo
import jwt
import datetime
import bcrypt
from functools import wraps
from bson import ObjectId

app = Flask(__name__)

# 🔹 환경 변수 설정 (SECRET_KEY 및 MongoDB 연결)
app.config["SECRET_KEY"] = "your_secret_key"
app.config["MONGO_URI"] = "mongodb://localhost:27017/1weekmini"

mongo = PyMongo(app)
users_collection = mongo.db.users
boards_collection = mongo.db.boards

# -------------------------------------
# JWT 인증 데코레이터
# -------------------------------------
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

# -------------------------------------
# HTML 페이지 라우팅
# -------------------------------------
@app.route("/")
def home():
    # 예: 로그인 페이지
    return render_template("login/login.html")

@app.route("/signup", methods=["GET"])
def signup_page():
    # 예: 회원가입 페이지
    return render_template("signup/signup.html")

@app.route("/boardlist", methods=["GET"])
@token_required
def board_list_page(current_user):
    # 게시글 리스트 페이지(프론트) 불러오기
    return render_template("board_list.html")

# -------------------------------------
# 회원가입 API
# -------------------------------------
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    nickname = data.get("nickname")
    email = data.get("email")
    password = data.get("password")

    if users_collection.find_one({"email": email}):
        return jsonify({"success": False, "message": "이미 가입된 이메일입니다."}), 400

    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    user_id = users_collection.insert_one({
        "nickname": nickname,
        "email": email,
        "password": hashed_pw,
    }).inserted_id

    return jsonify({"success": True, "message": "회원가입 성공!", "user_id": str(user_id)}), 201

# -------------------------------------
# 로그인 API (JWT 발급)
# -------------------------------------
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

    # 토큰 생성
    token = jwt.encode(
        {
            "user_id": str(user["_id"]),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        },
        app.config["SECRET_KEY"],
        algorithm="HS256"
    )

    return jsonify({"success": True, "token": token})

# -------------------------------------
# 사용자 정보 조회 API
#  - 닉네임 등을 프론트에서 쉽게 사용 가능
# -------------------------------------
@app.route("/user-info", methods=["GET"])
@token_required
def user_info(current_user):
    return jsonify({"nickname": current_user["nickname"]})

# -------------------------------------
# 게시글 작성 API (JWT 인증 필요)
# -------------------------------------
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

# -------------------------------------
# (1) 사용자 본인의 모든 게시글 조회 API
# -------------------------------------
@app.route("/board", methods=["GET"])
@token_required
def get_boards(current_user):
    """
    - 현재 로그인한 사용자 본인의 게시글 전부 조회
    - 실제로는 "내" 게시글만 보이도록 설계되었지만,
      프로젝트에 따라 전체 게시글을 조회하고 싶다면
      boards_collection.find() 등으로 수정
    """
    user_boards = boards_collection.find({"user_id": current_user["_id"]}).sort("created_at", -1)
    result = []
    for board in user_boards:
        result.append({
            "id": str(board["_id"]),
            "title": board["title"],
            "content": board["content"],
            "created_at": board["created_at"].strftime("%Y-%m-%d %H:%M:%S")
        })

    return jsonify(result)

# -------------------------------------
# (2) 게시글 상세 조회 API
# -------------------------------------
@app.route("/board/<board_id>", methods=["GET"])
@token_required
def get_board_detail(current_user, board_id):
    """
    - 게시글 상세 조회
    - '내' 게시글만 볼 수 있게 하려면 "user_id" 조건을 추가,
      전체 공개라면 조건 제거
    """
    board = boards_collection.find_one({"_id": ObjectId(board_id)})
    if not board:
        return jsonify({"message": "게시글이 존재하지 않습니다."}), 404

    # 권한 체크 (내 게시글만 확인 가능하게 하려면 주석 해제)
    # if board["user_id"] != current_user["_id"]:
    #     return jsonify({"message": "접근 권한이 없습니다."}), 403

    return jsonify({
        "id": str(board["_id"]),
        "title": board["title"],
        "content": board["content"],
        "created_at": board["created_at"].strftime("%Y-%m-%d %H:%M:%S")
    })

# -------------------------------------
# 대시보드 (JWT 인증 필요)
# -------------------------------------
@app.route("/dashboard", methods=["GET"])
@token_required
def dashboard(current_user):
    return jsonify({"message": f"환영합니다, {current_user['nickname']}님!"})

# -------------------------------------
# Flask 앱 실행
# -------------------------------------
if __name__ == '__main__':
    app.run('0.0.0.0', port=5001, debug=True)
