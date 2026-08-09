from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
import requests
import os
from . import db, login_manager
from .models import User, Product, StockLog

# 企业微信配置（从环境变量读取）
WECHAT_CORP_ID = os.environ.get('WECHAT_CORP_ID', '')
WECHAT_AGENT_ID = os.environ.get('WECHAT_AGENT_ID', '')
WECHAT_SECRET = os.environ.get('WECHAT_SECRET', '')
WECHAT_TO_USER = os.environ.get('WECHAT_TO_USER', '@all')  # @all 或成员ID

def get_wechat_access_token():
    """获取企业微信 access_token"""
    if not WECHAT_CORP_ID or not WECHAT_SECRET:
        return None
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={WECHAT_CORP_ID}&corpsecret={WECHAT_SECRET}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return data.get('access_token')
    except Exception as e:
        print(f"获取企业微信token失败: {e}")
        return None

def send_wechat_message(title, content, url=None):
    """发送企业微信消息"""
    if not WECHAT_CORP_ID or not WECHAT_AGENT_ID or not WECHAT_SECRET:
        print("企业微信未配置，跳过推送")
        return False
    
    access_token = get_wechat_access_token()
    if not access_token:
        return False
    
    msg_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
    
    # 使用文本卡片消息，更醒目
    data = {
        "touser": WECHAT_TO_USER,
        "msgtype": "textcard",
        "agentid": WECHAT_AGENT_ID,
        "textcard": {
            "title": title,
            "description": content,
            "url": url or "https://work.weixin.qq.com",
            "btntxt": "查看详情"
        }
    }
    
    try:
        resp = requests.post(msg_url, json=data, timeout=10)
        result = resp.json()
        if result.get('errcode') == 0:
            print(f"企业微信推送成功: {title}")
            return True
        else:
            print(f"企业微信推送失败: {result}")
            return False
    except Exception as e:
        print(f"企业微信推送异常: {e}")
        return False

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
            # 入库推送通知
            send_wechat_message(
                title=f"📦 入库通知 - {p.name}",
                content=f"<div class=\"gray\">产品：{p.name}</div> <div class=\"normal\">入库数量：+{qty} {p.unit}</div><div class=\"normal\">当前库存：{p.stock} {p.unit}</div><div class=\"highlight\">操作人：{current_user.username}</div>",
                url=request.url_root
            )
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
            # 出库推送通知
            send_wechat_message(
                title=f"🚚 出库通知 - {p.name}",
                content=f"<div class=\"gray\">产品：{p.name}</div> <div class=\"normal\">出库数量：-{qty} {p.unit}</div><div class=\"normal\">当前库存：{p.stock} {p.unit}</div><div class=\"highlight\">操作人：{current_user.username}</div>",
                url=request.url_root
            )
            # 如果库存低于预警值，额外推送预警
            if p.stock < p.threshold:
                send_wechat_message(
                    title=f"⚠️ 库存预警 - {p.name}",
                    content=f"<div class=\"gray\">产品：{p.name}</div><div class=\"warning\">当前库存：<b>{p.stock}</b> {p.unit}</div><div class=\"normal\">预警阈值：{p.threshold} {p.unit}</div><div class=\"highlight\">请及时补货！</div>",
                    url=request.url_root + 'warnings'
                )
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

    @app.route('/settings', methods=['GET', 'POST'])
    @login_required
    def settings():
        """系统设置 - 企业微信配置"""
        if request.method == 'POST':
            # 这里只是展示，实际配置通过环境变量
            flash('企业微信配置请通过环境变量设置', 'info')
        wechat_configured = bool(WECHAT_CORP_ID and WECHAT_AGENT_ID and WECHAT_SECRET)
        return render_template('settings.html', wechat_configured=wechat_configured)

    @app.route('/test-wechat', methods=['POST'])
    @login_required
    def test_wechat():
        """测试企业微信推送"""
        if not WECHAT_CORP_ID or not WECHAT_AGENT_ID or not WECHAT_SECRET:
            flash('企业微信未配置，请先设置环境变量', 'error')
            return redirect(url_for('settings'))
        
        success = send_wechat_message(
            title="✅ 测试消息 - 三琪库存系统",
            content=f"<div class=\"gray\">这是一条测试消息</div><div class=\"normal\">发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div><div class=\"highlight\">如果收到这条消息，说明推送配置成功！</div>",
            url=request.url_root
        )
        if success:
            flash('测试消息已发送，请查看企业微信', 'success')
        else:
            flash('测试消息发送失败，请检查配置', 'error')
        return redirect(url_for('settings'))

    # Seed initial admin
    with app.app_context():
        if not User.query.filter_by(username='sanqi').first():
            u = User(username='sanqi')
            u.set_password('888999')
            db.session.add(u)
            db.session.commit()
