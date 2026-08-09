from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), default='未分类')
    unit = db.Column(db.String(20), default='件')
    stock = db.Column(db.Integer, default=0)
    threshold = db.Column(db.Integer, default=10)
    created_at = db.Column(db.String(30), default='')

class StockLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    change_type = db.Column(db.String(10), nullable=False)  # in / out
    quantity = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(200), default='')
    operator = db.Column(db.String(50), default='')
    created_at = db.Column(db.String(30), default='')
