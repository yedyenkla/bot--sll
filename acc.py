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
ADMIN_IDS = [8455715505]  # Thay bằng Telegram ID của Admin
ADMIN_PASSWORD = "Bxt223344@"  # Mật khẩu đăng nhập trang web quản lý
SECRET_KEY = "Bxt223344@"     # Khóa mã hóa session web

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


# --- GIAO DIỆN WEB QUẢN LÝ KHO (FLASK) ---
app = Flask(__name__)
app.secret_key = SECRET_KEY

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Quản Lý Kho SLL</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; }
        .container { max-width: 900px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h2 { color: #333; }
        textarea { width: 100%; height: 150px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; font-family: monospace; }
        button { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-size: 16px; margin-top: 10px; }
        button:hover { background: #0056b3; }
        .stats { display: flex; gap: 20px; margin-bottom: 20px; }
        .stat-box { flex: 1; background: #e9ecef; padding: 15px; border-radius: 6px; text-align: center; }
        .logout { float: right; color: red; text-decoration: none; }
    </style>
</head>
<body>
<div class="container">
    {% if not session.get('logged_in') %}
        <h2>🔑 Đăng Nhập Quản Trị Kho</h2>
        <form method="POST" action="/login">
            <input type="password" name="password" placeholder="Nhập mật khẩu quản trị" required style="padding: 10px; width: 60%; margin-right: 10px;">
            <button type="submit">Đăng Nhập</button>
        </form>
    {% else %}
        <a href="/logout" class="logout">Đăng xuất</a>
        <h2>📦 HỆ THỐNG QUẢN LÝ KHO TÀI KHOẢN SLL</h2>
        
        <div class="stats">
            <div class="stat-box"><h3>{{ unimported }}</h3><p>Chưa nhập mã</p></div>
            <div class="stat-box"><h3>{{ imported }}</h3><p>Sẵn bán</p></div>
            <div class="stat-box"><h3>{{ sold }}</h3><p>Đã bán</p></div>
        </div>

        <h3>➕ Thêm Tài Khoản Hàng Loạt (Mỗi dòng 1 tài khoản)</h3>
        <form method="POST" action="/add">
            <textarea name="accounts" placeholder="user|pass hoặc thông tin tài khoản..." required></textarea><br>
            <button type="submit">Thêm Vào Kho</button>
        </form>
    {% endif %}
</div>
</body>
</html>
"""

@app.route('/')
def index():
    unimported, imported, sold = get_stats()
    return render_template_string(HTML_TEMPLATE, unimported=unimported, imported=imported, sold=sold)

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
    count = 0
    for line in lines:
        acc = line.strip()
        if acc:
            try:
                cursor.execute("INSERT INTO accounts (account_data, status) VALUES (?, 0)", (acc,))
                count += 1
            except sqlite3.IntegrityError:
                pass 
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

def run_web():
    # Tự động nhận port từ Render (hoặc chạy port 10000 nếu chạy ở máy local)
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

async def daily_backup_job(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("accounts_manager.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT account_data FROM accounts WHERE status = 0")
    unimported = cursor.fetchall()
    cursor.execute("SELECT account_data FROM accounts WHERE status = 1")
    imported_unprocessed = cursor.fetchall()
    conn.close()

    file_path = "backup_kho_acc.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("=== ACC CHƯA NHẬP MÃ ===\n")
        for row in unimported:
            f.write(row[0] + "\n")
        f.write("\n=== ACC ĐÃ NHẬP MÃ (CHƯA BÁN) ===\n")
        for row in imported_unprocessed:
            f.write(row[0] + "\n")

    for admin_id in ADMIN_IDS:
        try:
            with open(file_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=admin_id,
                    document=f,
                    filename=f"backup_{datetime.now().strftime('%Y-%m-%d')}.txt",
                    caption="📂 **Báo cáo kho tự động lúc 00:00**",
                    parse_mode="Markdown",
                )
        except Exception as e:
            print(f"Lỗi gửi file backup: {e}")
    if os.path.exists(file_path):
        os.remove(file_path)

def main():
    keep_alive()  # Khởi chạy trang web quản lý chạy ngầm cùng bot
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    job_queue = application.job_queue
    vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
    job_queue.run_daily(
        daily_backup_job,
        time=datetime.now(vn_tz).replace(hour=0, minute=0, second=0, microsecond=0).time(),
        days=(0, 1, 2, 3, 4, 5, 6),
    )

    print("🤖 Bot và Trang Web Quản Lý đang chạy đồng thời...")
    application.run_polling()

if __name__ == "__main__":
    main()