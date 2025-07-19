from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler

BOT_TOKEN = ""  # Установи в переменных окружения

ASKING_NAME, ASKING_EMAIL, ASKING_PHONE, ASKING_ADDRESS, ASKING_SIZE, CONFIRM, ASKING_QUESTION = range(7)
sizes = ["M", "L", "XL", "XXL"]
orders = {}

ADMIN_ID = 123456789  # Твой Telegram ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("Оформить заказ"), KeyboardButton("Задать вопрос")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Здравствуйте! Чем могу помочь?", reply_markup=reply_markup)
    return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "Оформить заказ":
        await update.message.reply_text("Пожалуйста, введите ФИО:")
        return ASKING_NAME
    elif text == "Задать вопрос":
        await update.message.reply_text("Пожалуйста, напишите ваш вопрос:")
        return ASKING_QUESTION
    else:
        await update.message.reply_text("Пожалуйста, используйте кнопки для выбора.")
        return ConversationHandler.END

async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    fio = update.message.text.strip()
    if not fio:
        await update.message.reply_text("ФИО не может быть пустым. Пожалуйста, введите ФИО:")
        return ASKING_NAME
    orders[user_id] = {"fio": fio}
    await update.message.reply_text("Введите вашу электронную почту:")
    return ASKING_EMAIL

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    email = update.message.text.strip()
    if "@" not in email or "." not in email:
        await update.message.reply_text("Пожалуйста, введите корректный email:")
        return ASKING_EMAIL
    orders[user_id]["email"] = email
    await update.message.reply_text("Введите контактный номер телефона:")
    return ASKING_PHONE

async def ask_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    phone = update.message.text.strip()
    if len(phone) < 5:
        await update.message.reply_text("Пожалуйста, введите корректный номер телефона:")
        return ASKING_PHONE
    orders[user_id]["phone"] = phone
    await update.message.reply_text("Введите адрес доставки:")
    return ASKING_ADDRESS

async def ask_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    address = update.message.text.strip()
    if len(address) < 5:
        await update.message.reply_text("Пожалуйста, введите корректный адрес доставки:")
        return ASKING_ADDRESS
    orders[user_id]["address"] = address
    keyboard = [[InlineKeyboardButton(size, callback_data=size) for size in sizes]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите размер:", reply_markup=reply_markup)
    return ASKING_SIZE

async def size_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    size = query.data
    user_id = query.from_user.id
    orders[user_id]["size"] = size

    text = (
        f"Ваш заказ:\n"
        f"ФИО: {orders[user_id]['fio']}\n"
        f"Email: {orders[user_id]['email']}\n"
        f"Телефон: {orders[user_id]['phone']}\n"
        f"Адрес: {orders[user_id]['address']}\n"
        f"Размер: {size}\n\n"
        f"Итого к оплате: 1850 рублей (без доставки)."
    )
    keyboard = [
        [InlineKeyboardButton("Перейти к оплате", url="https://yoomoney.ru/to/4100118127237525/1850")],
        [InlineKeyboardButton("Наши соцсети", callback_data="socials")],
        [InlineKeyboardButton("Задать вопрос", callback_data="ask_question")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"Новый заказ:\n{text}")
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")

    await query.edit_message_text(text=text, reply_markup=reply_markup)
    return CONFIRM

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    question = update.message.text.strip()
    if not question:
        await update.message.reply_text("Пожалуйста, напишите ваш вопрос:")
        return ASKING_QUESTION

    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"Вопрос от пользователя {user_id}:\n{question}")
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")

    await update.message.reply_text("Спасибо! Ваш вопрос отправлен, мы скоро ответим.")
    return ConversationHandler.END

async def socials_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "Наши соцсети:\n"
        "Telegram канал: https://t.me/yourchannel\n"
        "Instagram: https://instagram.com/yourprofile\n"
        "TikTok: https://www.tiktok.com/@yourprofile"
    )
    await query.edit_message_text(text=text)
    return CONFIRM

async def ask_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Пожалуйста, напишите ваш вопрос:")
    return ASKING_QUESTION

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

def main():
    import os
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        states={
            ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
            ASKING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASKING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_address)],
            ASKING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_size)],
            ASKING_SIZE: [CallbackQueryHandler(size_chosen)],
            CONFIRM: [
                CallbackQueryHandler(ask_question_callback, pattern="ask_question"),
                CallbackQueryHandler(socials_callback, pattern="socials")
            ],
            ASKING_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_question)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
