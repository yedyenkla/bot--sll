import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
import pytz
from flask import Flask, request, redirect, url_for, render_template_string, session
from threading import Thread

# --- CẤU HÌNH BOT & WEB ---
TOKEN = "8978355103:AAHuIzc1USzlFDLolFRIsRMFKL6r6CCck5w"
ADMIN_IDS = [8455715505]  
ADMIN_PASSWORD = "Bxt223344@"  # Mật khẩu đăng nhập trang web quản lý
SECRET_KEY = "khoa_bi_mat_flask_session"     

# --- KHỞI TẠO DATABASE ---
def init_db():
    conn = sqlite3.connect("accounts_manager.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_data TEXT UNIQUE,
            status INTEGER DEFAULT 0,
            imported_by INTEGER,
            sold_to INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    conn.commit()
    conn.close()

init_db()

def get_stats():
    conn = sqlite3.connect("accounts_manager.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM accounts WHERE status = 0")
    unimported = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM accounts WHERE status = 1")
    imported = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM accounts WHERE status = 2")
    sold = cursor.fetchone()[0]
    conn.close()
    return unimported, imported, sold

# --- GIAO DIỆN WEB QUẢN LÝ KHO (PRO UI) ---
app = Flask(__name__)
app.secret_key = SECRET_KEY

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SLL Manager Pro - Ultimate Edition</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bs-body-font-family: 'Plus Jakarta Sans', sans-serif;
            --sidebar-width: 270px;
        }
        body {
            background-color: #090d16;
            color: #94a3b8;
            font-family: var(--bs-body-font-family);
        }
        .sidebar {
            width: var(--sidebar-width);
            height: 100vh;
            position: fixed;
            top: 0;
            left: 0;
            background-color: #0e1626;
            border-right: 1px solid #1e293b;
            z-index: 1000;
        }
        .sidebar .brand {
            font-weight: 700;
            font-size: 1.2rem;
            color: #ffffff;
            padding: 24px;
            letter-spacing: 0.5px;
        }
        .sidebar .nav-link {
            color: #64748b;
            padding: 13px 24px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 12px;
            transition: all 0.25s ease;
        }
        .sidebar .nav-link:hover, .sidebar .nav-link.active {
            color: #38bdf8;
            background: linear-gradient(90deg, rgba(56, 189, 248, 0.1) 0%, rgba(56, 189, 248, 0) 100%);
            border-left: 3px solid #38bdf8;
        }
        .main-content {
            margin-left: var(--sidebar-width);
            padding: 35px;
        }
        .glass-card {
            background: #111c2e;
            border: 1px solid #1e293b;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }
        .table-custom th {
            background-color: #111c2e !important;
            color: #64748b;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.7rem;
            letter-spacing: 1px;
            border-bottom: 1px solid #1e293b !important;
            padding: 16px;
        }
        .table-custom td {
            background-color: #111c2e !important;
            border-bottom: 1px solid #162235 !important;
            padding: 16px;
            vertical-align: middle;
            color: #cbd5e1;
        }
        .account-box {
            background: #090d16;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 6px 12px;
            font-family: monospace;
            font-size: 0.85rem;
            color: #38bdf8;
        }
        .form-control, .form-select {
            background-color: #090d16;
            border: 1px solid #1e293b;
            color: #f8fafc;
            border-radius: 10px;
            padding: 12px;
        }
        .form-control:focus, .form-select:focus {
            background-color: #090d16;
            border-color: #38bdf8;
            color: #f8fafc;
            box-shadow: 0 0 0 0.25rem rgba(56, 189, 248, 0.15);
        }
        .badge-pending {
            background-color: rgba(234, 179, 8, 0.15);
            color: #facc15;
            border: 1px solid rgba(234, 179, 8, 0.3);
            font-weight: 700;
            padding: 6px 12px;
            border-radius: 50rem;
            font-size: 0.75rem;
        }
        .badge-imported {
            background-color: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            font-weight: 700;
            padding: 6px 12px;
            border-radius: 50rem;
            font-size: 0.75rem;
        }
        .badge-sold {
            background-color: rgba(34, 197, 94, 0.15);
            color: #4ade80;
            border: 1px solid rgba(34, 197, 94, 0.3);
            font-weight: 700;
            padding: 6px 12px;
            border-radius: 50rem;
            font-size: 0.75rem;
        }
        #toast-container {
            position: fixed;
            bottom: 25px;
            right: 25px;
            z-index: 1050;
        }
    </style>
