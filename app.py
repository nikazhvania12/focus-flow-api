from flask import jsonify, Flask, request, send_from_directory, session
from flask_cors import CORS
from database import focus_flow_db, db, User, Task, Priority, Difficulty, Status
from datetime import datetime
from sqlalchemy import orm
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'e9b1b2c77c3cf993c4e7b6f3e93984a55dd8024b9ef37b15c479789b98d5029a'


CORS(app, 
     origins=["http://localhost:3000", "http://127.0.0.1:3000"],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     expose_headers=["Content-Type", "Authorization"],
     max_age=3600,
     send_wildcard=False)

RESOURCES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Resources')
if not os.path.exists(RESOURCES_FOLDER):
    os.makedirs(RESOURCES_FOLDER)

focus_flow_db(app)

def validate_required_fields(data, fields):
    for field in fields:
        if not data.get(field):
            return False, f"Missing required field: {field}"
    return True, None

@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()
        
        is_valid, error = validate_required_fields(data, ["username", "email", "password"])
        if not is_valid:
            return jsonify({"error": error}), 400
        
        if User.query.filter_by(email=data["email"]).first():
            return jsonify({"error": "Email already registered"}), 400
        if User.query.filter_by(username=data["username"]).first():
            return jsonify({"error": "Username already taken"}), 400
        
        new_user = User(
            username=data["username"],
            email=data["email"],
            password=generate_password_hash(data["password"])
        )
        
        db.session.add(new_user)
        db.session.commit()

        session["user_id"] = new_user.id
        
        return jsonify({
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        
        is_valid, error = validate_required_fields(data, ["email", "password"])
        if not is_valid:
            return jsonify({"error": error}), 400
        
        user = User.query.filter_by(email=data["email"]).first()
        if not user or not check_password_hash(user.password, data["password"]):
            return jsonify({"error": "Invalid email or password"}), 401
            
        session["user_id"] = user.id
        
        return jsonify({
            "id": user.id,
            "username": user.username,
            "email": user.email
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/currentuser", methods=["GET"])
def get_current_user():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({
            "id": user.id,
            "username": user.username,
            "email": user.email
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/logout", methods=["GET"])
def logout():
    try:
        session.pop("user_id", None)
        return jsonify({"message": "Logged out successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/tasks", methods=["GET"])
def get_tasks():
    try:
        priority_id = request.args.get('priority_id', type=int)
        difficulty_id = request.args.get('difficulty_id', type=int)
        val = request.args.get('val', type=str)
        user_id = request.args.get('user_id', type=int)
        
        query = Task.query.options(
            orm.joinedload(Task.priority),
            orm.joinedload(Task.difficulty),
            orm.joinedload(Task.status),
            orm.joinedload(Task.user)
        )
        
        if priority_id is not None and priority_id != 0:
            query = query.filter(Task.priority_id == priority_id)
        if difficulty_id is not None and difficulty_id != 0:
            query = query.filter(Task.difficulty_id == difficulty_id)
        if val is not None:
            query = query.filter(
                db.or_(
                    Task.title.like(f'%{val}%'),
                    Task.description.like(f'%{val}%')
                )
            )
        if user_id is not None and user_id != 0:
            query = query.filter(Task.user_id == user_id)
        
        tasks = query.all()
        
        return jsonify([{
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "deadline": task.deadline.strftime("%Y-%m-%d"),
            "priority": {
                "id": task.priority_id,
                "name": task.priority.name,
                "filepath": task.priority.filepath
            },
            "difficulty": {
                "id": task.difficulty_id,
                "name": task.difficulty.name
            },
            "status": {
                "id": task.status_id,
                "name": task.status.name
            },
            "user": {
                "id": task.user_id,
                "username": task.user.username
            }
        } for task in tasks]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/tasks", methods=["POST"])
def add_task():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401

        data = request.get_json()
        
        required_fields = ["title", "priority_id", "difficulty_id", "status_id", "deadline"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        new_task = Task(
            title=data["title"],
            description=data.get("description", ""),
            priority_id=data["priority_id"],
            difficulty_id=data["difficulty_id"],
            status_id=data["status_id"],
            user_id=user_id,
            deadline=datetime.fromisoformat(data["deadline"])
        )
        
        db.session.add(new_task)
        db.session.commit()
        
        return jsonify({
            "id": new_task.id,
            "title": new_task.title,
            "description": new_task.description,
            "deadline": new_task.deadline.strftime("%Y-%m-%d"),
            "priority": {
                "id": new_task.priority_id,
                "name": new_task.priority.name,
                "filepath": new_task.priority.filepath
            },
            "difficulty": {
                "id": new_task.difficulty_id,
                "name": new_task.difficulty.name
            },
            "status": {
                "id": new_task.status_id,
                "name": new_task.status.name
            },
            "user": {
                "id": new_task.user_id,
                "username": new_task.user.username
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401

        task = Task.query.get_or_404(task_id)
        
        # Check if the task belongs to the current user
        if task.user_id != user_id:
            return jsonify({"error": "Unauthorized"}), 403

        data = request.get_json()
        
        if "title" in data:
            task.title = data["title"]
        if "description" in data:
            task.description = data["description"]
        if "priority_id" in data:
            task.priority_id = data["priority_id"]
        if "difficulty_id" in data:
            task.difficulty_id = data["difficulty_id"]
        if "status_id" in data:
            task.status_id = data["status_id"]
        if "deadline" in data:
            task.deadline = datetime.fromisoformat(data["deadline"])
        
        db.session.commit()
        
        return jsonify({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "deadline": task.deadline.strftime("%Y-%m-%d"),
            "priority": {
                "id": task.priority_id,
                "name": task.priority.name,
                "filepath": task.priority.filepath
            },
            "difficulty": {
                "id": task.difficulty_id,
                "name": task.difficulty.name
            },
            "status": {
                "id": task.status_id,
                "name": task.status.name
            },
            "user": {
                "id": task.user_id,
                "username": task.user.username
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    try:
        task = Task.query.get_or_404(task_id)
        db.session.delete(task)
        db.session.commit()
        return "", 204
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/priorities", methods=["GET"])
def get_priorities():
    try:
        priorities = Priority.query.all()
        return jsonify([{
            "id": priority.id,
            "name": priority.name,
            "filepath": priority.filepath
        } for priority in priorities]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/difficulties", methods=["GET"])
def get_difficulties():
    try:
        difficulties = Difficulty.query.all()
        return jsonify([{
            "id": difficulty.id,
            "name": difficulty.name
        } for difficulty in difficulties]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/statuses", methods=["GET"])
def get_statuses():
    try:
        statuses = Status.query.all()
        return jsonify([{
            "id": status.id,
            "name": status.name
        } for status in statuses]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/Resources/<filename>", methods=["GET"])
def get_image(filename):
    try:
        return send_from_directory(RESOURCES_FOLDER, filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)