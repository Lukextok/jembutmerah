import sys
import subprocess
import os

# 🔥 AUTO-INSTALLER AKTIF & AMAN DI ROOT SERVER
def install_missing_packages():
    required_packages = {
        "telegram": "python-telegram-bot",
        "dns": "dnspython",
        "requests": "requests"
    }
    for module, package in required_packages.items():
        try:
            __import__(module)
        except ImportError:
            print(f"📦 [SISTEM] Modul '{module}' tidak ditemukan. Menginstal {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_missing_packages()

# ==========================================
# LOAD UTAMA SETELAH AUTO-INSTALL
# ==========================================
import asyncio
import logging
import json
import re
import random
import smtplib
import imaplib
import dns.resolver
import socket
import threading
import requests
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
from email.message import EmailMessage
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 📂 JALUR FILE DIKUNCI DI LUAR FOLDER (ROOT)
USER_DATA_FILE = "users_db.json"
GMAIL_FILE = "gmail.txt"

# 🔑 --- KONFIGURASI AKSES REPOSITORY GITHUB ---
GITHUB_TOKEN = "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" 
GITHUB_REPO = "Lukextok/jembutmerah"
GITHUB_BRANCH = "main"

running_tasks = {}
user_states = {}
CUSTOM_DNS = ["8.8.8.8", "1.1.1.1", "8.8.4.4"]

def custom_getaddrinfo(*args, **kwargs):
    host = args[0]
    port = args[1]
    if isinstance(host, bytes):
        try: host = host.decode('utf-8')
        except: return org_getaddrinfo(*args, **kwargs)
    if not host: return org_getaddrinfo(*args, **kwargs)
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', host) or host == "localhost":
        return org_getaddrinfo(host, port, *args[2:], **kwargs)
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = CUSTOM_DNS
        resolver.timeout = 10
        resolver.lifetime = 10
        answers = resolver.resolve(host, 'A')
        ip_address = answers[0].to_text()
        return org_getaddrinfo(ip_address, port, *args[2:], **kwargs)
    except Exception:
        return org_getaddrinfo(host, port, *args[2:], **kwargs)

org_getaddrinfo = socket.getaddrinfo
socket.getaddrinfo = custom_getaddrinfo

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot Active 24/7')
    def log_message(self, format, *args): return

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', 7860), SimpleHTTPRequestHandler).serve_forever(), daemon=True).start()

def push_gmail_to_github(new_gmail, new_pass):
    if not GITHUB_TOKEN or "MASUKKAN" in GITHUB_TOKEN: return False
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GMAIL_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    current_content = ""
    sha = None
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        sha = data["sha"]
        current_content = base64.b64decode(data["content"]).decode("utf-8")
    new_line = f"{new_gmail} {new_pass}"
    if new_line in current_content: return True
    updated_content = current_content.strip() + f"\n{new_line}\n"
    payload = {
        "message": f"🤖 Bot Auto-Save: Menambahkan {new_gmail}",
        "content": base64.b64encode(updated_content.encode("utf-8")).decode("utf-8"),
        "branch": GITHUB_BRANCH
    }
    if sha: payload["sha"] = sha
    res_put = requests.put(url, headers=headers, json=payload)
    return res_put.status_code in [200, 201]

def delete_gmail_from_github(gmail_to_delete):
    if not GITHUB_TOKEN or "MASUKKAN" in GITHUB_TOKEN: return False
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GMAIL_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    if res.status_code != 200: return False
    data = res.json()
    sha = data["sha"]
    current_content = base64.b64decode(data["content"]).decode("utf-8")
    lines = current_content.splitlines()
    updated_lines = [line for line in lines if not line.startswith(gmail_to_delete)]
    updated_content = "\n".join(updated_lines) + "\n"
    payload = {
        "message": f"🤖 Bot Auto-Delete: Menghapus {gmail_to_delete}",
        "content": base64.b64encode(updated_content.encode("utf-8")).decode("utf-8"),
        "sha": sha,
        "branch": GITHUB_BRANCH
    }
    res_put = requests.put(url, headers=headers, json=payload)
    return res_put.status_code == 200

def load_users():
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r') as f:
                return json.load(f)
        except: return {}
    return {}

def save_user(data):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_user_profile(user_id):
    users = load_users()
    if user_id not in users or not isinstance(users[user_id], dict):
        users[user_id] = {
            "accounts": [],
            "targets": ["support@support.whatsapp.com", "smb@support.whatsapp.com"],
            "active_target": "support@support.whatsapp.com"
        }
    pasukan_gmail = []
    if os.path.exists(GMAIL_FILE):
        try:
            with open(GMAIL_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split()
                        if len(parts) >= 2:
                            pasukan_gmail.append({"gmail": parts[0].strip(), "pass": "".join(parts[1:]).strip()})
        except: pass
    users[user_id]["accounts"] = pasukan_gmail
    save_user(users)
    return users[user_id]

def update_user_profile(user_id, profile):
    users = load_users()
    users[user_id] = profile
    save_user(users)

def is_valid_number(text):
    cleaned = text.strip().replace(" ", "").replace("-", "")
    return bool(re.match(r'^\+[1-9]\d{6,14}$', cleaned))

def clean_gmail_logs(gmail_user, gmail_pass, targets):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", timeout=20)
        mail.login(gmail_user, gmail_pass)
        for folder in ['"[Gmail]/Sent Mail"', "inbox"]:
            try:
                mail.select(folder)
                for target in targets:
                    criteria = f'TO "{target}"' if "Sent" in folder else f'FROM "{target}"'
                    typ, data = mail.search(None, criteria)
                    for num in data[0].split():
                        mail.store(num, '+FLAGS', '\\Deleted')
            except: continue
        mail.expunge()
        mail.logout()
    except: pass

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("📞 Input Number"), KeyboardButton("📁 Get File")],
        [KeyboardButton("👤 My Profile"), KeyboardButton("👥 Leaderboard")],
        [KeyboardButton("⚙️ Setting"), KeyboardButton("❌ Cancel")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("❌ Cancel")]], resize_keyboard=True)

