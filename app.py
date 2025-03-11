from flask import Flask, request, jsonify, send_from_directory
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os

app = Flask(__name__)

# MongoDB 연결
client = MongoClient("mongodb://localhost:27017/")
db = client["mydatabase"]
collection = db["articles"]

# ObjectId를 문자열로 변환하는 함수
def serialize_document(doc):
    doc["_id"] = str(doc["_id"])
    if "created_at" in doc and isinstance(doc["created_at"], datetime):
        doc["created_at"] = doc["created_at"].strftime("%Y-%m-%d %H:%M:%S")

    if "comments" in doc:
        for comment in doc["comments"]:
            comment["_id"] = str(comment["_id"])
            if "created_at" in comment and isinstance(comment["created_at"], datetime):
                comment["created_at"] = comment["created_at"].strftime("%Y-%m-%d %H:%M:%S")
    return doc

# (1) 게시글 생성 (Create)
@app.route("/api/articles", methods=["POST"])
def create_article():
    data = request.json
    if "title" not in data or "content" not in data:
        return jsonify({"error": "제목과 내용을 입력하세요"}), 400

    new_article = {
        "title": data["title"],
        "content": data["content"],
        "comments": [],
        "created_at": datetime.now()  # 생성 시간 기록
    }
    result = collection.insert_one(new_article)
    return jsonify({"message": "게시글이 작성되었습니다", "id": str(result.inserted_id)}), 201

# (2) 게시글 목록 조회 (Read - 다건)
@app.route("/api/articles", methods=["GET"])
def get_articles():
    articles = list(collection.find().sort("created_at", -1))  # 최신순 정렬 예시
    return jsonify([serialize_document(article) for article in articles])

# (3) 게시글 상세 조회 (Read - 단건)
@app.route("/api/articles/<id>", methods=["GET"])
def get_article(id):
    article = collection.find_one({"_id": ObjectId(id)})
    if article:
        return jsonify(serialize_document(article))
    return jsonify({"error": "게시글을 찾을 수 없습니다"}), 404

# (4) 게시글 수정 (Update)
@app.route("/api/articles/<id>", methods=["PUT"])
def update_article(id):
    data = request.json
    update_data = {}

    if "title" in data:
        update_data["title"] = data["title"]
    if "content" in data:
        update_data["content"] = data["content"]

    result = collection.update_one({"_id": ObjectId(id)}, {"$set": update_data})

    if result.matched_count:
        return jsonify({"message": "게시글이 수정되었습니다"})
    return jsonify({"error": "게시글을 찾을 수 없습니다"}), 404

# (5) 게시글 삭제 (Delete)
@app.route("/api/articles/<id>", methods=["DELETE"])
def delete_article(id):
    result = collection.delete_one({"_id": ObjectId(id)})
    if result.deleted_count:
        return jsonify({"message": "게시글이 삭제되었습니다"})
    return jsonify({"error": "게시글을 찾을 수 없습니다"}), 404

# (6) 댓글 추가 (Create)
@app.route("/api/articles/<id>/comments", methods=["POST"])
def add_comment(id):
    data = request.json
    if "nickname" not in data or "content" not in data:
        return jsonify({"error": "닉네임과 댓글 내용을 입력하세요"}), 400

    comment = {
        "_id": ObjectId(),   # 각 댓글에 대한 고유 ID
        "nickname": data["nickname"],
        "content": data["content"],
        "created_at": datetime.now()
    }
    result = collection.update_one({"_id": ObjectId(id)}, {"$push": {"comments": comment}})
    
    if result.matched_count:
        return jsonify({"message": "댓글이 추가되었습니다", "comment_id": str(comment["_id"])})
    return jsonify({"error": "게시글을 찾을 수 없습니다"}), 404

# (7) 댓글 조회 (Read)
@app.route("/api/articles/<id>/comments", methods=["GET"])
def get_comments(id):
    article = collection.find_one({"_id": ObjectId(id)})
    if article:
        # article["comments"]가 없을 경우 빈 리스트
        comments = article.get("comments", [])
        # 날짜 문자열 변환
        for c in comments:
            c["_id"] = str(c["_id"])
            if "created_at" in c and isinstance(c["created_at"], datetime):
                c["created_at"] = c["created_at"].strftime("%Y-%m-%d %H:%M:%S")
        return jsonify(comments)
    return jsonify({"error": "게시글을 찾을 수 없습니다"}), 404

# (8) 댓글 수정 (Update)
@app.route("/api/articles/<article_id>/comments/<comment_id>", methods=["PUT"])
def update_comment(article_id, comment_id):
    data = request.json
    update_data = {}

    if "content" in data:
        update_data["comments.$.content"] = data["content"]
    
    result = collection.update_one(
        {"_id": ObjectId(article_id), "comments._id": ObjectId(comment_id)},
        {"$set": update_data}
    )

    if result.matched_count:
        return jsonify({"message": "댓글이 수정되었습니다"})
    return jsonify({"error": "댓글을 찾을 수 없습니다"}), 404

# (9) 댓글 삭제 (Delete)
@app.route("/api/articles/<article_id>/comments/<comment_id>", methods=["DELETE"])
def delete_comment(article_id, comment_id):
    result = collection.update_one(
        {"_id": ObjectId(article_id)},
        {"$pull": {"comments": {"_id": ObjectId(comment_id)}}}
    )
    
    if result.modified_count:
        return jsonify({"message": "댓글이 삭제되었습니다"})
    return jsonify({"error": "댓글을 찾을 수 없습니다"}), 404

# ------ 정적 파일 & 메인 페이지 라우팅 (예시) ------
@app.route("/")
def serve_root():
    # Flask가 index.html(아래 작성할 HTML)을 서빙하도록 구성
    return send_from_directory(os.path.join(app.root_path, "static"), "index.html")

# 만약 /mate-search 경로로 접속했을 때 동일 파일을 서빙하고 싶다면:
@app.route("/mate-search")
def serve_mate_search():
    return send_from_directory(os.path.join(app.root_path, "static"), "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
