from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from . import db, login_manager
from .models import User, Product, StockLog

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_routes(app):

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for('dashboard'))
            flash('账号或密码错误', 'error')
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('已退出登录', 'info')
        return redirect(url_for('login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        products = Product.query.order_by(
            (Product.stock < Product.threshold).desc(),
            Product.name
        ).all()
        warning_count = sum(1 for p in products if p.stock < p.threshold)
        total_count = len(products)
        return render_template('dashboard.html',
                               products=products,
                               warning_count=warning_count,
                               total_count=total_count)

    @app.route('/product/add', methods=['GET', 'POST'])
    @login_required
    def add_product():
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            category = request.form.get('category', '').strip()
            unit = request.form.get('unit', '件').strip()
            stock = request.form.get('stock', 0, type=int)
            threshold = request.form.get('threshold', 10, type=int)
            if not name:
                flash('产品名称不能为空', 'error')
                return redirect(url_for('add_product'))
            p = Product(name=name, category=category or '未分类',
                        unit=unit, stock=stock, threshold=threshold,
                        created_at=datetime.now().strftime('%Y-%m-%d %H:%M'))
            db.session.add(p)
            db.session.commit()
            flash(f'产品「{name}」添加成功', 'success')
            return redirect(url_for('dashboard'))
        return render_template('product_add.html')

    @app.route('/product/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_product(id):
        p = Product.query.get_or_404(id)
        if request.method == 'POST':
            p.name = request.form.get('name', '').strip()
            p.category = request.form.get('category', '').strip() or '未分类'
            p.unit = request.form.get('unit', '件').strip()
            p.threshold = request.form.get('threshold', 10, type=int)
            db.session.commit()
            flash(f'产品「{p.name}」已更新', 'success')
            return redirect(url_for('dashboard'))
        return render_template('product_edit.html', product=p)

    @app.route('/product/delete/<int:id>', methods=['POST'])
    @login_required
    def delete_product(id):
        p = Product.query.get_or_404(id)
        name = p.name
        StockLog.query.filter_by(product_id=id).delete()
        db.session.delete(p)
        db.session.commit()
        flash(f'产品「{name}」已删除', 'warning')
        return redirect(url_for('dashboard'))

    @app.route('/stock/in/<int:id>', methods=['GET', 'POST'])
    @login_required
    def stock_in(id):
        p = Product.query.get_or_404(id)
        if request.method == 'POST':
            qty = request.form.get('quantity', 0, type=int)
            note = request.form.get('note', '').strip()
            if qty <= 0:
                flash('入库数量必须大于0', 'error')
                return redirect(url_for('stock_in', id=id))
            p.stock += qty
            log = StockLog(product_id=id, change_type='in', quantity=qty,
                           note=note, operator=current_user.username,
                           created_at=datetime.now().strftime('%Y-%m-%d %H:%M'))
            db.session.add(log)
            db.session.commit()
            flash(f'入库成功：{p.name} +{qty}{p.unit}', 'success')
            return redirect(url_for('dashboard'))
        return render_template('stock_in.html', product=p)

    @app.route('/stock/out/<int:id>', methods=['GET', 'POST'])
    @login_required
    def stock_out(id):
        p = Product.query.get_or_404(id)
        if request.method == 'POST':
            qty = request.form.get('quantity', 0, type=int)
            note = request.form.get('note', '').strip()
            if qty <= 0:
                flash('出库数量必须大于0', 'error')
                return redirect(url_for('stock_out', id=id))
            if qty > p.stock:
                flash('库存不足，无法出库', 'error')
                return redirect(url_for('stock_out', id=id))
            p.stock -= qty
            log = StockLog(product_id=id, change_type='out', quantity=qty,
                           note=note, operator=current_user.username,
                           created_at=datetime.now().strftime('%Y-%m-%d %H:%M'))
            db.session.add(log)
            db.session.commit()
            flash(f'出库成功：{p.name} -{qty}{p.unit}', 'success')
            return redirect(url_for('dashboard'))
        return render_template('stock_out.html', product=p)

    @app.route('/logs')
    @login_required
    def logs():
        logs = StockLog.query.order_by(StockLog.id.desc()).limit(100).all()
        product_map = {p.id: p.name for p in Product.query.all()}
        return render_template('logs.html', logs=logs, product_map=product_map)

    @app.route('/warnings')
    @login_required
    def warnings():
        products = Product.query.filter(Product.stock < Product.threshold).order_by(Product.stock).all()
        return render_template('warnings.html', products=products)

    @app.route('/password', methods=['GET', 'POST'])
    @login_required
    def change_password():
        if request.method == 'POST':
            old = request.form.get('old_password', '')
            new_pwd = request.form.get('new_password', '')
            confirm = request.form.get('confirm_password', '')
            if not current_user.check_password(old):
                flash('原密码错误', 'error')
                return redirect(url_for('change_password'))
            if len(new_pwd) < 6:
                flash('新密码至少6位', 'error')
                return redirect(url_for('change_password'))
            if new_pwd != confirm:
                flash('两次密码不一致', 'error')
                return redirect(url_for('change_password'))
            current_user.set_password(new_pwd)
            db.session.commit()
            flash('密码修改成功，请重新登录', 'success')
            logout_user()
            return redirect(url_for('login'))
        return render_template('password.html')

    @app.route('/api/products')
    @login_required
    def api_products():
        products = Product.query.order_by(
            (Product.stock < Product.threshold).desc(),
            Product.name
        ).all()
        return jsonify([{
            'id': p.id, 'name': p.name, 'category': p.category,
            'unit': p.unit, 'stock': p.stock, 'threshold': p.threshold,
            'warning': p.stock < p.threshold,
            'created_at': p.created_at
        } for p in products])

    # Seed initial admin
    with app.app_context():
        if not User.query.filter_by(username='sanqi').first():
            u = User(username='sanqi')
            u.set_password('888999')
            db.session.add(u)
            db.session.commit()
