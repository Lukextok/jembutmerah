import sys
import subprocess
import os

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

import asyncio
import logging
import json
import re
import random
import smtplib
import imaplib
import email
import dns.resolver
import socket
from email.message import EmailMessage
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

USER_DATA_FILE = "users_db.json"
GMAIL_FILE = "gmail.txt"

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
        users[user_id] = {
            "accounts": [],
            "targets": ["support@support.whatsapp.com", "smb@support.whatsapp.com"],
            "active_target": "support@support.whatsapp.com"
        }
    pasukan_gmail = users[user_id].get("accounts", [])
    if os.path.exists(GMAIL_FILE):
        try:
            with open(GMAIL_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split()
                        if len(parts) >= 2:
                            gmail_addr = parts[0].strip()
                            gmail_pass = "".join(parts[1:]).strip().replace(" ", "")
                            if not any(acc['gmail'] == gmail_addr for acc in pasukan_gmail):
                                pasukan_gmail.append({"gmail": gmail_addr, "pass": gmail_pass})
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

def get_main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📞 Input Number"), KeyboardButton("📁 Get File")],
        [KeyboardButton("👤 My Profile"), KeyboardButton("👥 Leaderboard")],
        [KeyboardButton("⚙️ Setting"), KeyboardButton("❌ Cancel")]
    ], resize_keyboard=True)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("❌ Cancel")]], resize_keyboard=True)

