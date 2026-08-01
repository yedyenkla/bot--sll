import os
import sqlite3
from flask import Flask, request, redirect, url_for, render_template_string, session
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# --- CẤU HÌNH HỆ THỐNG ---
TOKEN = "8978355103:AAHuIzc1USzlFDLolFRIsRMFKL6r6CCck5w"
ADMIN_IDS = [8455715505]  
ADMIN_PASSWORD = "123"  
SECRET_KEY = "khoa_bi_mat_flask_session_sll_manager"     

# --- KHỞI TẠO DATABASE ---
def init_db():
    with sqlite3.connect("accounts_manager.db", check_same_thread=False) as conn:
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

init_db()

def get_stats():
    with sqlite3.connect("accounts_manager.db", check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM accounts WHERE status = 0")
        unimported = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM accounts WHERE status = 1")
        imported = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM accounts WHERE status = 2")
        sold = cursor.fetchone()[0]
    return unimported, imported, sold

# --- GIAO DIỆN WEB (HTML + CSS + JS) MỚI NHẤT & ĐẸP MẮT ---
app = Flask(__name__)
app.secret_key = SECRET_KEY

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SLL Manager Pro - Enterprise Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bs-body-font-family: 'Plus Jakarta Sans', sans-serif;
            --sidebar-width: 280px;
            --bg-main: #060913;
            --bg-card: #0e1526;
            --bg-card-hover: #131c31;
            --border-color: #1e293b;
            --accent-glow: rgba(56, 189, 248, 0.12);
        }
        body {
            background-color: var(--bg-main);
            color: #94a3b8;
            font-family: var(--bs-body-font-family);
            overflow-x: hidden;
        }
        .sidebar {
            width: var(--sidebar-width);
            height: 100vh;
            position: fixed;
            top: 0;
            left: 0;
            background-color: var(--bg-card);
            border-right: 1px solid var(--border-color);
            z-index: 1040;
            display: flex;
            flex-direction: column;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .sidebar-brand {
            padding: 24px;
            font-size: 1.15rem;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid var(--border-color);
        }
        .sidebar-brand .logo-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #38bdf8 0%, #2563eb 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            box-shadow: 0 4px 12px rgba(56, 189, 248, 0.3);
        }
        .nav-sidebar {
            padding: 20px 16px;
            list-style: none;
            margin: 0;
            flex-grow: 1;
        }
        .nav-sidebar .nav-link {
            color: #64748b;
            padding: 12px 16px;
            font-weight: 600;
            font-size: 0.92rem;
            display: flex;
            align-items: center;
            gap: 14px;
            border-radius: 12px;
            transition: all 0.25s ease;
            margin-bottom: 6px;
        }
        .nav-sidebar .nav-link:hover, .nav-sidebar .nav-link.active {
            color: #38bdf8;
            background: var(--accent-glow);
            box-shadow: inset 0 0 0 1px rgba(56, 189, 248, 0.2);
        }
        .nav-sidebar .nav-link i {
            font-size: 1.2rem;
        }
        .main-content {
            margin-left: var(--sidebar-width);
            padding: 40px;
            min-height: 100vh;
        }
        @media (max-width: 991.98px) {
            .sidebar { transform: translateX(-100%); }
            .main-content { margin-left: 0; padding: 20px; }
        }
        .glass-card {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }
        .glass-card:hover {
            border-color: rgba(56, 189, 248, 0.3);
        }
        .stat-card {
            position: relative;
            overflow: hidden;
            padding: 24px;
        }
        .stat-card::after {
            content: '';
            position: absolute;
            top: 0; right: 0;
            width: 120px; height: 120px;
            background: radial-gradient(circle, rgba(56, 189, 248, 0.05) 0%, transparent 70%);
            pointer-events: none;
        }
        .table-custom {
            margin-bottom: 0;
        }
        .table-custom th {
            background-color: #0b1120 !important;
            color: #64748b;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.7rem;
            letter-spacing: 1.2px;
            border-bottom: 1px solid var(--border-color) !important;
            padding: 16px 20px;
        }
        .table-custom td {
            background-color: var(--bg-card) !important;
            border-bottom: 1px solid #162238 !important;
            padding: 16px 20px;
            vertical-align: middle;
            color: #cbd5e1;
            font-size: 0.9rem;
        }
        .table-custom tr:hover td {
            background-color: var(--bg-card-hover) !important;
        }
        .account-box {
            background: #060913;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 8px 12px;
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 0.82rem;
            color: #38bdf8;
            word-break: break-all;
            display: inline-block;
            max-width: 320px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            vertical-align: middle;
        }
        .form-control, .form-select {
            background-color: #060913;
            border: 1px solid var(--border-color);
            color: #f8fafc;
            border-radius: 12px;
            padding: 14px 18px;
            font-size: 0.95rem;
            transition: all 0.25s ease;
        }
        .form-control:focus, .form-select:focus {
            background-color: #060913;
            border-color: #38bdf8;
            color: #f8fafc;
            box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.15);
        }
        textarea.form-control {
            min-height: 120px;
            resize: vertical;
        }
        .btn-glow {
            background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%);
            border: none;
            color: #fff;
            font-weight: 700;
            padding: 12px 24px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(56, 189, 248, 0.35);
            transition: all 0.25s ease;
        }
        .btn-glow:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(56, 189, 248, 0.5);
            color: #fff;
        }
        .badge-custom {
            font-weight: 700;
            padding: 6px 12px;
            border-radius: 50rem;
            font-size: 0.72rem;
            letter-spacing: 0.5px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .badge-pending { background-color: rgba(234, 179, 8, 0.12); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.25); }
        .badge-imported { background-color: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.25); }
        .badge-sold { background-color: rgba(34, 197, 94, 0.12); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.25); }
        #toast-container { position: fixed; bottom: 30px; right: 30px; z-index: 1080; }
        .login-wrapper {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: radial-gradient(circle at 50% 30%, #111c38 0%, #060913 70%);
            padding: 20px;
        }
    </style>
</head>
<body>

    {% if not session.get('logged_in') %}
    <!-- ĐĂNG NHẬP ENTERPRISE -->
    <div class="login-wrapper">
        <div class="glass-card p-4 p-md-5 w-100" style="max-width: 440px;">
            <div class="text-center mb-4">
                <div class="logo-icon mx-auto mb-3 shadow-lg" style="width: 64px; height: 64px; border-radius: 18px; font-size: 1.8rem;">
                    <i class="bi bi-shield-lock-fill"></i>
                </div>
                <h3 class="fw-bold text-white fs-4 mb-1">Xác Thực Quản Trị</h3>
                <p class="text-secondary small">Hệ thống quản lý kho tài khoản SLL Pro</p>
            </div>
            <form method="POST" action="/login">
                <div class="mb-4">
                    <label class="form-label text-secondary small fw-bold text-uppercase mb-2">Mật khẩu quản trị</label>
                    <div class="input-group">
                        <span class="input-group-text bg-transparent border-end-0" style="border-color: var(--border-color); border-radius: 12px 0 0 12px; color: #64748b;"><i class="bi bi-key"></i></span>
                        <input type="password" name="password" class="form-control border-start-0 ps-0" placeholder="Nhập mật khẩu bảo mật..." required style="border-radius: 0 12px 12px 0;">
                    </div>
                </div>
                <button type="submit" class="btn btn-glow w-100 py-3 shadow-lg">Truy Cập Hệ Thống</button>
            </form>
        </div>
    </div>
    {% else %}

    <!-- SIDEBAR HIỆN ĐẠI -->
    <div class="sidebar">
        <div class="sidebar-brand">
            <div class="logo-icon">
                <i class="bi bi-cpu-fill fs-5"></i>
            </div>
            <span>SLL MANAGER <span class="badge bg-primary bg-opacity-20 text-primary fs-8 ms-1">PRO</span></span>
        </div>
        <ul class="nav-sidebar">
            <li>
                <a href="/" class="nav-link active"><i class="bi bi-grid-1x2-fill"></i> Tổng Quan Kho</a>
            </li>
        </ul>
        <div class="p-3 m-3 rounded-4" style="background-color: #060913; border: 1px solid var(--border-color);">
            <div class="d-flex align-items-center gap-2 small text-success fw-bold mb-3">
                <span class="spinner-grow spinner-grow-sm text-success" role="status" aria-hidden="true"></span>
                Bot Telegram: Hoạt Động
            </div>
            <a href="/logout" class="btn btn-outline-danger btn-sm w-100 py-2 rounded-3 fw-semibold"><i class="bi bi-box-arrow-right me-1"></i> Đăng Xuất</a>
        </div>
    </div>

    <!-- MOBILE NAVBAR -->
    <nav class="navbar navbar-dark border-bottom border-secondary d-lg-none px-4 py-3" style="background-color: var(--bg-card); border-color: var(--border-color) !important;">
        <div class="container-fluid px-0">
            <span class="navbar-brand fw-bold fs-6 d-flex align-items-center gap-2">
                <i class="bi bi-cpu-fill text-primary"></i> SLL MANAGER PRO
            </span>
            <a href="/logout" class="btn btn-outline-danger btn-sm px-3 rounded-pill"><i class="bi bi-box-arrow-right"></i></a>
        </div>
    </nav>

    <!-- MAIN CONTENT -->
    <div class="main-content">
        <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4 pb-2 border-bottom" style="border-color: var(--border-color) !important;">
            <div>
                <h2 class="fw-extrabold text-white fs-3 mb-1">Bảng Điều Hành Kho Tài Khoản</h2>
                <p class="text-secondary small mb-0">Hệ thống cấp phát & quản lý tài khoản tự động SLL cho Người làm và Đối tác.</p>
            </div>
            <div>
                <a href="/" class="btn btn-outline-light btn-sm px-3 py-2 rounded-pill border-secondary bg-transparent text-light fw-semibold"><i class="bi bi-arrow-clockwise me-1"></i> Làm Mới Dữ Liệu</a>
            </div>
        </div>

        <!-- THỐNG KÊ DASHBOARD -->
        <div class="row g-4 mb-4">
            <div class="col-12 col-md-4">
                <div class="glass-card stat-card">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <span class="text-secondary small fw-bold text-uppercase tracking-wider">Chưa nhập mã</span>
                            <h2 class="fw-extrabold text-warning mt-2 mb-0 fs-2">{{ unimported }}</h2>
                        </div>
                        <div class="bg-warning bg-opacity-10 p-3 rounded-4 text-warning"><i class="bi bi-clock-history fs-2"></i></div>
                    </div>
                </div>
            </div>
            <div class="col-12 col-md-4">
                <div class="glass-card stat-card">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <span class="text-secondary small fw-bold text-uppercase tracking-wider">Sẵn Sàng Bán</span>
                            <h2 class="fw-extrabold text-info mt-2 mb-0 fs-2">{{ imported }}</h2>
                        </div>
                        <div class="bg-info bg-opacity-10 p-3 rounded-4 text-info"><i class="bi bi-check2-circle fs-2"></i></div>
                    </div>
                </div>
            </div>
            <div class="col-12 col-md-4">
                <div class="glass-card stat-card">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <span class="text-secondary small fw-bold text-uppercase tracking-wider">Đã Bán Tổng Cộng</span>
                            <h2 class="fw-extrabold text-success mt-2 mb-0 fs-2">{{ sold }}</h2>
                        </div>
                        <div class="bg-success bg-opacity-10 p-3 rounded-4 text-success"><i class="bi bi-cart-check fs-2"></i></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- KHUNG NHẬP KHO HÀNG LOẠT -->
        <div class="glass-card p-4 mb-4">
            <h5 class="fw-bold text-white fs-6 mb-3 d-flex align-items-center gap-2">
                <i class="bi bi-cloud-arrow-up-fill text-success fs-5"></i> Thêm Tài Khoản Hàng Loạt (Mỗi dòng một tài khoản)
            </h5>
            <form method="POST" action="/add">
                <div class="row g-3">
                    <div class="col-12 col-lg-10">
                        <textarea class="form-control" name="accounts" placeholder="Dán danh sách tài khoản định dạng user|pass hoặc thông tin chi tiết..." required></textarea>
                    </div>
                    <div class="col-12 col-lg-2 d-flex flex-column justify-content-end">
                        <button type="submit" class="btn btn-success w-100 py-3 fw-bold shadow-sm rounded-3" style="background: linear-gradient(135deg, #22c55e 0%, #15803d 100%); border: none;">
                            <i class="bi bi-plus-lg me-1"></i> Thêm Vào Kho
                        </button>
                    </div>
                </div>
            </form>
        </div>

        <!-- BẢNG DỮ LIỆU & LỌC -->
        <div class="glass-card overflow-hidden">
            <div class="p-4 border-bottom d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3" style="border-color: var(--border-color) !important;">
                <h5 class="fw-bold text-white fs-6 mb-0 d-flex align-items-center gap-2">
                    <i class="bi bi-table text-primary"></i> Danh Sách Tài Khoản Gần Đây
                </h5>
                <div class="w-100 w-md-auto" style="max-width: 320px;">
                    <div class="input-group input-group-sm">
                        <span class="input-group-text bg-transparent border-end-0 text-secondary" style="border-color: var(--border-color); border-radius: 10px 0 0 10px;"><i class="bi bi-search"></i></span>
                        <input type="text" id="searchInput" class="form-control form-control-sm border-start-0 ps-0" placeholder="Lọc nhanh tài khoản trên màn hình..." onkeyup="filterTable()" style="border-radius: 0 10px 10px 0;">
                    </div>
                </div>
            </div>
            <div class="table-responsive">
                <table class="table table-custom mb-0" id="accountTable">
                    <thead>
                        <tr>
                            <th class="ps-4">#ID</th>
                            <th>Thông tin tài khoản</th>
                            <th>Trạng thái</th>
                            <th>Xử lý / Mua bởi</th>
                            <th class="text-center pe-4">Thao tác</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for acc in accounts %}
                        <tr>
                            <td class="ps-4 text-secondary fw-bold">#{{ acc[0] }}</td>
                            <td><span class="account-box" title="{{ acc[1] }}">{{ acc[1] }}</span></td>
                            <td>
                                {% if acc[2] == 0 %}<span class="badge-custom badge-pending"><i class="bi bi-circle-fill" style="font-size: 6px;"></i> Chưa nhập</span>
                                {% elif acc[2] == 1 %}<span class="badge-custom badge-imported"><i class="bi bi-circle-fill" style="font-size: 6px;"></i> Sẵn bán</span>
                                {% else %}<span class="badge-custom badge-sold"><i class="bi bi-circle-fill" style="font-size: 6px;"></i> Đã bán</span>{% endif %}
                            </td>
                            <td class="text-secondary small">
                                {% if acc[3] %}<span class="text-info fw-semibold">Làm: {{ acc[3] }}</span>{% endif %}
                                {% if acc[4] %}<span class="text-success fw-semibold"> | Bán: {{ acc[4] }}</span>{% endif %}
                                {% if not acc[3] and not acc[4] %}<span class="text-muted">Chưa gán</span>{% endif %}
                            </td>
                            <td class="text-center pe-4">
                                <button class="btn btn-sm btn-outline-info px-2 py-1 me-1 rounded-2" onclick="showToast('{{ acc[1] }}')" title="Copy tài khoản"><i class="bi bi-clipboard"></i></button>
                                <a href="/delete/{{ acc[0] }}" class="btn btn-sm btn-outline-danger px-2 py-1 rounded-2" title="Xóa tài khoản" onclick="return confirm('Bạn có chắc muốn xóa tài khoản này khỏi hệ thống?')"><i class="bi bi-trash"></i></a>
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="5" class="text-center py-5 text-secondary">
                                <i class="bi bi-inbox fs-1 d-block mb-2 text-muted"></i>
                                Kho hiện tại chưa có tài khoản nào trong cơ sở dữ liệu.
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    {% endif %}

    <!-- TOAST NOTIFICATION -->
    <div id="toast-container">
        <div id="copyToast" class="toast align-items-center text-white bg-dark border border-success shadow-lg rounded-3" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex p-2">
                <div class="toast-body fw-semibold text-success d-flex align-items-center gap-2">
                    <i class="bi bi-check-circle-fill fs-5"></i> Đã sao chép tài khoản vào bộ nhớ tạm!
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

        function filterTable() {
            let input = document.getElementById("searchInput");
            let filter = input.value.toLowerCase();
            let table = document.getElementById("accountTable");
            let tr = table.getElementsByTagName("tr");

            for (let i = 1; i < tr.length; i++) {
                let td = tr[i].getElementsByTagName("td")[1];
                if (td) {
                    let txtValue = td.textContent || td.innerText;
                    if (txtValue.toLowerCase().indexOf(filter) > -1) {
                        tr[i].style.display = "";
                    } else {
                        tr[i].style.display = "none";
                    }
                }
            }
        }
    </script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# --- ROUTE WEB ---
