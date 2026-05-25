from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Exercise, Appointment, Payment
from datetime import datetime, timedelta
import os
import random
import re

app = Flask(__name__)
# Используем абсолютный путь для БД, чтобы на облачном хостинге всё работало надежно
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'logoped.db')
app.config['SECRET_KEY'] = 'super-secret-key'
db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    # Современный метод запроса к БД (убирает предупреждения в консоли)
    return db.session.get(User, int(user_id))


def get_sound_from_name(name):
    """Извлекает точный звук из названия файла или папки"""
    clean_sounds = ['С', 'Сь', 'З', 'Зь', 'Ш', 'Ж', 'Л', 'Ль', 'Р', 'Рь']
    name_lower = name.lower()

    if 'ж' in name_lower or 'zh' in name_lower:
        return 'Ж'

    # Разбиваем строку на отдельные слова, игнорируя спецсимволы
    parts = re.split(r'[^а-яА-ЯёЁa-zA-Z]+', name)
    for part in parts:
        for s in clean_sounds:
            if part.lower() == s.lower():
                return s
    return None


def inject_mock_data():
    """Чистое наполнение базы контентом (без логов)"""
    if Exercise.query.count() == 0:
        clean_sounds = ['С', 'Сь', 'З', 'Зь', 'Ш', 'Ж', 'Л', 'Ль', 'Р', 'Рь']

        rutube_links = [
            'https://rutube.ru/play/embed/b183aa1c519cc5e769e6b7b3a5a6e0b5/',
            'https://rutube.ru/play/embed/464360/'
        ]
        for i, s in enumerate(clean_sounds):
            video_url = rutube_links[i % len(rutube_links)]
            db.session.add(Exercise(category='постановка', sound=s, content_url=video_url))

        img_dir = os.path.join(basedir, 'static', 'img')

        if os.path.exists(img_dir):
            answers_map = {}
            for filename in os.listdir(img_dir):
                fn_lower = filename.lower()
                if ('answer' in fn_lower or 'ответ' in fn_lower) and not os.path.isdir(os.path.join(img_dir, filename)):
                    matched_ans_sound = get_sound_from_name(filename)
                    if matched_ans_sound:
                        answers_map[matched_ans_sound] = f'/static/img/{filename}'

            for folder_name in os.listdir(img_dir):
                folder_path = os.path.join(img_dir, folder_name)
                if os.path.isdir(folder_path):
                    matched_sound = get_sound_from_name(folder_name)

                    if matched_sound:
                        for filename in os.listdir(folder_path):
                            file_path = os.path.join(folder_path, filename)
                            if not os.path.isdir(file_path) and filename.lower().endswith(
                                    ('.png', '.jpg', '.jpeg', '.webp', '.pdf')):
                                img_url = f'/static/img/{folder_name}/{filename}'
                                ans_url = answers_map.get(matched_sound)
                                db.session.add(Exercise(
                                    category='автоматизация',
                                    sound=matched_sound,
                                    content_url=img_url,
                                    answer_url=ans_url
                                ))
        db.session.commit()


with app.app_context():
    db.create_all()
    inject_mock_data()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/learning')
@login_required
def learning():
    sounds = ['С', 'Сь', 'З', 'Зь', 'Ш', 'Ж', 'Л', 'Ль', 'Р', 'Рь']
    return render_template('learning.html', sounds=sounds)


@app.route('/exercise/<category>')
@login_required
def exercise(category):
    sound = request.args.get('sound')
    if not sound:
        flash('Пожалуйста, выберите звук', 'warning')
        return redirect(url_for('learning'))

    cat_name = 'постановка' if category == 'postanovka' else 'автоматизация'
    exercises = Exercise.query.filter_by(category=cat_name, sound=sound).all()
    ex = random.choice(exercises) if exercises else None

    return render_template('exercise.html', category=cat_name, sound=sound, exercise=ex)


@app.route('/test')
def logo_test():
    return render_template('test.html')


@app.route('/materials')
def materials():
    return render_template('materials.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Имя пользователя уже занято', 'danger')
            return redirect(url_for('register'))
        new_user = User(username=username, password_hash=generate_password_hash(password), role=role)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('dashboard'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Неверные данные', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'logoped':
        appointments = Appointment.query.all()
        total_income = sum(p.amount for p in Payment.query.all())
        return render_template('dashboard_logoped.html', appointments=appointments, income=total_income)
    else:
        my_appointments = Appointment.query.filter_by(user_id=current_user.id).all()
        return render_template('dashboard_parent.html', appointments=my_appointments)


@app.route('/pay/<int:appointment_id>')
@login_required
def simulate_payment(appointment_id):
    appt = db.session.get(Appointment, appointment_id)
    if not appt:
        flash('Запись не найдена', 'danger')
        return redirect(url_for('dashboard'))

    if appt.user_id != current_user.id:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('dashboard'))

    payment = Payment(user_id=current_user.id, amount=1500)
    appt.status = 'оплачено'
    db.session.add(payment)
    db.session.commit()
    flash('Оплата прошла успешно! Чек отправлен на почту.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/booking', methods=['GET', 'POST'])
@login_required
def booking():
    if request.method == 'POST':
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        new_appt = Appointment(user_id=current_user.id, date_time=dt)
        db.session.add(new_appt)
        db.session.commit()
        flash('Вы успешно записались! Пожалуйста, оплатите занятие в личном кабинете.', 'success')
        return redirect(url_for('dashboard'))
    time_slots = [(datetime.strptime('10:00', '%H:%M') + timedelta(minutes=30 * i)).strftime('%H:%M') for i in
                  range(11)]
    return render_template('booking.html', time_slots=time_slots)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)