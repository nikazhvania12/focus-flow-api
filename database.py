from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

def create_default_user():
    # Check if default user exists
    default_user = User.query.filter_by(username="default_user").first()
    if not default_user:
        default_user = User(
            username="default_user",
            email="default@example.com",
            password="default_password"  # In real app, this should be properly hashed
        )
        db.session.add(default_user)
        db.session.commit()

def focus_flow_db(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///focus_flow.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        create_default_user()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    tasks = db.relationship('Task', backref='user', lazy=True)

class Priority(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    filepath = db.Column(db.String(200))
    tasks = db.relationship('Task', backref='priority', lazy=True)

class Difficulty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    tasks = db.relationship('Task', backref='difficulty', lazy=True)

class Status(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    tasks = db.relationship('Task', backref='status', lazy=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deadline = db.Column(db.DateTime, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Foreign keys
    priority_id = db.Column(db.Integer, db.ForeignKey('priority.id'), nullable=False)
    difficulty_id = db.Column(db.Integer, db.ForeignKey('difficulty.id'), nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('status.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) 