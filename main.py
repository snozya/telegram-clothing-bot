from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler

BOT_TOKEN = ""  # Добавь токен через переменные окружения

ASKING_NAME, ASKING_EMAIL, ASKING_PHONE, ASKING_ADDRESS, ASKING_SIZE, CONFIRM = range(6)
sizes = ["M", "L", "XL", "XXL"]
orders = {}

ADMIN_CHAT_ID = 12345678  # замени на свой ID администратора

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("Оформить заказ"), KeyboardButton("Задать вопрос")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Здравствуйте! Чем могу помочь?", reply_markup=reply_markup)
    return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Оформить заказ":
        await update.message.reply_text("Пожалуйста, введите ваше ФИО:")
        return ASKING_NAME
    elif text == "Задать вопрос":
        await update.message.reply_text("Напишите ваш вопрос, мы ответим в ближайшее время.")
        return ASKING_EMAIL  # сразу ждем вопрос (в следующем состоянии)
    else:
        await update.message.reply_text("Пожалуйста, выберите одну из кнопок ниже.")
        return ConversationHandler.END

async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if context.user_data.get('is_question'):
        question = update.message.text
        # Отправляем админу вопрос
        await context.bot.send_message(ADMIN_CHAT_ID, f"Вопрос от @{update.message.from_user.username or update.message.from_user.first_name}:\n{question}")
        await update.message.reply_text("Спасибо! Ваш вопрос получен, мы скоро ответим.")
        context.user_data.clear()
        return ConversationHandler.END
    else:
        # Если это оформление заказа - записываем ФИО
        orders[user_id] = {"fio": update.message.text}
        await update.message.reply_text("Введите вашу электронную почту:")
        return ASKING_EMAIL

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    orders[user_id]["email"] = update.message.text
    await update.message.reply_text("Введите контактный номер телефона:")
    return ASKING_PHONE

async def ask_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    orders[user_id]["phone"] = update.message.text
    await update.message.reply_text("Введите адрес доставки:")
    return ASKING_ADDRESS

async def ask_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    orders[user_id]["address"] = update.message.text

    keyboard = [
        [InlineKeyboardButton(size, callback_data=size) for size in sizes]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите размер:", reply_markup=reply_markup)
    return ASKING_SIZE

async def size_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    size = query.data
    user_id = query.from_user.id
    orders[user_id]["size"] = size

    order_text = (
        f"Ваш заказ:\n"
        f"ФИО: {orders[user_id]['fio']}\n"
        f"Email: {orders[user_id]['email']}\n"
        f"Телефон: {orders[user_id]['phone']}\n"
        f"Адрес: {orders[user_id]['address']}\n"
        f"Размер: {size}\n\n"
        f"Итого к оплате: 1850 рублей (без доставки)."
    )

    keyboard = [
        [InlineKeyboardButton("Перейти к оплате", url="https://yoomoney.ru/to/4100118127237525/1850")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем админу уведомление о новом заказе
    await context.bot.send_message(ADMIN_CHAT_ID, f"Новый заказ от @{query.from_user.username or query.from_user.first_name}:\n{order_text}")

    await query.edit_message_text(text=order_text, reply_markup=reply_markup)
    return CONFIRM

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отмена. Если нужно, начните заново командой /start.")
    context.user_data.clear()
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
            CONFIRM: [MessageHandler(filters.ALL, cancel)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
