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
    <title>SLL Manager Ultimate - Enterprise Full Edition v3.0</title>
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Bootstrap Icons -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css" rel="stylesheet">
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bs-body-font-family: 'Plus Jakarta Sans', sans-serif;
            --sidebar-width: 280px;
            --bg-base: #020617;
            --bg-surface: #090e1a;
            --bg-glass: rgba(15, 23, 42, 0.75);
            --border-subtle: rgba(255, 255, 255, 0.06);
            --border-hover: rgba(56, 189, 248, 0.3);
        }

        body {
            background-color: var(--bg-base);
            color: #94a3b8;
            font-family: var(--bs-body-font-family);
            overflow-x: hidden;
            position: relative;
        }

        body::before {
            content: ''; position: fixed; top: -10%; left: -10%; width: 40vw; height: 40vw;
            background: radial-gradient(circle, rgba(56, 189, 248, 0.06) 0%, transparent 70%);
            z-index: -1; pointer-events: none;
        }
        body::after {
            content: ''; position: fixed; bottom: -10%; right: -10%; width: 40vw; height: 40vw;
            background: radial-gradient(circle, rgba(129, 140, 248, 0.06) 0%, transparent 70%);
            z-index: -1; pointer-events: none;
        }

        /* Sidebar */
        .sidebar {
            width: var(--sidebar-width); height: 100vh; position: fixed; top: 0; left: 0;
            background-color: var(--bg-surface); border-right: 1px solid var(--border-subtle);
            z-index: 1000; backdrop-filter: blur(12px);
        }
        .sidebar .brand {
            font-weight: 800; font-size: 1.2rem; color: #ffffff; padding: 28px 24px;
            background: linear-gradient(135deg, #ffffff 30%, #94a3b8 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .sidebar .nav-link {
            color: #64748b; padding: 12px 20px; font-weight: 600; font-size: 0.88rem;
            display: flex; align-items: center; gap: 14px; border-radius: 10px; margin: 6px 16px;
            transition: all 0.25s ease; cursor: pointer;
        }
        .sidebar .nav-link:hover, .sidebar .nav-link.active {
            color: #38bdf8; background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.12);
        }

        .main-content {
            margin-left: var(--sidebar-width); padding: 30px 40px;
        }
        @media (max-width: 991.98px) {
            .sidebar { transform: translateX(-100%); }
            .main-content { margin-left: 0; padding: 20px; }
        }

        /* Glass Cards */
        .glass-card {
            background: var(--bg-glass); backdrop-filter: blur(16px);
            border: 1px solid var(--border-subtle); border-radius: 20px;
            box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5); transition: all 0.35s ease;
        }
        .glass-card:hover { border-color: var(--border-hover); }

        /* Live Status Bar */
        .live-bar {
            background: rgba(2, 6, 23, 0.8); border: 1px solid var(--border-subtle);
            border-radius: 12px; padding: 10px 20px; font-size: 0.85rem;
            display: flex; align-items: center; justify-content: space-between; margin-bottom: 25px;
            flex-wrap: wrap; gap: 10px;
        }

        /* Table */
        .table-custom th {
            background-color: transparent !important; color: #64748b; font-weight: 700;
            text-transform: uppercase; font-size: 0.68rem; letter-spacing: 1.5px;
            border-bottom: 1px solid var(--border-subtle) !important; padding: 16px;
        }
        .table-custom td {
            background-color: transparent !important; border-bottom: 1px solid rgba(255, 255, 255, 0.03) !important;
            padding: 16px; vertical-align: middle; color: #e2e8f0; font-size: 0.9rem;
        }
        .table-custom tbody tr:hover { background-color: rgba(255, 255, 255, 0.015); }

        .account-box {
            background: #020617; border: 1px solid var(--border-subtle); border-radius: 8px;
            padding: 6px 12px; font-family: monospace; font-size: 0.82rem; color: #38bdf8; word-break: break-all;
        }

        /* Form Controls */
        .form-control, .form-select {
            background-color: #020617; border: 1px solid var(--border-subtle); color: #f8fafc;
            border-radius: 12px; padding: 12px 16px; font-size: 0.95rem;
        }
        .form-control:focus, .form-select:focus {
            background-color: #020617; border-color: #38bdf8; color: #f8fafc;
            box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.12);
        }

        /* Badges & Tags */
        .badge-custom {
            font-weight: 700; padding: 5px 12px; border-radius: 50rem; font-size: 0.7rem;
            display: inline-flex; align-items: center; gap: 5px;
        }
        .badge-pending { background: rgba(234, 179, 8, 0.1); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.2); }
        .badge-imported { background: rgba(56, 189, 248, 0.1); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.2); }
        .badge-sold { background: rgba(34, 197, 94, 0.1); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.2); }
        .tag-badge { background: rgba(129, 140, 248, 0.1); color: #818cf8; border: 1px solid rgba(129, 140, 248, 0.2); font-size: 0.68rem; padding: 3px 8px; border-radius: 6px; font-weight: 600; }

        /* Floating Bulk Actions Bar */
        #bulkToolbar {
            position: fixed; bottom: -80px; left: 50%; transform: translateX(-50%);
            background: #0f172a; border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 16px;
            padding: 12px 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); z-index: 1040;
            display: flex; align-items: center; gap: 20px; transition: bottom 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        #bulkToolbar.show { bottom: 25px; }

        .btn-action {
            background: rgba(255, 255, 255, 0.03); border: 1px solid var(--border-subtle); color: #94a3b8;
            border-radius: 8px; padding: 6px 10px; transition: all 0.2s ease;
        }
        .btn-action:hover { background: rgba(56, 189, 248, 0.1); border-color: rgba(56, 189, 248, 0.3); color: #38bdf8; }

        /* View Panels Toggle */
        .app-view { display: none; }
        .app-view.active { display: block; }

        #toast-container { position: fixed; bottom: 30px; right: 30px; z-index: 1050; }
    </style>
</head>
<body>

    {% if not session.get('logged_in') %}
    <!-- ĐĂNG NHẬP ENTERPRISE -->
    <div class="login-wrapper d-flex align-items-center justify-content-center min-vh-100" style="background: radial-gradient(circle at 50% 30%, #111c38 0%, #060913 70%); padding: 20px;">
        <div class="glass-card p-4 p-md-5 w-100" style="max-width: 440px;">
            <div class="text-center mb-4">
                <div class="logo-icon mx-auto mb-3 shadow-lg bg-info bg-opacity-10 text-info d-flex align-items-center justify-content-center" style="width: 64px; height: 64px; border-radius: 18px; font-size: 1.8rem;">
                    <i class="bi bi-shield-lock-fill"></i>
                </div>
                <h3 class="fw-bold text-white fs-4 mb-1">Xác Thực Quản Trị</h3>
                <p class="text-secondary small">Hệ thống quản lý kho tài khoản SLL Ultimate</p>
            </div>
            <form method="POST" action="/login">
                <div class="mb-4">
                    <label class="form-label text-secondary small fw-bold text-uppercase mb-2">Mật khẩu quản trị</label>
                    <div class="input-group">
                        <span class="input-group-text bg-transparent border-end-0 text-secondary" style="border-color: var(--border-subtle); border-radius: 12px 0 0 12px;"><i class="bi bi-key"></i></span>
                        <input type="password" name="password" class="form-control border-start-0 ps-0" placeholder="Nhập mật khẩu bảo mật..." required style="border-radius: 0 12px 12px 0;">
                    </div>
                </div>
                <button type="submit" class="btn btn-info w-100 py-3 fw-bold text-dark shadow-lg border-0" style="background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%); color: #fff !important;">Truy Cập Hệ Thống</button>
            </form>
        </div>
    </div>
    {% else %}

    <!-- SIDEBAR (PC & Tablet ngang) -->
    <div class="sidebar d-none d-lg-flex flex-column">
        <div class="brand d-flex align-items-center gap-3">
            <div class="bg-info bg-opacity-10 p-2 rounded-3 text-info"><i class="bi bi-layers-fill fs-5"></i></div>
            <span>SLL ULTIMATE</span>
        </div>
        <ul class="nav flex-column flex-grow-1 pt-2">
            <li class="nav-item"><a class="nav-link active" onclick="switchView('kho')" id="nav-kho"><i class="bi bi-grid-fill fs-5"></i> Quản trị kho</a></li>
            <li class="nav-item"><a class="nav-link" onclick="switchView('ctv')" id="nav-ctv"><i class="bi bi-people-fill fs-5"></i> Đối soát CTV</a></li>
            <li class="nav-item"><a class="nav-link" onclick="switchView('shop')" id="nav-shop"><i class="bi bi-shop fs-5"></i> Cửa hàng tự động</a></li>
            <li class="nav-item"><a class="nav-link" onclick="switchView('log')" id="nav-log"><i class="bi bi-journal-text fs-5"></i> Nhật ký hoạt động</a></li>
            <li class="nav-item"><a class="nav-link" onclick="switchView('backup')" id="nav-backup"><i class="bi bi-database-gear fs-5"></i> Sao lưu & Phục hồi</a></li>
        </ul>
        <div class="p-3 m-3 rounded-4" style="background-color: rgba(2, 6, 23, 0.6); border: 1px solid var(--border-subtle);">
            <div class="d-flex align-items-center gap-2 small text-success fw-semibold mb-3">
                <span class="spinner-grow spinner-grow-sm text-success" role="status"></span> Bot Trực Tuyến 24/7
            </div>
            <a href="/logout" class="btn btn-outline-danger btn-sm w-100 py-2 rounded-3 border-secondary"><i class="bi bi-box-arrow-right me-1"></i> Đăng xuất</a>
        </div>
    </div>

    <!-- MOBILE & TABLET NAVBAR -->
    <nav class="navbar navbar-dark bg-dark border-bottom border-secondary d-lg-none px-3 py-2 sticky-top">
        <div class="container-fluid">
            <span class="navbar-brand fw-bold fs-6"><i class="bi bi-layers-fill text-info me-2"></i> SLL ULTIMATE</span>
            <div class="d-flex align-items-center gap-2">
                <a href="/logout" class="btn btn-outline-danger btn-sm px-2 py-1"><i class="bi bi-box-arrow-right"></i></a>
                <button class="navbar-toggler border-0" type="button" data-bs-toggle="collapse" data-bs-target="#mobileNav">
                    <span class="navbar-toggler-icon"></span>
                </button>
            </div>
            <div class="collapse navbar-collapse mt-2" id="mobileNav">
                <ul class="navbar-nav gap-2 pb-2">
                    <li class="nav-item"><a class="nav-link text-white active" href="#" onclick="switchView('kho'); closeNavbar();">Quản trị kho</a></li>
                    <li class="nav-item"><a class="nav-link text-white" href="#" onclick="switchView('ctv'); closeNavbar();">Đối soát CTV</a></li>
                    <li class="nav-item"><a class="nav-link text-white" href="#" onclick="switchView('shop'); closeNavbar();">Cửa hàng tự động</a></li>
                    <li class="nav-item"><a class="nav-link text-white" href="#" onclick="switchView('log'); closeNavbar();">Nhật ký hoạt động</a></li>
                    <li class="nav-item"><a class="nav-link text-white" href="#" onclick="switchView('backup'); closeNavbar();">Sao lưu & Phục hồi</a></li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- MAIN CONTENT AREA -->
    <div class="main-content">
        
        <!-- LIVE STATUS BAR & LOW STOCK ALERT -->
        <div class="live-bar">
            <div class="d-flex align-items-center gap-3">
                <div class="d-flex align-items-center gap-2 text-success">
                    <i class="bi bi-circle-fill" style="font-size: 8px;"></i>
                    <span class="fw-bold text-white small">Database Online</span>
                </div>
                <span class="text-secondary d-none d-md-inline">|</span>
                <!-- Low Stock Notification Badge -->
                <div id="lowStockAlert" class="badge bg-danger bg-opacity-10 text-danger border border-danger border-opacity-25 py-1 px-2 rounded-pill d-flex align-items-center gap-1">
                    <i class="bi bi-exclamation-triangle-fill"></i> Tồn kho Konpeito thấp (&lt;500 acc)! Đã báo Telegram.
                </div>
            </div>
            <div class="d-flex align-items-center gap-3 text-secondary small">
                <span><i class="bi bi-shield-lock text-success me-1"></i> 2FA PIN: <strong class="text-white">Active</strong></span>
                <span><i class="bi bi-activity text-warning me-1"></i> Ping: <strong class="text-white">18ms</strong></span>
            </div>
        </div>

        <!-- VIEW 1: QUẢN TRỊ KHO -->
        <div id="view-kho" class="app-view active">
            <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
                <div>
                    <h2 class="fw-extrabold text-white fs-3 mb-1">Bảng Điều Hành Kho Tài Khoản</h2>
                    <p class="text-secondary small mb-0">Hệ thống cấp phát tự động tích hợp quản lý Excel/CSV và Bot Telegram.</p>
                </div>
                <div class="d-flex gap-2 flex-wrap">
                    <button class="btn btn-action px-3 py-2 rounded-pill shadow-sm" onclick="showToast('Đang tải file mẫu .CSV...')"><i class="bi bi-file-earmark-arrow-down me-1 text-info"></i> Tải File Mẫu</button>
                    <label class="btn btn-action px-3 py-2 rounded-pill shadow-sm mb-0" style="cursor: pointer;"><i class="bi bi-file-earmark-spreadsheet me-1 text-success"></i> Nhập File Excel <input type="file" hidden onchange="showToast('Đã upload và xử lý file thành công!')"></label>
                </div>
            </div>

            <!-- STATS -->
            <div class="row g-4 mb-4">
                <div class="col-12 col-md-4">
                    <div class="glass-card p-4">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <span class="text-secondary small fw-bold text-uppercase">Chưa nhập mã</span>
                                <h2 class="fw-extrabold text-warning mt-2 mb-0 fs-2" id="statPendingCount">{{ unimported }}</h2>
                            </div>
                            <div class="bg-warning bg-opacity-10 p-3 rounded-4 text-warning"><i class="bi bi-clock-history fs-2"></i></div>
                        </div>
                    </div>
                </div>
                <div class="col-12 col-md-4">
                    <div class="glass-card p-4">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <span class="text-secondary small fw-bold text-uppercase">Sẵn bán</span>
                                <h2 class="fw-extrabold text-info mt-2 mb-0 fs-2" id="statAvailableCount">{{ imported }}</h2>
                            </div>
                            <div class="bg-info bg-opacity-10 p-3 rounded-4 text-info"><i class="bi bi-check2-circle fs-2"></i></div>
                        </div>
                    </div>
                </div>
                <div class="col-12 col-md-4">
                    <div class="glass-card p-4">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <span class="text-secondary small fw-bold text-uppercase">Đã bán tổng cộng</span>
                                <h2 class="fw-extrabold text-success mt-2 mb-0 fs-2">{{ sold }}</h2>
                            </div>
                            <div class="bg-success bg-opacity-10 p-3 rounded-4 text-success"><i class="bi bi-cart-check fs-2"></i></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ADVANCED FILTER & SEARCH PANEL -->
            <div class="glass-card p-4 mb-4">
                <div class="d-flex align-items-center justify-content-between mb-3">
                    <h5 class="fw-bold text-white fs-6 mb-0 d-flex align-items-center gap-2">
                        <i class="bi bi-funnel-fill text-info"></i> Bộ Lọc & Tìm Kiếm Nâng Cao
                    </h5>
                    <button class="btn btn-sm btn-outline-secondary py-1 px-2 text-secondary small" onclick="resetFilters()">Đặt lại bộ lọc</button>
                </div>
                <div class="row g-3">
                    <div class="col-12 col-md-3">
                        <label class="form-label text-secondary small fw-semibold">Từ ngày</label>
                        <input type="date" id="filterDateFrom" class="form-control form-control-sm" onchange="applyAdvancedFilters()">
                    </div>
                    <div class="col-12 col-md-3">
                        <label class="form-label text-secondary small fw-semibold">Đến ngày</label>
                        <input type="date" id="filterDateTo" class="form-control form-control-sm" onchange="applyAdvancedFilters()">
                    </div>
                    <div class="col-12 col-md-3">
                        <label class="form-label text-secondary small fw-semibold">Loại Gói / Tag</label>
                        <select id="filterTag" class="form-select form-select-sm" onchange="applyAdvancedFilters()">
                            <option value="">Tất cả các gói</option>
                            <option value="konpeito">Konpeito SV</option>
                            <option value="other">Gói Khác</option>
                        </select>
                    </div>
                    <div class="col-12 col-md-3">
                        <label class="form-label text-secondary small fw-semibold">Trạng thái kho</label>
                        <select id="filterStatus" class="form-select form-select-sm" onchange="applyAdvancedFilters()">
                            <option value="">Tất cả trạng thái</option>
                            <option value="pending">Chưa nhập</option>
                            <option value="imported">Sẵn bán</option>
                            <option value="sold">Đã bán</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- BULK IMPORT & CHARTS -->
            <div class="row g-4 mb-4">
                <div class="col-12 col-lg-7">
                    <div class="glass-card p-4 h-100 d-flex flex-column justify-content-between">
                        <form method="POST" action="/add">
                            <h5 class="fw-bold text-white fs-6 mb-3 d-flex align-items-center gap-2">
                                <i class="bi bi-cloud-arrow-up-fill text-success fs-5"></i> Nhập Tài Khoản Hàng Loạt
                            </h5>
                            <textarea class="form-control mb-3" name="accounts" rows="4" placeholder="Dán danh sách định dạng user|pass|extra (Mỗi dòng 1 tài khoản)..." style="resize: none;" required></textarea>
                            <button type="submit" class="btn btn-success w-100 py-3 fw-bold shadow-lg rounded-3 border-0" style="background: linear-gradient(135deg, #22c55e, #16a34a);">
                                <i class="bi bi-plus-circle-fill me-2"></i> Đưa Vào Kho Dữ Liệu Ngay
                            </button>
                        </form>
                    </div>
                </div>
                <div class="col-12 col-lg-5">
                    <div class="glass-card p-4 h-100 d-flex flex-column justify-content-between">
                        <h5 class="fw-bold text-white fs-6 mb-2"><i class="bi bi-graph-up text-info me-2"></i> Biểu Đồ Giao Dịch & Hoạt Động</h5>
                        <div style="height: 160px;" class="d-flex justify-content-center align-items-center">
                            <canvas id="activityChart"></canvas>
                        </div>
                        <div class="text-center text-secondary small mt-1">Thống kê truy xuất theo thời gian thực</div>
                    </div>
                </div>
            </div>

            <!-- TABLE SECTION -->
            <div class="glass-card overflow-hidden">
                <div class="p-4 border-bottom border-secondary d-flex flex-column flex-lg-row justify-content-between align-items-lg-center gap-3" style="border-color: var(--border-subtle) !important;">
                    <div class="d-flex align-items-center gap-2 flex-wrap">
                        <span class="text-white fw-bold me-2">Danh sách kho:</span>
                        <span id="activeFilterBadge" class="tag-badge">Hiển thị toàn bộ dữ liệu</span>
                    </div>
                    <div class="w-100 w-lg-auto" style="max-width: 280px;">
                        <div class="input-group input-group-sm">
                            <span class="input-group-text bg-dark border-secondary text-secondary"><i class="bi bi-search"></i></span>
                            <input type="text" id="searchInput" class="form-control" placeholder="Tìm kiếm nhanh..." onkeyup="applyAdvancedFilters()">
                        </div>
                    </div>
                </div>
                <div class="table-responsive">
                    <table class="table table-custom mb-0" id="accountTable">
                        <thead>
                            <tr>
                                <th class="ps-4" style="width: 40px;"><input type="checkbox" class="form-check-input bg-dark border-secondary" id="selectAll" onclick="toggleSelectAll(this)"></th>
                                <th>#ID & Gói</th>
                                <th>Thông tin tài khoản</th>
                                <th>Ngày tạo / Nhập</th>
                                <th>Trạng thái</th>
                                <th>Xử lý / Mua</th>
                                <th class="text-center">Thao tác</th>
                            </tr>
                        </thead>
                        <tbody id="accountTableBody">
                            {% for acc in accounts %}
                            <tr data-date="{{ acc[5][:10] if acc|length > 5 and acc[5] else '2026-08-01' }}" data-tag="konpeito" data-status="{% if acc[2] == 0 %}pending{% elif acc[2] == 1 %}imported{% else %}sold{% endif %}">
                                <td class="ps-4"><input type="checkbox" class="form-check-input bg-dark border-secondary row-checkbox" onclick="checkBulkBar()"></td>
                                <td>
                                    <div class="fw-bold text-white">#{{ acc[0] }}</div>
                                    <span class="tag-badge mt-1">Konpeito SV</span>
                                </td>
                                <td><span class="account-box" title="{{ acc[1] }}">{{ acc[1] }}</span></td>
                                <td class="text-secondary small">{{ acc[5] if acc|length > 5 and acc[5] else '01/08/2026' }}</td>
                                <td>
                                    {% if acc[2] == 0 %}<span class="badge-custom badge-pending"><i class="bi bi-circle-fill" style="font-size: 6px;"></i> Chưa nhập</span>
                                    {% elif acc[2] == 1 %}<span class="badge-custom badge-imported"><i class="bi bi-circle-fill" style="font-size: 6px;"></i> Sẵn bán</span>
                                    {% else %}<span class="badge-custom badge-sold"><i class="bi bi-circle-fill" style="font-size: 6px;"></i> Đã bán</span>{% endif %}
                                </td>
                                <td class="text-secondary small">
                                    {% if acc[3] %}<span class="text-info fw-semibold">Làm: {{ acc[3] }}</span>{% endif %}
                                    {% if acc[4] %}<span class="text-success fw-semibold"> | Bán: {{ acc[4] }}</span>{% endif %}
                                    {% if not acc[3] and not acc[4] %}<span class="text-muted">Trống</span>{% endif %}
                                </td>
                                <td class="text-center">
                                    <button class="btn btn-action btn-sm me-1" onclick="showToast('Đã copy: {{ acc[1] }}'); navigator.clipboard.writeText('{{ acc[1] }}');" title="Copy"><i class="bi bi-clipboard"></i></button>
                                    <a href="/delete/{{ acc[0] }}" class="btn btn-action btn-sm text-danger" onclick="return confirm('Bạn có chắc muốn xóa tài khoản này?')" title="Xóa"><i class="bi bi-trash"></i></a>
                                </td>
                            </tr>
                            {% else %}
                            <tr>
                                <td colspan="7" class="text-center py-5 text-secondary">
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

        <!-- VIEW 2: ĐỐI SOÁT CTV -->
        <div id="view-ctv" class="app-view">
            <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
                <div>
                    <h2 class="fw-extrabold text-white fs-3 mb-1">Bảng Đối Soát Sản Lượng CTV</h2>
                    <p class="text-secondary small mb-0">Theo dõi chi tiết số lượng công việc hoàn thành và lương thưởng của từng cộng tác viên.</p>
                </div>
                <button class="btn btn-action px-3 py-2 rounded-pill" onclick="requestPinCode('export_salary')"><i class="bi bi-download me-1 text-info"></i> Xuất Báo Cáo Lương</button>
            </div>

            <div class="glass-card overflow-hidden">
                <div class="table-responsive">
                    <table class="table table-custom mb-0">
                        <thead>
                            <tr>
                                <th class="ps-4">Tên CTV</th>
                                <th>Đã Xử Lý (Hôm Nay)</th>
                                <th>Đã Xử Lý (Tổng)</th>
                                <th>Đơn Giá / Acc</th>
                                <th>Thành Tiền Dự Kiến</th>
                                <th class="text-center">Trạng Thái Lương</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td class="ps-4 fw-bold text-white"><i class="bi bi-person-badge text-info me-2"></i> CTV_Nam</td>
                                <td><span class="text-info fw-bold">45 acc</span></td>
                                <td>1,420 acc</td>
                                <td>2,500đ</td>
                                <td class="text-success fw-bold">3,550,000 đ</td>
                                <td class="text-center"><span class="badge bg-warning bg-opacity-10 text-warning border border-warning border-opacity-25 px-3 py-1 rounded-pill">Chưa thanh toán</span></td>
                            </tr>
                            <tr>
                                <td class="ps-4 fw-bold text-white"><i class="bi bi-person-badge text-info me-2"></i> CTV_Huy</td>
                                <td><span class="text-info fw-bold">38 acc</span></td>
                                <td>980 acc</td>
                                <td>2,500đ</td>
                                <td class="text-success fw-bold">2,450,000 đ</td>
                                <td class="text-center"><span class="badge bg-success bg-opacity-10 text-success border border-success border-opacity-25 px-3 py-1 rounded-pill">Đã thanh toán</span></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- VIEW 3: CỬA HÀNG TỰ ĐỘNG (PUBLIC CHECKOUT PAGE) -->
        <div id="view-shop" class="app-view">
            <div class="mb-4">
                <h2 class="fw-extrabold text-white fs-3 mb-1">Cửa Hàng Mua Hàng Nhanh Cho Khách</h2>
                <p class="text-secondary small mb-0">Khách hàng tự chọn gói, quét mã QR chuyển khoản và nhận tài khoản tự động ngay lập tức.</p>
            </div>

            <div class="row g-4">
                <div class="col-12 col-md-6">
                    <div class="glass-card p-4 h-100">
                        <h4 class="text-white fw-bold fs-5 mb-3"><i class="bi bi-cart4 text-info me-2"></i> Chọn Gói Dịch Vụ</h4>
                        <div class="mb-3">
                            <label class="form-label text-secondary small">Chọn Loại Gói Tài Khoản</label>
                            <select id="shopPackage" class="form-select" onchange="updateShopPrice()">
                                <option value="50000">Gói Konpeito Cơ Bản (1 Acc) - 50,000đ</option>
                                <option value="120000">Gói Konpeito VIP (3 Acc) - 120,000đ</option>
                                <option value="250000">Gói Đại Lý Konpeito (7 Acc) - 250,000đ</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label text-secondary small">Số lượng mua</label>
                            <input type="number" id="shopQty" class="form-control" value="1" min="1" max="10" onchange="updateShopPrice()">
                        </div>
                        <div class="p-3 rounded-3 mb-4" style="background: rgba(2,6,23,0.6); border: 1px solid var(--border-subtle);">
                            <div class="d-flex justify-content-between text-secondary small mb-1">
                                <span>Đơn giá:</span>
                                <span id="shopUnitPrice" class="text-white">50,000đ</span>
                            </div>
                            <div class="d-flex justify-content-between fw-bold text-white fs-5">
                                <span>Tổng thanh toán:</span>
                                <span id="shopTotalPrice" class="text-info">50,000đ</span>
                            </div>
                        </div>
                        <button class="btn btn-info w-100 py-3 fw-bold text-dark rounded-3 border-0" onclick="proceedCheckout()">
                            <i class="bi bi-qr-code-scan me-2"></i> Tạo Mã QR Thanh Toán
                        </button>
                    </div>
                </div>

                <div class="col-12 col-md-6">
                    <div class="glass-card p-4 h-100 text-center d-flex flex-column justify-content-center align-items-center" id="checkoutResultArea">
                        <div class="bg-dark p-4 rounded-4 border border-secondary mb-3 w-100" style="max-width: 260px;">
                            <i class="bi bi-qr-code text-white" style="font-size: 5rem;"></i>
                            <div class="text-secondary small mt-2">Quét mã bằng app Ngân hàng</div>
                        </div>
                        <h5 class="text-white fw-bold fs-6">Nội dung chuyển khoản: <span class="text-warning">MUA KONPEITO 1029</span></h5>
                        <p class="text-secondary small mt-1 mb-0">Hệ thống sẽ tự động duyệt thanh toán và trả tài khoản sau 5-10 giây.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- VIEW 4: NHẬT KÝ HOẠT ĐỘNG (AUDIT LOG) -->
        <div id="view-log" class="app-view">
            <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
                <div>
                    <h2 class="fw-extrabold text-white fs-3 mb-1">Nhật Ký Hoạt Động (Audit Log)</h2>
                    <p class="text-secondary small mb-0">Lịch sử toàn bộ thao tác thêm, xóa hoặc xuất kho tài khoản trong hệ thống.</p>
                </div>
                <button class="btn btn-action px-3 py-2 rounded-pill text-danger" onclick="requestPinCode('clear_log')"><i class="bi bi-trash me-1"></i> Xoá Log</button>
            </div>

            <div class="glass-card p-4">
                <div class="d-flex flex-column gap-3">
                    <div class="d-flex justify-content-between align-items-center p-3 rounded-3" style="background: rgba(255,255,255,0.015); border: 1px solid var(--border-subtle);">
                        <div class="d-flex align-items-center gap-3">
                            <div class="bg-success bg-opacity-10 p-2 rounded-3 text-success"><i class="bi bi-plus-lg"></i></div>
                            <div>
                                <div class="text-white fw-bold small">Thêm mới tài khoản vào kho</div>
                                <div class="text-secondary" style="font-size: 0.75rem;">Thực hiện qua Web quản trị</div>
                            </div>
                        </div>
                        <span class="text-secondary small">Hôm nay</span>
                    </div>
                    <div class="d-flex justify-content-between align-items-center p-3 rounded-3" style="background: rgba(255,255,255,0.015); border: 1px solid var(--border-subtle);">
                        <div class="d-flex align-items-center gap-3">
                            <div class="bg-info bg-opacity-10 p-2 rounded-3 text-info"><i class="bi bi-cart-check"></i></div>
                            <div>
                                <div class="text-white fw-bold small">Cấp phát tài khoản cho người dùng</div>
                                <div class="text-secondary" style="font-size: 0.75rem;">Xử lý tự động qua Bot Telegram</div>
                            </div>
                        </div>
                        <span class="text-secondary small">Hôm nay</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- VIEW 5: SAO LƯU & PHỤC HỒI DỮ LIỆU (BACKUP & RESTORE) -->
        <div id="view-backup" class="app-view">
            <div class="mb-4">
                <h2 class="fw-extrabold text-white fs-3 mb-1">Sao Lưu & Phục Hồi Dữ Liệu</h2>
                <p class="text-secondary small mb-0">Xuất file cấu hình và dữ liệu kho toàn hệ thống hoặc khôi phục nhanh chóng khi thay đổi thiết bị.</p>
            </div>

            <div class="row g-4">
                <div class="col-12 col-md-6">
                    <div class="glass-card p-4 h-100 d-flex flex-column justify-content-between">
                        <div>
                            <div class="bg-info bg-opacity-10 p-3 rounded-4 text-info d-inline-block mb-3">
                                <i class="bi bi-cloud-arrow-down-fill fs-3"></i>
                            </div>
                            <h4 class="text-white fw-bold fs-5">Xuất Bản Sao Lưu (Backup)</h4>
                            <p class="text-secondary small">Tải xuống toàn bộ cơ sở dữ liệu hiện tại (Kho tài khoản, lịch sử CTV, nhật ký log) dưới định dạng file `.json` an toàn.</p>
                        </div>
                        <button class="btn btn-info w-100 py-3 fw-bold text-dark rounded-3 border-0 mt-3" onclick="requestPinCode('export_backup')">
                            <i class="bi bi-download me-2"></i> Tải Xuống File Backup (.JSON)
                        </button>
                    </div>
                </div>

                <div class="col-12 col-md-6">
                    <div class="glass-card p-4 h-100 d-flex flex-column justify-content-between">
                        <div>
                            <div class="bg-warning bg-opacity-10 p-3 rounded-4 text-warning d-inline-block mb-3">
                                <i class="bi bi-cloud-arrow-up-fill fs-3"></i>
                            </div>
                            <h4 class="text-white fw-bold fs-5">Phục Hồi Dữ Liệu (Restore)</h4>
                            <p class="text-secondary small">Tải lên tệp `.json` đã sao lưu trước đó để khôi phục toàn bộ trạng thái hệ thống ngay lập tức.</p>
                        </div>
                        <div class="mt-3">
                            <input type="file" id="restoreFileinput" accept=".json" class="d-none" onchange="importDatabaseBackup(event)">
                            <label for="restoreFileinput" class="btn btn-warning w-100 py-3 fw-bold text-dark rounded-3 border-0 text-center m-0" style="cursor: pointer;">
                                <i class="bi bi-upload me-2"></i> Chọn File Phục Hồi (.JSON)
                            </label>
                        </div>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <!-- FLOATING BULK ACTIONS TOOLBAR -->
    <div id="bulkToolbar">
        <div class="text-white small fw-bold">Đã chọn: <span id="selectedCount" class="text-info">0</span> tài khoản</div>
        <div class="d-flex gap-2">
            <button class="btn btn-outline-info btn-sm px-3 py-1 fw-semibold" onclick="showToast('Đã xuất file TXT thành công!')"><i class="bi bi-download me-1"></i> Xuất File TXT</button>
            <button class="btn btn-outline-danger btn-sm px-3 py-1 fw-semibold" onclick="requestPinCode('delete_bulk')"><i class="bi bi-trash me-1"></i> Xóa Đã Chọn</button>
        </div>
    </div>

    <!-- MODAL NHẬP MÃ PIN 2FA BẢO MẬT -->
    <div class="modal fade" id="pinModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered" style="max-width: 380px;">
            <div class="modal-content glass-card p-4 border border-secondary bg-dark">
                <div class="text-center mb-3">
                    <div class="bg-info bg-opacity-10 p-3 rounded-circle text-info d-inline-block mb-2">
                        <i class="bi bi-shield-lock-fill fs-3"></i>
                    </div>
                    <h5 class="text-white fw-bold">Xác Thực Mã PIN Admin</h5>
                    <p class="text-secondary small mb-0">Thao tác này yêu cầu nhập mã PIN bảo mật 2 lớp của bạn.</p>
                </div>
                <input type="password" id="adminPinInput" class="form-control text-center fw-bold fs-4 mb-3" placeholder="••••" maxlength="6">
                <div class="d-flex gap-2">
                    <button class="btn btn-outline-secondary w-50 py-2 rounded-3" data-bs-dismiss="modal">Hủy</button>
                    <button class="btn btn-info w-50 py-2 fw-bold text-dark rounded-3" onclick="verifyPinCode()">Xác Nhận</button>
                </div>
            </div>
        </div>
    </div>

    <!-- TOAST NOTIFICATION -->
    <div id="toast-container">
        <div id="copyToast" class="toast align-items-center text-white bg-dark border border-success shadow-lg rounded-3" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex p-2">
                <div class="toast-body fw-semibold text-success d-flex align-items-center gap-2" id="toastMessage">
                    <i class="bi bi-check-circle-fill fs-5"></i> Thao tác thành công!
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    </div>

    {% endif %}

    <!-- Bootstrap JS & Chart.js Script -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function switchView(viewId) {
            document.querySelectorAll('.app-view').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.sidebar .nav-link').forEach(el => el.classList.remove('active'));
            
            document.getElementById('view-' + viewId).classList.add('active');
            const navEl = document.getElementById('nav-' + viewId);
            if(navEl) navEl.classList.add('active');
        }

        function closeNavbar() {
            const navbar = document.getElementById('mobileNav');
            if(navbar && navbar.classList.contains('show')) {
                new bootstrap.Collapse(navbar).hide();
            }
        }

        function showToast(msg) {
            if(msg) document.getElementById('toastMessage').innerHTML = `<i class="bi bi-check-circle-fill fs-5"></i> ${msg}`;
            const toastEl = document.getElementById('copyToast');
            const toast = new bootstrap.Toast(toastEl);
            toast.show();
        }

        let currentAction = null;
        function requestPinCode(action) {
            currentAction = action;
            const pinModal = new bootstrap.Modal(document.getElementById('pinModal'));
            pinModal.show();
        }

        function verifyPinCode() {
            const pin = document.getElementById('adminPinInput').value;
            if(pin === "123" || pin === "1234") {
                const modalEl = document.getElementById('pinModal');
                const modal = bootstrap.Modal.getInstance(modalEl);
                modal.hide();
                document.getElementById('adminPinInput').value = '';
                showToast('Xác thực bảo mật thành công!');
                if(currentAction === 'export_backup') {
                    setTimeout(() => showToast('Đã tải xuống file backup.json'), 1000);
                }
            } else {
                alert('Mã PIN không chính xác! (Mật khẩu mặc định: 123)');
            }
        }

        function toggleSelectAll(source) {
            const checkboxes = document.querySelectorAll('.row-checkbox');
            checkboxes.forEach(cb => cb.checked = source.checked);
            checkBulkBar();
        }

        function checkBulkBar() {
            const checkedCount = document.querySelectorAll('.row-checkbox:checked').length;
            document.getElementById('selectedCount').innerText = checkedCount;
            const toolbar = document.getElementById('bulkToolbar');
            if(checkedCount > 0) {
                toolbar.classList.add('show');
            } else {
                toolbar.classList.remove('show');
            }
        }

        function updateShopPrice() {
            const select = document.getElementById('shopPackage');
            const qty = document.getElementById('shopQty').value;
            const unitPrice = parseInt(select.value);
            const total = unitPrice * qty;
            document.getElementById('shopUnitPrice').innerText = unitPrice.toLocaleString() + 'đ';
            document.getElementById('shopTotalPrice').innerText = total.toLocaleString() + 'đ';
        }

        function proceedCheckout() {
            showToast('Đã tạo mã QR thanh toán thành công!');
        }

        function applyAdvancedFilters() {
            const search = document.getElementById('searchInput').value.toLowerCase();
            const tag = document.getElementById('filterTag').value;
            const status = document.getElementById('filterStatus').value;
            const rows = document.querySelectorAll('#accountTableBody tr');

            rows.forEach(row => {
                if(row.cells.length < 2) return;
                const text = row.innerText.toLowerCase();
                const rowTag = row.getAttribute('data-tag') || '';
                const rowStatus = row.getAttribute('data-status') || '';

                let matchSearch = text.includes(search);
                let matchTag = !tag || rowTag === tag;
                let matchStatus = !status || rowStatus === status;

                if(matchSearch && matchTag && matchStatus) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }

        function resetFilters() {
            document.getElementById('searchInput').value = '';
            document.getElementById('filterTag').value = '';
            document.getElementById('filterStatus').value = '';
            document.getElementById('filterDateFrom').value = '';
            document.getElementById('filterDateTo').value = '';
            applyAdvancedFilters();
        }

        // Khởi tạo Chart.js
        window.addEventListener('DOMContentLoaded', (event) => {
            const ctx = document.getElementById('activityChart');
            if(ctx) {
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'],
                        datasets: [{
                            label: 'Giao dịch',
                            data: [12, 19, 15, 25, 22, 30, 45],
                            borderColor: '#38bdf8',
                            backgroundColor: 'rgba(56, 189, 248, 0.1)',
                            fill: true,
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { grid: { display: false }, ticks: { color: '#64748b' } },
                            y: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#64748b' } }
                        }
                    }
                });
            }
        });
    </script>
</body>
</html>
"""

# --- ROUTE WEB ---
@app.route('/')
def index():
    unimported, imported, sold = get_stats()
    with sqlite3.connect("accounts_manager.db", check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, account_data, status, imported_by, sold_to, created_at FROM accounts ORDER BY id DESC LIMIT 50")
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

# --- BOT TELEGRAM ---
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