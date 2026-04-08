import os, io, requests, qrcode, pdfplumber, asyncio
from PIL import Image
from deep_translator import GoogleTranslator
from yt_dlp import YoutubeDL
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters, ContextTypes)

TOKEN = os.environ.get("TOKEN")
user_state = {}
reminders = {}
scheduler = AsyncIOScheduler()

# ========== القائمة الرئيسية ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🖼️ إزالة خلفية صورة", callback_data="rembg"),
         InlineKeyboardButton("📄 PDF إلى نص", callback_data="pdf")],
        [InlineKeyboardButton("🔗 اختصار رابط", callback_data="short"),
         InlineKeyboardButton("📷 QR Code", callback_data="qr")],
        [InlineKeyboardButton("🎵 يوتيوب MP3", callback_data="yt"),
         InlineKeyboardButton("🌍 ترجمة نص", callback_data="translate")],
        [InlineKeyboardButton("💰 تحويل عملات", callback_data="currency"),
         InlineKeyboardButton("⏰ تذكير يومي", callback_data="reminder")],
    ]
    msg = update.message or update.callback_query.message
    await msg.reply_text(
        "👋 *مركز الأدوات الذكية*\n\nاختر الأداة:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ========== الأزرار ==========
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    messages = {
        "rembg":    "🖼️ أرسل الصورة لإزالة خلفيتها:",
        "pdf":      "📄 أرسل ملف PDF لتحويله إلى نص:",
        "short":    "🔗 أرسل الرابط لاختصاره:",
        "qr":       "📷 أرسل النص أو الرابط لتحويله إلى QR Code:",
        "yt":       "🎵 أرسل رابط يوتيوب لتحميله MP3:",
        "translate":"🌍 أرسل النص للترجمة إلى العربية:",
        "currency": "💰 أرسل بالشكل:\n`100 USD to SAR`",
        "reminder": "⏰ أرسل التذكير بالشكل:\n`08:00 اشرب الماء`",
    }

    user_state[uid] = data
    await query.edit_message_text(
        messages[data] + "\n\n/start للرجوع",
        parse_mode="Markdown"
    )

# ========== معالجة الرسائل ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    state = user_state.get(uid)

    if not state:
        await start(update, context)
        return

    # ترجمة النص
    if state == "translate":
        text = update.message.text
        try:
            result = GoogleTranslator(source='auto', target='ar').translate(text)
            await update.message.reply_text(f"🌍 *الترجمة:*\n\n{result}", parse_mode="Markdown")
        except:
            await update.message.reply_text("❌ فشلت الترجمة، حاول مجدداً.")
        user_state[uid] = None

    # اختصار رابط
    elif state == "short":
        url = update.message.text.strip()
        try:
            r = requests.get(f"https://tinyurl.com/api-create.php?url={url}", timeout=10)
            await update.message.reply_text(f"✅ *رابطك المختصر:*\n{r.text}", parse_mode="Markdown")
        except:
            await update.message.reply_text("❌ تعذر الاختصار.")
        user_state[uid] = None

    # QR Code
    elif state == "qr":
        text = update.message.text
        img = qrcode.make(text)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        await update.message.reply_photo(buf, caption="📷 QR Code جاهز!")
        user_state[uid] = None

    # تحويل عملات
    elif state == "currency":
        try:
            parts = update.message.text.upper().split()
            amount, from_c, to_c = float(parts[0]), parts[1], parts[3]
            r = requests.get(f"https://api.exchangerate-api.com/v4/latest/{from_c}", timeout=10)
            rate = r.json()["rates"][to_c]
            result = round(amount * rate, 2)
            await update.message.reply_text(
                f"💰 *النتيجة:*\n{amount} {from_c} = *{result} {to_c}*",
                parse_mode="Markdown"
            )
        except:
            await update.message.reply_text("❌ تأكد من الشكل الصحيح:\n`100 USD to SAR`", parse_mode="Markdown")
        user_state[uid] = None

    # تذكير يومي
    elif state == "reminder":
        try:
            parts = update.message.text.split(" ", 1)
            time_str, reminder_text = parts[0], parts[1]
            hour, minute = map(int, time_str.split(":"))
            chat_id = update.message.chat_id

            scheduler.add_job(
                send_reminder,
                'cron', hour=hour, minute=minute,
                args=[context, chat_id, reminder_text],
                id=f"reminder_{uid}",
                replace_existing=True
            )
            await update.message.reply_text(
                f"✅ تذكير مضبوط!\n⏰ {time_str} كل يوم\n📝 {reminder_text}"
            )
        except:
            await update.message.reply_text("❌ الشكل الصحيح:\n`08:00 اشرب الماء`", parse_mode="Markdown")
        user_state[uid] = None

    # يوتيوب
    elif state == "yt":
        url = update.message.text.strip()
        await update.message.reply_text("⏳ جاري التحميل...")
        try:
            opts = {
                'format': 'bestaudio/best',
                'outtmpl': '/tmp/%(title)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'quiet': True,
            }
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = f"/tmp/{info['title']}.mp3"
            with open(filename, 'rb') as f:
                await update.message.reply_audio(f, title=info['title'])
            os.remove(filename)
        except Exception as e:
            await update.message.reply_text(f"❌ فشل التحميل: {str(e)[:100]}")
        user_state[uid] = None

    else:
        await start(update, context)

# ========== معالجة الملفات ==========
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    state = user_state.get(uid)

    # PDF إلى نص
    if state == "pdf":
        await update.message.reply_text("⏳ جاري استخراج النص...")
        try:
            file = await update.message.document.get_file()
            path = "/tmp/input.pdf"
            await file.download_to_drive(path)
            text = ""
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            if text.strip():
                if len(text) > 4000:
                    text = text[:4000] + "\n\n... (تم الاقتطاع)"
                await update.message.reply_text(f"📄 *النص المستخرج:*\n\n{text}", parse_mode="Markdown")
            else:
                await update.message.reply_text("⚠️ لم يُعثر على نص في هذا الـ PDF.")
        except:
            await update.message.reply_text("❌ فشل استخراج النص.")
        user_state[uid] = None

    # إزالة خلفية
    elif state == "rembg":
        await update.message.reply_text("⏳ جاري إزالة الخلفية...")
        try:
            photo = update.message.photo[-1] if update.message.photo else update.message.document
            file = await photo.get_file()
            path = "/tmp/input.png"
            await file.download_to_drive(path)

            # إزالة بسيطة بالألوان
            img = Image.open(path).convert("RGBA")
            data = img.getdata()
            new_data = []
            bg = data[0][:3]
            for item in data:
                if all(abs(item[i] - bg[i]) < 40 for i in range(3)):
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)
            img.putdata(new_data)
            out = io.BytesIO()
            img.save(out, format="PNG")
            out.seek(0)
            await update.message.reply_document(out, filename="no_bg.png", caption="✅ تمت إزالة الخلفية!")
        except:
            await update.message.reply_text("❌ فشلت العملية.")
        user_state[uid] = None

# ========== إرسال التذكير ==========
async def send_reminder(context, chat_id, text):
    await context.bot.send_message(chat_id=chat_id, text=f"⏰ *تذكيرك اليومي:*\n\n{text}", parse_mode="Markdown")

# ========== تشغيل البوت ==========
async def post_init(application):
    scheduler.start()

app = (ApplicationBuilder()
    .token(TOKEN)
    .post_init(post_init)
    .build())

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_file))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("✅ البوت يعمل بكل الميزات!")
app.run_polling(drop_pending_updates=True)