</head>
<body>

    {% if not session.get('logged_in') %}
    <!-- GIAO DIỆN ĐĂNG NHẬP -->
    <div class="container d-flex align-items-center justify-content-center min-vh-100">
        <div class="glass-card p-5 w-100" style="max-width: 450px;">
            <div class="text-center mb-4">
                <div class="bg-primary bg-opacity-15 p-3 rounded-4 text-primary d-inline-block mb-3">
                    <i class="bi bi-shield-lock-fill fs-2"></i>
                </div>
                <h3 class="fw-bold text-white">Đăng Nhập Quản Trị</h3>
                <p class="text-secondary small">Hệ thống quản lý kho tài khoản SLL</p>
            </div>
            <form method="POST" action="/login">
                <div class="mb-3">
                    <label class="form-label text-secondary small">Mật khẩu quản trị</label>
                    <input type="password" name="password" class="form-control" placeholder="Nhập mật khẩu..." required>
                </div>
                <button type="submit" class="btn btn-primary w-100 py-3 fw-bold rounded-3 shadow-sm">Xác Nhận Đăng Nhập</button>
            </form>
        </div>
    </div>
    {% else %}

    <!-- Sidebar -->
    <div class="sidebar d-flex flex-column">
        <div class="brand d-flex align-items-center gap-3">
            <div class="bg-primary bg-opacity-15 p-2 rounded-3 text-primary">
                <i class="bi bi-shield-lock-fill fs-4"></i>
            </div>
            <span>SLL MANAGER</span>
        </div>
        <ul class="nav flex-column flex-grow-1 pt-2">
            <li class="nav-item">
                <a href="/" class="nav-link active"><i class="bi bi-grid-1x2-fill"></i> Tổng quan kho</a>
            </li>
        </ul>
        <div class="p-3 m-3 rounded-3" style="background-color: #090d16; border: 1px solid #1e293b;">
            <div class="d-flex align-items-center gap-2 small text-success fw-semibold mb-2">
                <i class="bi bi-circle-fill" style="font-size: 8px;"></i> Bot Telegram: Hoạt động
            </div>
            <a href="/logout" class="btn btn-outline-danger btn-sm w-100 mt-1"><i class="bi bi-box-arrow-right me-1"></i> Đăng xuất</a>
        </div>
    </div>

    <!-- Main Content -->
    <div class="main-content">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <div>
                <h3 class="fw-bold text-white mb-1">Bảng Điều Hành Kho Tài Khoản</h3>
                <p class="text-secondary small mb-0">Hệ thống cấp phát tự động SLL cho Người làm & Người bán.</p>
            </div>
            <div>
                <a href="/" class="btn btn-outline-light btn-sm px-3 py-2 rounded-pill border-secondary"><i class="bi bi-arrow-clockwise me-1"></i> Làm mới</a>
            </div>
        </div>

        <!-- Thống kê nhanh -->
        <div class="row g-4 mb-4">
            <div class="col-md-4">
                <div class="glass-card p-4">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <span class="text-secondary small fw-bold text-uppercase">Chưa nhập mã</span>
                            <h2 class="fw-bold text-warning mt-2 mb-0">{{ unimported }}</h2>
                        </div>
                        <div class="bg-warning bg-opacity-10 p-3 rounded-4 text-warning">
                            <i class="bi bi-clock-history fs-3"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="glass-card p-4">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <span class="text-secondary small fw-bold text-uppercase">Đã nhập mã (Sẵn bán)</span>
                            <h2 class="fw-bold text-info mt-2 mb-0">{{ imported }}</h2>
                        </div>
                        <div class="bg-info bg-opacity-10 p-3 rounded-4 text-info">
                            <i class="bi bi-check2-circle fs-3"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="glass-card p-4">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <span class="text-secondary small fw-bold text-uppercase">Đã bán tổng cộng</span>
                            <h2 class="fw-bold text-success mt-2 mb-0">{{ sold }}</h2>
                        </div>
                        <div class="bg-success bg-opacity-10 p-3 rounded-4 text-success">
                            <i class="bi bi-cart-check fs-3"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Khung nhập SLL -->
        <div class="glass-card p-4 mb-4">
            <h5 class="fw-bold text-white mb-3 d-flex align-items-center gap-2">
                <i class="bi bi-cloud-arrow-up-fill text-success"></i> Thêm Tài Khoản Hàng Loạt (Mỗi dòng 1 tài khoản)
            </h5>
            <form method="POST" action="/add">
                <div class="row g-3">
                    <div class="col-md-9">
                        <textarea class="form-control" name="accounts" rows="3" placeholder="user|pass hoặc thông tin tài khoản..." required style="resize: none;"></textarea>
                    </div>
                    <div class="col-md-3 d-flex flex-column justify-content-end">
                        <button type="submit" class="btn btn-success w-100 py-3 fw-bold shadow-sm rounded-3">
                            <i class="bi bi-plus-lg me-1"></i> Thêm Vào Kho Ngay
                        </button>
                    </div>
                </div>
            </form>
        </div>

        <!-- Bảng danh sách tài khoản -->
        <div class="glass-card overflow-hidden">
            <div class="p-4 border-bottom border-secondary d-flex justify-content-between align-items-center" style="border-color: #1e293b !important;">
                <h5 class="fw-bold text-white mb-0">Danh Sách Tài Khoản Gần Đây</h5>
            </div>
            <div class="table-responsive">
                <table class="table table-custom mb-0">
                    <thead>
                        <tr>
                            <th class="ps-4">#ID</th>
                            <th>Thông tin tài khoản</th>
                            <th>Trạng thái</th>
                            <th>Người xử lý / Mua</th>
                            <th class="text-center">Thao tác</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for acc in accounts %}
                        <tr>
                            <td class="ps-4 text-secondary fw-bold">#{{ acc[0] }}</td>
                            <td><span class="account-box">{{ acc[1] }}</span></td>
                            <td>
                                {% if acc[2] == 0 %}
                                    <span class="badge badge-pending">Chưa nhập mã</span>
                                {% elif acc[2] == 1 %}
                                    <span class="badge badge-imported">Sẵn bán</span>
                                {% else %}
                                    <span class="badge badge-sold">Đã bán</span>
                                {% endif %}
                            </td>
                            <td class="text-secondary small">
                                {% if acc[3] %}Làm: {{ acc[3] }}{% endif %}
                                {% if acc[4] %} | Bán: {{ acc[4] }}{% endif %}
                                {% if not acc[3] and not acc[4] %}Trống{% endif %}
                            </td>
                            <td class="text-center">
                                <button class="btn btn-sm btn-outline-info px-2 py-1" onclick="showToast('{{ acc[1] }}')" title="Copy"><i class="bi bi-clipboard"></i></button>
                                <a href="/delete/{{ acc[0] }}" class="btn btn-sm btn-outline-danger px-2 py-1" title="Xóa" onclick="return confirm('Bạn có chắc muốn xóa tài khoản này?')"><i class="bi bi-trash"></i></a>
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="5" class="text-center py-4 text-secondary">Kho hiện tại chưa có tài khoản nào.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    {% endif %}

    <div id="toast-container">
        <div id="copyToast" class="toast align-items-center text-white bg-success border-0 shadow-lg" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body fw-semibold">
                    <i class="bi bi-check-circle-fill me-2"></i> Đã copy tài khoản vào bộ nhớ tạm!
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    </div>

    <script>
        function showToast(text) {
            navigator.clipboard.writeText(text);
            const toastEl = document.getElementById('copyToast');
            const toast = new bootstrap.Toast(toastEl);
            toast.show();
        }
    </script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

