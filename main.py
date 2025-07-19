from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

ASKING_NAME, ASKING_EMAIL, ASKING_PHONE, ASKING_ADDRESS, ASKING_SIZE, CONFIRM = range(6)
sizes = ["M", "L", "XL", "XXL"]

# Хранение данных по user_id
orders = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("Оформить заказ"), KeyboardButton("Задать вопрос"), KeyboardButton("Наши соцсети")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Здравствуйте! Выберите действие:", reply_markup=reply_markup)
    return ConversationHandler.END

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if text == "Оформить заказ":
        orders[user_id] = {}  # Инициализируем заказ
        await update.message.reply_text("Введите, пожалуйста, ФИО:")
        return ASKING_NAME

    elif text == "Задать вопрос":
        await update.message.reply_text("Напишите ваш вопрос:")
        return CONFIRM

    elif text == "Наши соцсети":
        text = (
            "Наши соцсети:\n"
            "Telegram: https://t.me/yourchannel\n"
            "Instagram: https://instagram.com/yourprofile\n"
            "TikTok: https://tiktok.com/@yourprofile"
        )
        await update.message.reply_text(text)
        # Предлагаем главное меню заново
        keyboard = [
            [KeyboardButton("Оформить заказ"), KeyboardButton("Задать вопрос"), KeyboardButton("Наши соцсети")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Пожалуйста, выберите одну из кнопок.")
        return ConversationHandler.END


async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    orders[user_id]["fio"] = update.message.text.strip()
    await update.message.reply_text("Введите электронную почту:")
    return ASKING_EMAIL

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    orders[user_id]["email"] = update.message.text.strip()
    await update.message.reply_text("Введите номер телефона:")
    return ASKING_PHONE

async def ask_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    orders[user_id]["phone"] = update.message.text.strip()
    await update.message.reply_text("Введите адрес доставки:")
    return ASKING_ADDRESS

async def ask_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    orders[user_id]["address"] = update.message.text.strip()

    keyboard = [
        [InlineKeyboardButton(size, callback_data=size) for size in sizes]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите размер:", reply_markup=reply_markup)
    return ASKING_SIZE

async def size_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    size = query.data
    orders[user_id]["size"] = size

    order_text = (
        f"Новый заказ:\n"
        f"ФИО: {orders[user_id]['fio']}\n"
        f"Email: {orders[user_id]['email']}\n"
        f"Телефон: {orders[user_id]['phone']}\n"
        f"Адрес: {orders[user_id]['address']}\n"
        f"Размер: {size}\n\n"
        f"Итого к оплате: 1850 рублей"
    )

    # Отправляем админу
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=order_text)

    text = (
        f"Ваш заказ принят:\n"
        f"ФИО: {orders[user_id]['fio']}\n"
        f"Email: {orders[user_id]['email']}\n"
        f"Телефон: {orders[user_id]['phone']}\n"
        f"Адрес: {orders[user_id]['address']}\n"
        f"Размер: {size}\n\n"
        f"Итого к оплате: 1850 рублей"
    )

    keyboard = [
        [InlineKeyboardButton("Оплатить", url="https://yoomoney.ru/to/4100118127237525/1850")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup)

    return ConversationHandler.END


async def receive_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    question = update.message.text.strip()
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Вопрос от пользователя {user_id}:\n{question}")
    await update.message.reply_text("Спасибо! Ваш вопрос принят. Мы свяжемся с вами в ближайшее время.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена. Чтобы начать заново, нажмите /start")
    return ConversationHandler.END


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)],
        states={
            ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
            ASKING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASKING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_address)],
            ASKING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_size)],
            ASKING_SIZE: [CallbackQueryHandler(size_chosen)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_question)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