def get_settings_inline_kb(profile):
    buttons = []
    buttons.append([InlineKeyboardButton("── 🎯 TARGET EMAIL TUJUAN ──", callback_data="none")])
    for index, tgt in enumerate(profile.get("targets", [])):
        icon = "🟢" if tgt == profile.get("active_target", "") else "⚪"
        buttons.append([InlineKeyboardButton(f"{icon} {tgt}", callback_data=f"set_active_{index}")])
    buttons.append([InlineKeyboardButton("➕ Tambah Target Email", callback_data="add_new_target")])
    buttons.append([InlineKeyboardButton("── 📨 EMAIL PENGIRIM (SENDER) ──", callback_data="none")])
    if not profile.get("accounts", []):
        buttons.append([InlineKeyboardButton("❌ Belum ada email pengirim", callback_data="none")])
    else:
        for idx, acc in enumerate(profile.get("accounts", [])):
            buttons.append([InlineKeyboardButton(f"▫️ {acc['gmail']}", callback_data="none"), InlineKeyboardButton("🗑️", callback_data=f"del_sender_{idx}")])
    buttons.append([InlineKeyboardButton("➕ Tambah Email Pengirim", callback_data="add_new_sender")])
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_states[user_id] = None
    profile = get_user_profile(user_id)
    acc_list = profile.get("accounts", [])
    display = "\n".join([f"▫️ {a['gmail']}" for a in acc_list]) if acc_list else "_Belum ada akun_"
    text = f"📨 *BOT BYPASS FIX RED (MONITOR MODE)*\n━━━━━━━━━━━━━━━━━━\nTotal Email Pengirim: *{len(acc_list)}*\n🎯 Target: `{profile.get('active_target')}`\n\n{display}\n\n⚡ *Status:* Deteksi balasan otomatis & Auto-Delete Jejak Aktif!"
    await update.message.reply_text(text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

async def handle_button_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_clicked = update.message.text
    user_id = str(update.effective_user.id)
    profile = get_user_profile(user_id)
    user_states[user_id] = None
    if text_clicked == "📞 Input Number":
        await update.message.reply_text("🚀 Silakan kirim daftar nomor target atau **kirim file .txt**.")
    elif text_clicked == "⚙️ Setting":
        await update.message.reply_text("⚙️ *PENGATURAN & PANEL KONTROL*", reply_markup=get_settings_inline_kb(profile), parse_mode='Markdown')
    elif text_clicked == "❌ Cancel":
        if user_id in running_tasks and not running_tasks[user_id].done():
            running_tasks[user_id].cancel()
            await update.message.reply_text("🛑 *PROSES DIBATALKAN PENGGUNA!*", reply_markup=get_main_keyboard(), parse_mode='Markdown')
        else:
            await update.message.reply_text("ℹ️ Tidak ada proses yang berjalan.", reply_markup=get_main_keyboard())

async def inline_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    profile = get_user_profile(user_id)
    await query.answer()
    if query.data.startswith("set_active_"):
        index = int(query.data.replace("set_active_", ""))
        if 0 <= index < len(profile["targets"]):
            profile["active_target"] = profile["targets"][index]
            update_user_profile(user_id, profile)
            await query.edit_message_reply_markup(reply_markup=get_settings_inline_kb(profile))
            await query.message.reply_text(f"🎯 Target diubah ke: `{profile['active_target']}`", parse_mode='Markdown')
    elif query.data == "add_new_sender":
        user_states[user_id] = "WAITING_SENDER"
        await query.message.reply_text("📝 Silakan kirim data akun dengan format:\n`Gmail` `SandiAplikasi`", parse_mode='Markdown')

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    state = user_states.get(user_id)
    profile = get_user_profile(user_id)
    text_input = update.message.text.strip()
    
    if state == "WAITING_SENDER":
        user_states[user_id] = None
        parts = text_input.split(maxsplit=1)
        if len(parts) >= 2:
            gmail, app_pass = parts[0].strip(), parts[1].replace(" ", "").strip()
            if not any(acc['gmail'] == gmail for acc in profile["accounts"]):
                profile["accounts"].append({"gmail": gmail, "pass": app_pass})
                update_user_profile(user_id, profile)
            await update.message.reply_text(f"✅ Email Pengirim `{gmail}` sukses disimpan!", reply_markup=get_main_keyboard())
        return

    numbers = [n.strip() for n in text_input.splitlines() if is_valid_number(n.strip())]
    if numbers:
        if user_id in running_tasks and not running_tasks[user_id].done():
            await update.message.reply_text("⚠️ Proses lama masih berjalan.")
            return
        await update.message.reply_text("⏳ Memulai antrean pengiriman & pemantauan...", reply_markup=get_cancel_keyboard())
        task = asyncio.create_task(execute_parallel_queue(update, numbers, profile))
        running_tasks[user_id] = task

# 🕵️‍♂️ --- ENGINE UTAMA: CEK BALASAN & HAPUS JEJAK ---
def tunggu_dan_bersihkan_balasan(acc, target_email, subyek_cari):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", timeout=20)
        mail.login(acc['gmail'], acc['pass'])
        
        # Loop memantau inbox selama maksimal 3 menit (180 detik)
        for _ in range(36): 
            mail.select("inbox")
            # Cari email masuk dari target
            status, search_data = mail.search(None, f'FROM "{target_email}" UNSEEN')
            
            for msg_id in search_data[0].split():
                status, msg_data = mail.fetch(msg_id, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject = str(msg['subject'])
                        
                        # Pastikan balasan tersebut merujuk pada nomor/subyek yang kita kirim
                        if subyek_cari in subject or "Re:" in subject:
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                        break
                            else:
                                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                            
                            # 🗑️ EKSEKUSI HAPUS PERMANEN (Inbox Balasan & Sent Mail Kita)
                            mail.store(msg_id, '+FLAGS', '\\Deleted')
                            
                            # Pindah ke folder Sent Mail untuk hapus pesan keluar kita
                            try:
                                mail.select('"[Gmail]/Sent Mail"')
                                _, sent_data = mail.search(None, f'TO "{target_email}"')
                                for s_id in sent_data[0].split():
                                    mail.store(s_id, '+FLAGS', '\\Deleted')
                            except: pass
                            
                            mail.expunge()
                            mail.logout()
                            return body[:1500] # Kembalikan potongan teks balasan
            
            # Cek setiap 5 detik sekali
            import time
            time.sleep(5)
            
        # Jika timeout hapus saja data sent mail lama
        try:
            mail.select('"[Gmail]/Sent Mail"')
            _, sent_data = mail.search(None, f'TO "{target_email}"')
            for s_id in sent_data[0].split(): mail.store(s_id, '+FLAGS', '\\Deleted')
            mail.expunge()
        except: pass
        mail.logout()
    except Exception as e:
        print(f"IMAP Error: {e}")
    return None

async def kirim_email_tunggal(num, acc, target_email, pesan_pilihan, status_msg):
    subyek = f"Fix {num}"
    isi_pesan = pesan_pilihan.replace("{nomor}", num)
    
    def _execute_smtp():
        smtp = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
        smtp.starttls() 
        smtp.login(acc['gmail'], acc['pass'])
        msg = EmailMessage()
        msg['Subject'] = subyek
        msg['From'] = acc['gmail']
        msg['To'] = target_email
        msg.set_content(isi_pesan)
        smtp.send_message(msg)
        smtp.quit()
        
    try:
        await asyncio.to_thread(_execute_smtp)
        await status_msg.edit_text(
            f"🚀 *EMAIL TERKIRIM*\nNo: `{num}`\n🎯 Target: `{target_email}`\n\n📝 *Isi Pesan:*\n`{isi_pesan}`\n\n🕵️‍♂️ _Sedang menunggu balasan masuk dari target... (Auto-Delete Standby)_", 
            parse_mode='Markdown'
        )
        
        # Pemicu engine pemantau inbox asinkron
        balasan = await asyncio.to_thread(tunggu_dan_bersihkan_balasan, acc, target_email, subyek)
        
        if balasan:
            await status_msg.reply_text(
                f"📥 *BALASAN DITERIMA & JEJAK DIHAPUS!*\nNo Target: `{num}`\nFrom: `{target_email}`\n\n💬 *Isi Balasan:*\n`{balasan.strip()}`\n\n✨ _Status: Pesan masuk & keluar sukses dihapus permanen dari server!_",
                parse_mode='Markdown'
            )
        else:
            await status_msg.edit_text(f"🏁 *SELESAI*\nNo: `{num}`\n⚠️ Tidak ada balasan dalam 3 menit. Jejak pengiriman tetap dibersihkan.", parse_mode='Markdown')
            
    except Exception as e:
        await status_msg.edit_text(f"❌ Error (`{acc['gmail'][:5]}`): {e}")

async def email_worker(queue, acc, target_email, update):
    templates = [
        "Здравствуйте, команда поддержки WhatsApp.Я обращаюсь к вам с серьёзной проблемой, связанной с моим номером WhatsApp. Каждый раз, когда я пытаюсь зарегистрироваться или masuk к номер {nomor}, muncul pesan error Login not available.",
        "Құрметті WhatsAppЖеке нөмірімді тіркеу кезінде мәселе туындады, {nomor} нөмірімді тіркеуге көмектесіңіз."
    ]
    while not queue.empty():
        try: num = queue.get_nowait()
        except: break
        pesan_pilihan = random.choice(templates)
        status_msg = await update.message.reply_text(f"📨 *SLOT ACTIVE*\nNo: `{num}`\nVia: `{acc['gmail'][:5]}***` ⏳ Mengirim...")
        await kirim_email_tunggal(num, acc, target_email, pesan_pilihan, status_msg)
        queue.task_done()
        await asyncio.sleep(2)

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
            await update.message.reply_text("🏁 *SEMUA PROSES ANTREAN SELESAI!*", reply_markup=get_main_keyboard(), parse_mode='Markdown')
    except asyncio.CancelledError:
        for w in workers: w.cancel()
    finally:
        if user_id in running_tasks: del running_tasks[user_id]

async def process_file_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    profile = get_user_profile(user_id)
    if not profile.get("accounts"): return
    document = update.message.document
    if not document.file_name.endswith('.txt'): return
    tg_file = await context.bot.get_file(document.file_id)
    file_bytes = await tg_file.download_as_bytearray()
    numbers = [n.strip() for n in file_bytes.decode('utf-8').splitlines() if is_valid_number(n.strip())]
    if numbers:
        await update.message.reply_text(f"📋 Terdeteksi *{len(numbers)} nomor* dari file. Memulai antrean...", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')
        task = asyncio.create_task(execute_parallel_queue(update, numbers, profile))
        running_tasks[user_id] = task

async def main_async():
    TOKEN = "8756606308:AAGPX-6rn7SPYEyG_DarddcbcN8W9UYSaGQ"
    app = Application.builder().token(TOKEN).connect_timeout(60).read_timeout(60).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(inline_callback_handler))
    app.add_handler(MessageHandler(filters.Text(["📞 Input Number", "📁 Get File", "👤 My Profile", "👥 Leaderboard", "⚙️ Setting", "❌ Cancel"]), handle_button_clicks))
    app.add_handler(MessageHandler(filters.Document.ALL, process_file_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    
    print("🟢 Bot Monitor & Auto-Delete Aktif 24/7!")
    sys.stdout.flush()
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    stop_signal = asyncio.Event()
    await stop_signal.wait()

if __name__ == "__main__":
    asyncio.run(main_async())
      
