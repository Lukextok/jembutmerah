import os
import sys
import logging
import asyncio
import json
import re
import random
import smtplib
import imaplib
import dns.resolver
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from email.message import EmailMessage
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ==========================================
# 1. KONFIGURASI LOGGING & PATH FILE
# ==========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

USER_DATA_FILE = "users_db.json"
TOKEN_FILE = "token.txt"

running_tasks = {}
user_states = {}

# 🔌 --- SETTING DNS INTERNAL ---
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

# 🌐 --- SERVER DUMMY PORT 7860 ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot Active 24/7')
    def log_message(self, format, *args):
        return

def run_dummy_server():
    try:
        server_address = ('0.0.0.0', 7860)
        httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
        print("🌐 Web dummy port 7860 started successfully.")
        httpd.serve_forever()
    except Exception as e:
        print(f"⚠️ Web dummy warning: {e}")

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- DATABASE LOGIC ---
def load_users():
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except: return {}
    return {}

def save_user(data):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_user_profile(user_id):
    users = load_users()
    if user_id not in users or not isinstance(users[user_id], dict):
        # 📨 PONDASI PENGATURAN AWAL OTOMATIS
        users[user_id] = {
            # ⬇️ TULIS DAFTAR PASUKAN GMAIL KAMU DI SINI BIAR PERMANEN AMAN ⬇️
            "accounts": [
                {"gmail": "emailkamu1@gmail.com", "pass": "sandiaplikasi1"},
                {"gmail": "emailkamu2@gmail.com", "pass": "sandiaplikasi2"}
            ],
            "targets": ["support@support.whatsapp.com", "smb@support.whatsapp.com"],
            "active_target": "support@support.whatsapp.com"
        }
        save_user(users)
        
    # BACKUP EXTRA: Memastikan jika data ter-reset tapi fungsi dipanggil, data hardcode tetap disuntikkan
    if not users[user_id].get("accounts"):
        users[user_id]["accounts"] = [
            {"gmail": "emailkamu1@gmail.com", "pass": "sandiaplikasi1"},
            {"gmail": "emailkamu2@gmail.com", "pass": "sandiaplikasi2"}
        ]
        save_user(users)
        
    return users[user_id]

def update_user_profile(user_id, profile):
    users = load_users()
    users[user_id] = profile
    save_user(users)

def is_valid_number(text):
    cleaned = text.strip().replace(" ", "").replace("-", "")
    return bool(re.match(r'^\+[1-9]\d{6,14}$', cleaned))

# --- GMAIL CLEANER (IMAP) ---
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

