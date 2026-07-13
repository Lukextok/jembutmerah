import os
import sys
import logging
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==========================================
# 1. KONFIGURASI LOGGING & PATH FILE
# ==========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN_FILE = "token.txt"

# ==========================================
# 2. SERVER DUMMY PORT 7860
# ==========================================
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

# ==========================================
# 3. FUNGSI HANDLER BOT TELEGRAM
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["📞 Input Number", "📁 Get File"],
        ["👤 My Profile", "👥 Leaderboard"],
        ["⚙️ Setting", "❌ Cancel"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "👋 Selamat datang di Bot Mode Antrean Slot Email!\nSilakan pilih menu di bawah ini:",
        reply_markup=reply_markup
    )

async def handle_button_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📞 Input Number":
        await update.message.reply_text("Silakan masukkan nomor target antrean kamu:")
    elif text == "📁 Get File":
        await update.message.reply_text("Silakan kirimkan dokumen berkas/file data (.txt) kamu:")
    elif text == "👤 My Profile":
        await update.message.reply_text(f"👤 Profile: {update.effective_user.first_name}\nID: `{update.effective_user.id}`")
    elif text == "👥 Leaderboard":
        await update.message.reply_text("📊 Klasemen Antrean saat ini masih kosong.")
    elif text == "⚙️ Setting":
        await update.message.reply_text("⚙️ Pengaturan sistem bot aktif.")
    elif text == "❌ Cancel":
        await update.message.reply_text("Aksi dibatalkan. Menunggu instruksi selanjutnya.")

async def inline_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text=f"Pilihan dikonfirmasi: {query.data}")

async def process_file_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ File diterima. Sedang memproses dan menyortir data antrean...")

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    await update.message.reply_text(f"✅ Data diterima: `{user_input}`. Sedang dimasukkan ke antrean database.")

# ==========================================
# 4. ENGINE RUNNER UTAMA
# ==========================================
if __name__ == "__main__":
    TOKEN = ""
    
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f: 
            TOKEN = f.read().strip()
    
    if not TOKEN or TOKEN == "":
        TOKEN = "8756606308:AAGPX-6rn7SPYEyG_DarddcbcN8W9UYSaGQ"
        print("🔑 Token berhasil dimuat dari sistem.")

    app = Application.builder().token(TOKEN).connect_timeout(60).read_timeout(60).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(inline_callback_handler))
    app.add_handler(MessageHandler(filters.Text(["📞 Input Number", "📁 Get File", "👤 My Profile", "👥 Leaderboard", "⚙️ Setting", "❌ Cancel"]), handle_button_clicks))
    app.add_handler(MessageHandler(filters.Document.ALL, process_file_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    
    print("🤖 Bot Mode Antrean Slot Email Aktif... Menunggu kiriman data dari Telegram.")
    app.run_polling()