def get_settings_inline_kb(profile):
    buttons = []
    buttons.append([InlineKeyboardButton("── 🎯 TARGET EMAIL TUJUAN ──", callback_data="none")])
    targets = profile.get("targets", [])
    active = profile.get("active_target", "")
    for index, tgt in enumerate(targets):
        icon = "🟢" if tgt == active else "⚪"
        buttons.append([InlineKeyboardButton(f"{icon} {tgt}", callback_data=f"set_active_{index}")])
    buttons.append([InlineKeyboardButton("➕ Tambah Target Email", callback_data="add_new_target")])
    buttons.append([InlineKeyboardButton("── 📨 EMAIL PENGIRIM (SENDER) ──", callback_data="none")])
    accounts = profile.get("accounts", [])
    if not accounts:
        buttons.append([InlineKeyboardButton("❌ Belum ada email pengirim", callback_data="none")])
    else:
        for idx, acc in enumerate(accounts):
            buttons.append([InlineKeyboardButton(f"▫️ {acc['gmail']}", callback_data="none"), InlineKeyboardButton("🗑️", callback_data=f"del_sender_{idx}")])
    buttons.append([InlineKeyboardButton("➕ Tambah Email Pengirim", callback_data="add_new_sender")])
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_states[user_id] = None
    profile = get_user_profile(user_id)
    acc_list = profile.get("accounts", [])
    active_target = profile.get("active_target", "_Belum Dipilih_")
    display = "\n".join([f"▫️ {a['gmail']}" for a in acc_list]) if acc_list else "_Belum ada akun_"
    text = (
        "📨 *BOT BYPASS FIX RED (CLOUD QUEUE)*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"Total Email Pengirim: *{len(acc_list)}*\n"
        f"🎯 Target Tujuan Saat Ini: `{active_target}`\n\n"
        f"{display}\n\n"
        "⚡ *Sistem:* Auto-save ke Cloud Github Aktif! Akun permanen anti-hilang."
    )
    await update.message.reply_text(text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

async def handle_button_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_clicked = update.message.text
    user_id = str(update.effective_user.id)
    profile = get_user_profile(user_id)
    user_states[user_id] = None
    if text_clicked == "📞 Input Number":
        await update.message.reply_text("🚀 Silakan kirim daftar nomor target atau **kirim file .txt**.\n⚠️ *Ingat: Nomor wajib menggunakan tanda + di depannya!*")
    elif text_clicked == "📁 Get File":
        await update.message.reply_text("📂 Fitur unduh file laporan sedang dipersiapkan.")
    elif text_clicked == "👤 My Profile":
        acc_list = profile.get("accounts", [])
        await update.message.reply_text(f"👤 *PROFIL ANDA*\nID: `{user_id}`\nJumlah Email Terdaftar: *{len(acc_list)}* akun.\nTarget Aktif: `{profile.get('active_target')}`", parse_mode='Markdown')
    elif text_clicked == "👥 Leaderboard":
        await update.message.reply_text("🏆 Fitur peringkat pengguna aktif.")
    elif text_clicked == "⚙️ Setting":
        text_settings = f"⚙️ *PENGATURAN*\n🎯 Target Saat Ini: `{profile.get('active_target')}`\n📨 Total Pengirim: *{len(profile.get('accounts', []))}*"
        await update.message.reply_text(text_settings, reply_markup=get_settings_inline_kb(profile), parse_mode='Markdown')
    elif text_clicked == "❌ Cancel":
        if user_id in running_tasks and not running_tasks[user_id].done():
            running_tasks[user_id].cancel()
            await update.message.reply_text("🛑 *PROSES ANTREAN DIBATALKAN PENGGUNA!*", reply_markup=get_main_keyboard(), parse_mode='Markdown')
        else:
            await update.message.reply_text("ℹ️ Tidak ada proses pengiriman yang sedang berjalan.", reply_markup=get_main_keyboard())

async def inline_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    profile = get_user_profile(user_id)
    await query.answer()
    if query.data == "none": return
    elif query.data.startswith("set_active_"):
        index = int(query.data.replace("set_active_", ""))
        if 0 <= index < len(profile["targets"]):
            profile["active_target"] = profile["targets"][index]
            update_user_profile(user_id, profile)
            await query.edit_message_reply_markup(reply_markup=get_settings_inline_kb(profile))
            await query.message.reply_text(f"🎯 Target diubah ke: `{profile['active_target']}`", parse_mode='Markdown')
    elif query.data.startswith("del_sender_"):
        index = int(query.data.replace("del_sender_", ""))
        accounts = profile.get("accounts", [])
        if 0 <= index < len(accounts):
            removed = accounts.pop(index)
            await query.message.reply_text(f"⏳ Sedang menghapus `{removed['gmail']}`...")
            success = await asyncio.to_thread(delete_gmail_from_github, removed['gmail'])
            if success:
                profile["accounts"] = accounts
                update_user_profile(user_id, profile)
                await query.edit_message_reply_markup(reply_markup=get_settings_inline_kb(profile))
                await query.message.reply_text(f"🗑️ Email `{removed['gmail']}` sukses terhapus.")
    elif query.data == "add_new_target":
        user_states[user_id] = "WAITING_TARGET"
        await query.message.reply_text("📝 Silakan langsung ketik alamat email target baru kamu:", parse_mode='Markdown')
    elif query.data == "add_new_sender":
        user_states[user_id] = "WAITING_SENDER"
        await query.message.reply_text("📝 Silakan kirim data dengan format:\n`Gmail` `SandiAplikasi` (Dipisah Spasi)", parse_mode='Markdown')

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    state = user_states.get(user_id)
    profile = get_user_profile(user_id)
    text_input = update.message.text.strip()
    if state == "WAITING_SENDER":
        user_states[user_id] = None
        parts = text_input.split()
        if len(parts) >= 2:
            gmail, app_pass = parts[0].strip(), "".join(parts[1:]).strip()
            status_wait = await update.message.reply_text("⏳ Sinkronisasi Commit ke GitHub...")
            success = await asyncio.to_thread(push_gmail_to_github, gmail, app_pass)
            await status_wait.delete()
            if success:
                if not any(acc['gmail'] == gmail for acc in profile["accounts"]):
                    profile["accounts"].append({"gmail": gmail, "pass": app_pass})
                    update_user_profile(user_id, profile)
                await update.message.reply_text(f"✅ Email Pengirim `{gmail}` Berhasil disimpan Permanen!", reply_markup=get_main_keyboard())
        return
    elif state == "WAITING_TARGET":
        user_states[user_id] = None
        if "@" in text_input:
            if text_input not in profile["targets"]: profile["targets"].append(text_input)
            profile["active_target"] = text_input
            update_user_profile(user_id, profile)
            await update.message.reply_text(f"🎯 Target diaktifkan:\n`{text_input}`", reply_markup=get_main_keyboard(), parse_mode='Markdown')
        return
    numbers = [n.strip() for n in text_input.splitlines() if is_valid_number(n.strip())]
    if numbers:
        if user_id in running_tasks and not running_tasks[user_id].done():
            await update.message.reply_text("⚠️ Proses lama masih berjalan.")
            return
        await update.message.reply_text("⏳ Memulai pengiriman antrean...", reply_markup=get_cancel_keyboard())
        task = asyncio.create_task(execute_parallel_queue(update, numbers, profile))
        running_tasks[user_id] = task

async def kirim_email_tunggal(num, acc, target_email, pesan_pilihan, status_msg):
    def _execute_smtp():
        smtp = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
        smtp.starttls() 
        smtp.login(acc['gmail'], acc['pass'])
        msg = EmailMessage()
        msg['Subject'] = f"Fix {num}"
        msg['From'] = acc['gmail']
        msg['To'] = target_email
        msg.set_content(pesan_pilihan.replace("{nomor}", num))
        smtp.send_message(msg)
        smtp.quit()
    try:
        await asyncio.to_thread(_execute_smtp)
        await asyncio.sleep(4)
        await asyncio.to_thread(clean_gmail_logs, acc['gmail'], acc['pass'], [target_email])
        await status_msg.edit_text(f"🏁 *SELESAI BERSAMAAN*\nNo: `{num}`\n✅ DONE & CLEANED", parse_mode='Markdown')
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}")

