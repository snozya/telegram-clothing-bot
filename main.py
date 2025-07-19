from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler

BOT_TOKEN = ""  # Будет из переменных окружения

ASKING_NAME, ASKING_EMAIL, ASKING_PHONE, ASKING_ADDRESS, ASKING_SIZE, CONFIRM = range(6)
sizes = ["M", "L", "XL", "XXL"]
orders = {}

ADMIN_CHAT_ID = int("123456789")  # Задай свой ID админа

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("Оформить заказ"), KeyboardButton("Задать вопрос")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Здравствуйте! Пожалуйста, выберите действие:", reply_markup=reply_markup)
    return ConversationHandler.END  # Начинаем с меню, дальше обработка кнопок

async def handle_start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Оформить заказ":
        await update.message.reply_text("Введите ФИО:")
        return ASKING_NAME
    elif text == "Задать вопрос":
        await update.message.reply_text("Напишите ваш вопрос, мы ответим в ближайшее время.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Пожалуйста, выберите кнопку из меню.")
        return ConversationHandler.END

async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders[update.message.from_user.id] = {"fio": update.message.text}
    await update.message.reply_text("Введите электронную почту:")
    return ASKING_EMAIL

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders[update.message.from_user.id]["email"] = update.message.text
    await update.message.reply_text("Введите контактный номер телефона:")
    return ASKING_PHONE

async def ask_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders[update.message.from_user.id]["phone"] = update.message.text
    await update.message.reply_text("Введите адрес доставки:")
    return ASKING_ADDRESS

async def ask_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders[update.message.from_user.id]["address"] = update.message.text
    keyboard = [[InlineKeyboardButton(size, callback_data=size) for size in sizes]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите размер:", reply_markup=reply_markup)
    return ASKING_SIZE

async def size_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    size = query.data
    orders[query.from_user.id]["size"] = size

    text = (
        f"Ваш заказ:\n"
        f"ФИО: {orders[query.from_user.id]['fio']}\n"
        f"Email: {orders[query.from_user.id]['email']}\n"
        f"Телефон: {orders[query.from_user.id]['phone']}\n"
        f"Адрес: {orders[query.from_user.id]['address']}\n"
        f"Размер: {size}\n\n"
        f"Итого к оплате: 1850 рублей (без доставки)"
    )
    keyboard = [
        [InlineKeyboardButton("Перейти к оплате", url="https://yoomoney.ru/to/4100118127237525/1850")],
        [InlineKeyboardButton("Наши соцсети", callback_data="socials")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup)

    # Уведомляем админа
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"Новый заказ от {orders[query.from_user.id]['fio']}.\nДетали:\n{text}"
    )
    return CONFIRM

async def socials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "Наши соцсети:\n"
        "Telegram: https://t.me/yourchannel\n"
        "Instagram: https://instagram.com/yourprofile\n"
        "TikTok: https://tiktok.com/@yourprofile"
    )
    await query.edit_message_text(text=text)
    return CONFIRM

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменён.")
    return ConversationHandler.END

def main():
    import os
    token = os.getenv("BOT_TOKEN")
    global ADMIN_CHAT_ID
    ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", ADMIN_CHAT_ID))
    app = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), MessageHandler(filters.Regex("^(Оформить заказ|Задать вопрос)$"), handle_start_menu)],
        states={
            ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
            ASKING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASKING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_address)],
            ASKING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_size)],
            ASKING_SIZE: [CallbackQueryHandler(size_chosen)],
            CONFIRM: [CallbackQueryHandler(socials, pattern="socials")]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