# --- KEYBOARD MARKUP ---
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
            buttons.append([
                InlineKeyboardButton(f"▫️ {acc['gmail']}", callback_data="none"),
                InlineKeyboardButton("🗑️", callback_data=f"del_sender_{idx}")
            ])
            
    buttons.append([InlineKeyboardButton("➕ Tambah Email Pengirim", callback_data="add_new_sender")])
    return InlineKeyboardMarkup(buttons)

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_states[user_id] = None
    profile = get_user_profile(user_id)
    acc_list = profile.get("accounts", [])
    active_target = profile.get("active_target", "_Belum Dipilih_")
    
    display = "\n".join([f"▫️ {a['gmail']}" for a in acc_list]) if acc_list else "_Belum ada akun_"
    
    text = (
        "📨 *BOT BYPASS FIX RED (QUEUE MODE)*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"Total Email Pengirim: *{len(acc_list)}*\n"
        f"🎯 Target Tujuan Saat Ini: `{active_target}`\n\n"
        f"{display}\n\n"
        "⚡ *Sistem:* 1 Email = 1 Proses Bersamaan (Antrean Otomatis Aktif)."
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
        text_settings = (
            "⚙️ *PENGATURAN & PANEL KONTROL*\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🎯 Target Saat Ini: `{profile.get('active_target')}`\n"
            f"📨 Total Pengirim: *{len(profile.get('accounts', []))}*\n\n"
            "👇 *Gunakan panel menu interaktif di bawah untuk mengelola:* "
        )
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
            profile["accounts"] = accounts
            update_user_profile(user_id, profile)
            await query.edit_message_reply_markup(reply_markup=get_settings_inline_kb(profile))
            await query.message.reply_text(f"🗑️ Email pengirim `{removed['gmail']}` berhasil dihapus.")
    elif query.data == "add_new_target":
        user_states[user_id] = "WAITING_TARGET"
        await query.message.reply_text("📝 Silakan langsung ketik alamat email target baru kamu:", parse_mode='Markdown')
    elif query.data == "add_new_sender":
        user_states[user_id] = "WAITING_SENDER"
        await query.message.reply_text("📝 Silakan langsung kirim data akun pengirim baru dengan format:\n`Gmail` `SandiAplikasi` (Dipisah Spasi)", parse_mode='Markdown')

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    state = user_states.get(user_id)
    profile = get_user_profile(user_id)
    text_input = update.message.text.strip()
    
    if state == "WAITING_SENDER":
        user_states[user_id] = None
        parts = text_input.split()
        if len(parts) >= 2:
            gmail = parts[0].strip()
            app_pass = "".join(parts[1:]).strip()
            profile["accounts"].append({"gmail": gmail, "pass": app_pass})
            update_user_profile(user_id, profile)
            await update.message.reply_text(f"✅ Email Pengirim `{gmail}` disimpan!", reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text("❌ Format salah!", reply_markup=get_main_keyboard())
        return
    elif state == "WAITING_TARGET":
        user_states[user_id] = None
        if "@" in text_input:
            if text_input not in profile["targets"]: profile["targets"].append(text_input)
            profile["active_target"] = text_input
            update_user_profile(user_id, profile)
            await update.message.reply_text(f"🎯 Target diaktifkan:\n`{text_input}`", reply_markup=get_main_keyboard(), parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Tidak valid!", reply_markup=get_main_keyboard())
        return

    numbers = [n.strip() for n in text_input.splitlines() if is_valid_number(n.strip())]
    if numbers:
        if user_id in running_tasks and not running_tasks[user_id].done():
            await update.message.reply_text("⚠️ Proses lama masih berjalan. Tekan `❌ Cancel` dulu.")
            return
        await update.message.reply_text("⏳ Memulai pengiriman antrean... Menu dialihkan ke mode interupsi.", reply_markup=get_cancel_keyboard())
        task = asyncio.create_task(execute_parallel_queue(update, numbers, profile))
        running_tasks[user_id] = task

# --- INDIVIDUAL SMTP CORE ---
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
        await status_msg.edit_text(f"🏁 *SELESAI BERSAMAAN*\nNo: `{num}`\n✅ DONE & CLEANED\nVia: `{acc['gmail'][:5]}***`", parse_mode='Markdown')
    except asyncio.CancelledError:
        await status_msg.edit_text(f"❌ Proses `{num}` Dihentikan paksa.")
        raise
    except Exception as e:
        await status_msg.edit_text(f"❌ Error Jaringan (`{acc['gmail'][:5]}`): {e}")

# 🚀 --- EMAIL SLOT WORKER QUEUE ---
async def email_worker(queue, acc, target_email, update):
    templates = [
        "Здравствуйте, команда поддержки WhatsApp.Я обращаюсь к вам с серьёзной проблемой, связанной с моим номером WhatsApp. Каждый раз, когда я пытаюсь зарегистрироваться или masuk ke nomor {nomor}, muncul pesan error Login not available.",
        "Құрметті WhatsAppЖеке нөмірімді тіркеу кезінде мәселе туындады, {nomor} нөмірімді тіркеуге көмектесіңіз."
    ]
    while not queue.empty():
        try:
            num = queue.get_nowait()
        except asyncio.QueueEmpty:
            break
        
        pesan_pilihan = random.choice(templates)
        status_msg = await update.message.reply_text(
            f"📨 *SLOT ACTIVE*\nNo: `{num}`\n🎯 Target: `{target_email}`\nVia: `{acc['gmail'][:5]}***`\n⏳ Memproses...",
            parse_mode='Markdown'
        )
        
        await kirim_email_tunggal(num, acc, target_email, pesan_pilihan, status_msg)
        queue.task_done()
        await asyncio.sleep(1)

async def execute_parallel_queue(update: Update, numbers, profile):
    user_id = str(update.effective_user.id)
    acc_list = profile.get("accounts", [])
    target_email = profile.get("active_target", "support@support.whatsapp.com")
    
    queue = asyncio.Queue()
    for num in numbers:
        await queue.put(num)
        
    workers = []
    for acc in acc_list:
        worker = asyncio.create_task(email_worker(queue, acc, target_email, update))
        workers.append(worker)
        
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
    if user_id in running_tasks and not running_tasks[user_id].done():
        await update.message.reply_text("⚠️ Proses lama masih berjalan. Tekan `❌ Cancel` dulu.")
        return

    profile = get_user_profile(user_id)
    if not profile.get("accounts"): 
        await update.message.reply_text("⚠️ Pasukan Gmail kosong! Sila edit isi script hardcode dulu.")
        return

    document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Jenis file salah!")
        return

    status_loading = await update.message.reply_text("📥 _Mengunduh file teks..._", parse_mode='Markdown')
    try:
        tg_file = await context.bot.get_file(document.file_id)
        file_bytes = await tg_file.download_as_bytearray()
        file_content = file_bytes.decode('utf-8')
        numbers = [n.strip() for n in file_content.splitlines() if is_valid_number(n.strip())]
        await status_loading.delete()
        
        if not numbers:
            await update.message.reply_text("❌ Tidak ada nomor valid.")
            return

        await update.message.reply_text(f"📋 Terdeteksi *{len(numbers)} nomor* di dalam file.\nMemulai antrean slot...", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')
        task = asyncio.create_task(execute_parallel_queue(update, numbers, profile))
        running_tasks[user_id] = task
    except Exception as e:
        await status_loading.edit_text(f"❌ Gagal: {e}")

# --- MAIN BLOCK ---
if __name__ == "__main__":
    TOKEN = "8756606308:AAGPX-6rn7SPYEyG_DarddcbcN8W9UYSaGQ"
    print("🔑 Token dimuat via hardcode backend.")

    app = Application.builder().token(TOKEN).connect_timeout(60).read_timeout(60).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(inline_callback_handler))
    app.add_handler(MessageHandler(filters.Text(["📞 Input Number", "📁 Get File", "👤 My Profile", "👥 Leaderboard", "⚙️ Setting", "❌ Cancel"]), handle_button_clicks))
    app.add_handler(MessageHandler(filters.Document.ALL, process_file_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    
    print("🤖 Bot Mode Antrean Slot Email Aktif...")
    app.run_polling()
      