async def email_worker(queue, acc, target_email, update):
    templates = [
        "Здравствуйте, команда поддержки WhatsApp.Я обращаюсь к вам с серьёзной проблемой, связанной с моим номером WhatsApp. Каждый раз, когда я пытаюсь зарегистрироваться или masuk к номер {nomor}, muncul pesan error Login not available.",
        "Құрметті WhatsAppЖеке нөмірімді тіркеу кезінде мәселе туындады, {nomor} нөмірімді тіркеуге көмектесіңіз."
    ]
    while not queue.empty():
        try: num = queue.get_nowait()
        except: break
        pesan_pilihan = random.choice(templates)
        status_msg = await update.message.reply_text(f"📨 *SLOT ACTIVE*\nNo: `{num}`\nVia: `{acc['gmail'][:5]}***`")
        await kirim_email_tunggal(num, acc, target_email, pesan_pilihan, status_msg)
        queue.task_done()
        await asyncio.sleep(1)

async def execute_parallel_queue(update: Update, numbers, profile):
    user_id = str(update.effective_user.id)
    acc_list = profile.get("accounts", [])
    target_email = profile.get("active_target", "support@support.whatsapp.com")
    queue = asyncio.Queue()
    for num in numbers: await queue.put(num)
    workers = [asyncio.create_task(email_worker(queue, acc, target_email, update)) for acc in acc_list]
    try:
        if workers:
            await asyncio.gather(*workers)
            await update.message.reply_text("🏁 *SEMUA ANTREAN NOMOR SELESAI DIPROSES!*", reply_markup=get_main_keyboard(), parse_mode='Markdown')
    except asyncio.CancelledError:
        for w in workers: w.cancel()
    finally:
        if user_id in running_tasks: del running_tasks[user_id]

