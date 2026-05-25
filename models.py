from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'logoped', 'parent'

    appointments = db.relationship('Appointment', backref='client', lazy=True)
    payments = db.relationship('Payment', backref='payer', lazy=True)

class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50)) # 'постановка' или 'автоматизация'
    sound = db.Column(db.String(10))    # Чистый звук: 'С', 'Сь', 'Р'
    content_url = db.Column(db.String(200))
    answer_url = db.Column(db.String(200), nullable=True) # Ссылка на скриншот ответа

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='ожидает оплаты')

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='успешно')
    date = db.Column(db.DateTime, default=datetime.utcnow)