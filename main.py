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
    filters,
    ConversationHandler,
)
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

ASKING_NAME, ASKING_EMAIL, ASKING_PHONE, ASKING_ADDRESS, ASKING_SIZE, CONFIRM = range(6)

sizes = ["M", "L", "XL", "XXL"]
orders = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("Оформить заказ")],
        [KeyboardButton("Задать вопрос")],
        [KeyboardButton("Наши соцсети / Информация")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Добро пожаловать! Чем можем помочь?", reply_markup=reply_markup)

# Обработка главного меню
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Оформить заказ":
        await update.message.reply_text("Пожалуйста, введите ваше ФИО:")
        return ASKING_NAME

    elif text == "Задать вопрос":
        await update.message.reply_text("Напишите ваш вопрос, и мы свяжемся с вами в ближайшее время.")
        return ConversationHandler.END

    elif text == "Наши соцсети / Информация":
        await update.message.reply_text(
            "Следите за нами в соцсетях:\n\n"
            "📢 Telegram: https://t.me/yourchannel\n"
            "📸 Instagram: https://instagram.com/yourprofile\n"
            "🎵 TikTok: https://tiktok.com/@yourprofile"
        )
        return ConversationHandler.END

    else:
        await update.message.reply_text("Пожалуйста, выберите одну из кнопок.")
        return ConversationHandler.END

# Шаги оформления заказа
async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders[update.message.from_user.id] = {"fio": update.message.text}
    await update.message.reply_text("Введите вашу электронную почту:")
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
    keyboard = [
        [InlineKeyboardButton(size, callback_data=size) for size in sizes]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите размер:", reply_markup=reply_markup)
    return ASKING_SIZE

# Пользователь выбрал размер
async def size_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    size = query.data
    orders[user_id]["size"] = size

    order = orders[user_id]
    summary = (
        f"🛍 Ваш заказ:\n\n"
        f"👤 ФИО: {order['fio']}\n"
        f"📧 Email: {order['email']}\n"
        f"📞 Телефон: {order['phone']}\n"
        f"📦 Адрес: {order['address']}\n"
        f"📐 Размер: {size}\n\n"
        f"💰 Итого к оплате: 1850 ₽ (без доставки)"
    )

    keyboard = [
        [InlineKeyboardButton("Оплатить", url="https://yoomoney.ru/to/4100118127237525/1850")],
        [InlineKeyboardButton("Я оплатил", callback_data="payment_done")],
        [InlineKeyboardButton("Задать вопрос", callback_data="ask_question")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text=summary, reply_markup=reply_markup)

    # Уведомление администратору
    if ADMIN_ID:
        await context.bot.send_message(
            chat_id=int(ADMIN_ID),
            text=f"📥 Новый заказ от @{query.from_user.username or user_id}:\n\n{summary}"
        )

    return CONFIRM

# Пользователь нажал "Я оплатил"
async def payment_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ Спасибо! Мы скоро с вами свяжемся.")

    if ADMIN_ID:
        await context.bot.send_message(
            chat_id=int(ADMIN_ID),
            text=f"💳 Пользователь @{query.from_user.username or query.from_user.id} сообщил об оплате заказа."
        )
    return ConversationHandler.END

# Задать вопрос после заказа
async def ask_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Напишите ваш вопрос, и мы свяжемся с вами в ближайшее время.")
    return ConversationHandler.END

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END

# Запуск
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        ],
        states={
            ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
            ASKING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASKING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_address)],
            ASKING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_size)],
            ASKING_SIZE: [CallbackQueryHandler(size_chosen)],
            CONFIRM: [
                CallbackQueryHandler(ask_question_callback, pattern="ask_question"),
                CallbackQueryHandler(payment_done_callback, pattern="payment_done")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
