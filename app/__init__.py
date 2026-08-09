from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sanqi-inventory-secret-key-2024')
    
    # 数据库配置：Vercel 用 PostgreSQL，本地用 SQLite
    database_url = os.environ.get('POSTGRES_URL')
    
    if database_url:
        # Vercel PostgreSQL（免费 256MB，永久保存）
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    elif os.environ.get('VERCEL'):
        # Vercel 环境但没有 PostgreSQL：用内存 SQLite（临时，重启数据丢失）
        # 提醒：后续需要在 Vercel 后台创建 PostgreSQL 数据库
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    else:
        # 本地开发用 SQLite
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'check_same_thread': False} if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI'] else {}
    }

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    # Import models so tables are registered before create_all
    from . import models  # noqa
    from .routes import init_routes

    with app.app_context():
        db.create_all()
        # Seed initial admin user
        from .models import User
        if not User.query.filter_by(username='sanqi').first():
            admin = User(username='sanqi', name='sanqi')
            admin.set_password('888999')
            db.session.add(admin)
            db.session.commit()

    init_routes(app)

    return app