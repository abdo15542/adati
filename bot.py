from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "8612859173:AAFGuAXaoDt9J---j0-UV0XiknkS7qvxvWs"

user_state = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✍️ تلخيص نص", callback_data="summarize")],
        [InlineKeyboardButton("🔢 عد الكلمات", callback_data="wordcount")],
        [InlineKeyboardButton("🔗 اختصار رابط", callback_data="shortlink")],
    ]
    await update.message.reply_text(
        "👋 أهلاً في *مركز الأدوات الذكية*\n\nاختر الأداة:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if query.data == "summarize":
        user_state[uid] = "summarize"
        await query.edit_message_text("✍️ أرسل النص الذي تريد تلخيصه:")

    elif query.data == "wordcount":
        user_state[uid] = "wordcount"
        await query.edit_message_text("🔢 أرسل النص لعد كلماته:")

    elif query.data == "shortlink":
        user_state[uid] = "shortlink"
        await query.edit_message_text("🔗 أرسل الرابط الذي تريد اختصاره:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text
    state = user_state.get(uid)

    if state == "summarize":
        words = text.split()
        total = len(words)
        if total < 20:
            await update.message.reply_text("⚠️ النص قصير جداً للتلخيص!")
        else:
            summary = " ".join(words[:total//3]) + "..."
            await update.message.reply_text(
                f"📝 *الملخص:*\n\n{summary}\n\n"
                f"📊 الأصل: {total} كلمة | الملخص: {total//3} كلمة",
                parse_mode="Markdown"
            )
        user_state[uid] = None

    elif state == "wordcount":
        words = len(text.split())
        chars = len(text)
        lines = len(text.splitlines())
        await update.message.reply_text(
            f"📊 *إحصائيات النص:*\n\n"
            f"🔤 الكلمات: {words}\n"
            f"🔡 الأحرف: {chars}\n"
            f"📄 الأسطر: {lines}",
            parse_mode="Markdown"
        )
        user_state[uid] = None

    elif state == "shortlink":
        import urllib.parse
        encoded = urllib.parse.quote(text, safe='')
        short = f"https://tinyurl.com/api-create.php?url={encoded}"
        import urllib.request
        try:
            result = urllib.request.urlopen(short).read().decode()
            await update.message.reply_text(f"✅ *رابطك المختصر:*\n{result}", parse_mode="Markdown")
        except:
            await update.message.reply_text("❌ تعذر اختصار الرابط، تأكد أنه صحيح.")
        user_state[uid] = None

    else:
        await start(update, context)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("✅ البوت يعمل مع الأدوات!")
app.run_polling(drop_pending_updates=True)