@app.route('/')
def index():
    unimported, imported, sold = get_stats()
    with sqlite3.connect("accounts_manager.db", check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, account_data, status, imported_by, sold_to FROM accounts ORDER BY id DESC LIMIT 50")
        accounts = cursor.fetchall()
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
    
    with sqlite3.connect("accounts_manager.db", check_same_thread=False) as conn:
        cursor = conn.cursor()
        for line in lines:
            acc = line.strip()
            if acc:
                try:
                    cursor.execute("INSERT INTO accounts (account_data, status) VALUES (?, 0)", (acc,))
                except sqlite3.IntegrityError:
                    pass 
        conn.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:acc_id>')
def delete_account(acc_id):
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    with sqlite3.connect("accounts_manager.db", check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM accounts WHERE id = ?", (acc_id,))
        conn.commit()
    return redirect(url_for('index'))

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# --- BOT TELEGRAM (GIỮ NGUYÊN 100%) ---
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
        with sqlite3.connect("accounts_manager.db", check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, account_data FROM accounts WHERE status = 0 LIMIT 5")
            rows = cursor.fetchall()
            if not rows:
                await query.message.reply_text("❌ Kho hiện tại đã hết tài khoản chưa nhập mã!")
                return
            acc_ids = [row[0] for row in rows]
            acc_texts = [row[1] for row in rows]
            cursor.executemany("UPDATE accounts SET status = 1, imported_by = ? WHERE id = ?", [(user_id, aid) for aid in acc_ids])
            conn.commit()
        result_str = "\n".join(acc_texts)
        keyboard = [[InlineKeyboardButton("🔙 Quay lại menu chính", callback_data="back_home")]]
        await query.message.reply_text(f"📦 **Danh sách tài khoản cho bạn (Chạm vào đoạn mã dưới để copy):**\n\n```{result_str}```", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "get_seller":
        is_admin = user_id in ADMIN_IDS
        limit = 9999 if is_admin else 5
        with sqlite3.connect("accounts_manager.db", check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, account_data FROM accounts WHERE status = 1 LIMIT ?", (limit,))
            rows = cursor.fetchall()
            if not rows:
                await query.message.reply_text("❌ Không có tài khoản đã nhập mã nào khả dụng để bán!")
                return
            acc_ids = [row[0] for row in rows]
            acc_texts = [row[1] for row in rows]
            cursor.executemany("UPDATE accounts SET status = 2, sold_to = ? WHERE id = ?", [(user_id, aid) for aid in acc_ids])
            conn.commit()
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
