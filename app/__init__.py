from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'sanqi-inventory-secret-key-2024'
    # 数据库配置：Vercel 用 PostgreSQL，本地用 SQLite
    import os
    if os.environ.get('POSTGRES_URL'):
        # Vercel PostgreSQL（免费 256MB，永久保存）
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('POSTGRES_URL')
    else:
        # 本地开发用 SQLite
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    # Import models so tables are registered before create_all
    from . import models  # noqa
    from .routes import init_routes

    with app.app_context():
        db.create_all()

    init_routes(app)

    return app