@app.route('/')
def index():
    unimported, imported, sold = get_stats()
    conn = sqlite3.connect("accounts_manager.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT id, account_data, status, imported_by, sold_to FROM accounts ORDER BY id DESC LIMIT 50")
    accounts = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, unimported=unimported, imported=imported, sold=sold, accounts=accounts)

@app.route('/login', methods=['POST'])
def login():
    if request.form.get('password') == ADMIN_PASSWORD:
        session['logged_in'] = True
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/add', methods=['POST'])
def add_accounts():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    raw_text = request.form.get('accounts', '')
    lines = raw_text.splitlines()
    
    conn = sqlite3.connect("accounts_manager.db", check_same_thread=False)
    cursor = conn.cursor()
    for line in lines:
        acc = line.strip()
        if acc:
            try:
                cursor.execute("INSERT INTO accounts (account_data, status) VALUES (?, 0)", (acc,))
            except sqlite3.IntegrityError:
                pass 
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:acc_id>')
def delete_account(acc_id):
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    conn = sqlite3.connect("accounts_manager.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM accounts WHERE id = ?", (acc_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# --- PHẦN BOT TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("📥 Lấy ACC Làm Sẵn Tự Động", callback_data="get_worker")],
        [InlineKeyboardButton("🛒 Lấy ACC Bán Tự Động", callback_data="get_seller")],
    ]
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("📊 Xem Thống Kê Kho SLL", callback_data="stats")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = (
        "⭐ **HỆ THỐNG QUẢN LÝ KHO SLL**\n\n"
        "⚡ Hỗ trợ lấy và cấp phát tài khoản tự động, nhanh chóng và ổn định\n"
        "⚙️ Hệ thống tự động – thao tác đơn giản – hạn chế lỗi\n"
        "⏰ Hoạt động liên tục 24/24 phục vụ công việc\n\n"
        "✨ Kho tài khoản riêng biệt, ưu tiên tốc độ, độ ổn định và trải nghiệm sử dụng lâu dài.\n\n"
        "👇 Vui lòng chọn chức năng bên dưới để bắt đầu"
    )
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "stats":
        if user_id not in ADMIN_IDS:
            await query.answer("❌ Bạn không có quyền sử dụng chức năng này!", show_alert=True)
            return
        unimported, imported, sold = get_stats()
        keyboard = [[InlineKeyboardButton("🔙 Quay lại menu chính", callback_data="back_home")]]
        await query.edit_message_text(
            f"📊 **THỐNG KÊ KHO TÀI KHOẢN:**\n\n"
            f"🟡 Chưa nhập mã: `{unimported}`\n"
            f"🔵 Đã nhập mã (Sẵn bán): `{imported}`\n"
            f"🟢 Đã bán tổng cộng: `{sold}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "back_home":
        keyboard = [
            [InlineKeyboardButton("📥 Lấy ACC Làm Sẵn Tự Động", callback_data="get_worker")],
            [InlineKeyboardButton("🛒 Lấy ACC Bán Tự Động", callback_data="get_seller")],
        ]
        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("📊 Xem Thống Kê Kho SLL", callback_data="stats")])
        welcome_text = (
            "⭐ **HỆ THỐNG QUẢN LÝ KHO SLL**\n\n"
            "⚡ Hỗ trợ lấy và cấp phát tài khoản tự động, nhanh chóng và ổn định\n"
            "⚙️ Hệ thống tự động – thao tác đơn giản – hạn chế lỗi\n"
            "⏰ Hoạt động liên tục 24/24 phục vụ công việc\n\n"
            "✨ Kho tài khoản riêng biệt, ưu tiên tốc độ, độ ổn định và trải nghiệm sử dụng lâu dài.\n\n"
            "👇 Vui lòng chọn chức năng bên dưới để bắt đầu"
        )
        await query.edit_message_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "get_worker":
        conn = sqlite3.connect("accounts_manager.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT id, account_data FROM accounts WHERE status = 0 LIMIT 5")
        rows = cursor.fetchall()
        if not rows:
            await query.message.reply_text("❌ Kho hiện tại đã hết tài khoản chưa nhập mã!")
            conn.close()
            return
        acc_ids = [row[0] for row in rows]
        acc_texts = [row[1] for row in rows]
        cursor.executemany("UPDATE accounts SET status = 1, imported_by = ? WHERE id = ?", [(user_id, aid) for aid in acc_ids])
        conn.commit()
        conn.close()
        result_str = "\n".join(acc_texts)
        keyboard = [[InlineKeyboardButton("🔙 Quay lại menu chính", callback_data="back_home")]]
        await query.message.reply_text(f"📦 **Danh sách tài khoản cho bạn (Chạm vào đoạn mã dưới để copy):**\n\n```{result_str}```", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "get_seller":
        is_admin = user_id in ADMIN_IDS
        limit = 9999 if is_admin else 5
        conn = sqlite3.connect("accounts_manager.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT id, account_data FROM accounts WHERE status = 1 LIMIT ?", (limit,))
        rows = cursor.fetchall()
        if not rows:
            await query.message.reply_text("❌ Không có tài khoản đã nhập mã nào khả dụng để bán!")
            conn.close()
            return
        acc_ids = [row[0] for row in rows]
        acc_texts = [row[1] for row in rows]
        cursor.executemany("UPDATE accounts SET status = 2, sold_to = ? WHERE id = ?", [(user_id, aid) for aid in acc_ids])
        conn.commit()
        conn.close()
        result_str = "\n".join(acc_texts)
        keyboard = [[InlineKeyboardButton("🔙 Quay lại menu chính", callback_data="back_home")]]
        await query.message.reply_text(f"🛒 **Danh sách tài khoản bán (SL: {len(acc_texts)} - Chạm vào đoạn mã dưới để copy):**\n\n```{result_str}```", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

def main():
    keep_alive()  
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot và Trang Web Quản Lý đang chạy đồng thời...")
    application.run_polling()

if __name__ == "__main__":
    main()