async def process_file_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_states[user_id] = None
    if user_id in running_tasks and not running_tasks[user_id].done(): return
    profile = get_user_profile(user_id)
    if not profile.get("accounts"): return
    document = update.message.document
    if not document.file_name.endswith('.txt'): return
    status_loading = await update.message.reply_text("📥 _Mengunduh file teks..._", parse_mode='Markdown')
    try:
        tg_file = await context.bot.get_file(document.file_id)
        file_bytes = await tg_file.download_as_bytearray()
        numbers = [n.strip() for n in file_bytes.decode('utf-8').splitlines() if is_valid_number(n.strip())]
        await status_loading.delete()
        if not numbers: return
        await update.message.reply_text(f"📋 Terdeteksi *{len(numbers)} nomor*.")
        task = asyncio.create_task(execute_parallel_queue(update, numbers, profile))
        running_tasks[user_id] = task
    except Exception as e:
        await status_loading.edit_text(f"❌ Gagal: {e}")

async def main_async():
    TOKEN = "8756606308:AAGPX-6rn7SPYEyG_DarddcbcN8W9UYSaGQ"
    app = Application.builder().token(TOKEN).connect_timeout(60).read_timeout(60).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(inline_callback_handler))
    app.add_handler(MessageHandler(filters.Text(["📞 Input Number", "📁 Get File", "👤 My Profile", "👥 Leaderboard", "⚙️ Setting", "❌ Cancel"]), handle_button_clicks))
    app.add_handler(MessageHandler(filters.Document.ALL, process_file_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    
    print("🟢 Bot Cloud Queue Mode Berhasil Terkunci & Aktif 24/7!")
    sys.stdout.flush()
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    stop_signal = asyncio.Event()
    await stop_signal.wait()

def main():
    try: asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit): print("🛑 Bot dimatikan.")

if __name__ == "__main__":
    main()
    
