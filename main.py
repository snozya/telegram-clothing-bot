import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

ASKING_NAME, ASKING_EMAIL, ASKING_PHONE, ASKING_ADDRESS, ASKING_SIZE, CONFIRM, ASKING_QUESTION = range(7)

sizes = ["M", "L", "XL", "XXL"]
orders = {}
ADMIN_ID = os.getenv("ADMIN_ID")

payment_url = "https://yoomoney.ru/to/4100118127237525/1850"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("Оформить заказ"), KeyboardButton("Задать вопрос")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Здравствуйте! Я бот-консультант.\nВыберите, пожалуйста, один из пунктов меню:",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Оформить заказ":
        await update.message.reply_text("Пожалуйста, укажите ваше полное имя (ФИО):")
        return ASKING_NAME
    elif text == "Задать вопрос":
        await update.message.reply_text("Пожалуйста, напишите ваш вопрос. Мы передадим его администратору.")
        return ASKING_QUESTION
    else:
        await update.message.reply_text("Пожалуйста, выберите один из доступных вариантов.")
        return ConversationHandler.END

async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders[update.message.from_user.id] = {"fio": update.message.text}
    await update.message.reply_text("Укажите, пожалуйста, вашу электронную почту:")
    return ASKING_EMAIL

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders[update.message.from_user.id]["email"] = update.message.text
    await update.message.reply_text("Укажите ваш контактный номер телефона:")
    return ASKING_PHONE

async def ask_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders[update.message.from_user.id]["phone"] = update.message.text
    await update.message.reply_text("Укажите город в котором вы проживаете и точный адрес удобного для вас ПВЗ CDEK:")
    return ASKING_ADDRESS

async def ask_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders[update.message.from_user.id]["address"] = update.message.text
    keyboard = [
        [InlineKeyboardButton(size, callback_data=size) for size in sizes]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите, пожалуйста, нужный размер:", reply_markup=reply_markup)
    return ASKING_SIZE

async def size_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    size = query.data
    orders[query.from_user.id]["size"] = size

    order = orders[query.from_user.id]
    summary = (
        f"Ваш заказ оформлен:\n\n"
        f"👤 ФИО: {order['fio']}\n"
        f"📧 Email: {order['email']}\n"
        f"📞 Телефон: {order['phone']}\n"
        f"📦 Адрес доставки: {order['address']}\n"
        f"📐 Размер: {size}\n\n"
        f"💰 Итого к оплате: 1850 рублей (без учёта доставки)"
    )

    # Редактируем предыдущее сообщение текстом без кнопок
    await query.edit_message_text(text=summary)

    # Отправляем новое сообщение с кнопками оплаты и вопроса
    keyboard = [
        [InlineKeyboardButton("Перейти к оплате", url=payment_url)],
        [InlineKeyboardButton("Задать вопрос", callback_data="ask_question")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=query.from_user.id, text="Вы можете оплатить заказ по ссылке ниже:", reply_markup=reply_markup)

    if ADMIN_ID:
        try:
            await context.bot.send_message(
                chat_id=int(ADMIN_ID),
                text=f"📦 Новый заказ от @{query.from_user.username or 'неизвестного пользователя'}:\n\n{summary}"
            )
        except Exception as e:
            print(f"Ошибка отправки админу: {e}")

    return CONFIRM

async def ask_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Пожалуйста, напишите ваш вопрос. Мы передадим его администратору.")
    return ASKING_QUESTION

async def handle_user_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text
    username = update.message.from_user.username or "неизвестный пользователь"
    user_id = update.message.from_user.id

    await update.message.reply_text("Спасибо! Ваш вопрос отправлен администратору.")

    if ADMIN_ID:
        try:
            await context.bot.send_message(
                chat_id=int(ADMIN_ID),
                text=f"❓ Вопрос от @{username} (ID: {user_id}):\n\n{question}"
            )
        except Exception as e:
            print(f"Ошибка отправки админу: {e}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

def main():
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("^Оформить заказ$"), handle_message),
            MessageHandler(filters.Regex("^Задать вопрос$"), handle_message),
        ],
        states={
            ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
            ASKING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASKING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_address)],
            ASKING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_size)],
            ASKING_SIZE: [CallbackQueryHandler(size_chosen)],
            CONFIRM: [CallbackQueryHandler(ask_question_callback, pattern="ask_question")],
            ASKING_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_question)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
