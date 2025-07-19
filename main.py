import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
if ADMIN_CHAT_ID == 0:
    raise ValueError("ADMIN_CHAT_ID не задан в переменных окружения")

ASKING_NAME, ASKING_EMAIL, ASKING_PHONE, ASKING_ADDRESS, ASKING_SIZE, CONFIRM = range(6)
sizes = ["M", "L", "XL", "XXL"]
orders = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("Оформить заказ"), KeyboardButton("Задать вопрос")],
        [KeyboardButton("Наши соцсети / Информация")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Здравствуйте! Чем могу помочь?", reply_markup=reply_markup
    )
    return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Оформить заказ":
        await update.message.reply_text("Пожалуйста, введите ФИО:")
        return ASKING_NAME
    elif text == "Задать вопрос":
        await update.message.reply_text("Напишите ваш вопрос, мы ответим в ближайшее время.")
        return ASKING_EMAIL
    elif text == "Наши соцсети / Информация":
        keyboard = [
            [
                InlineKeyboardButton("Telegram канал", url="https://t.me/your_channel"),
                InlineKeyboardButton("Instagram", url="https://instagram.com/your_profile"),
            ],
            [
                InlineKeyboardButton("TikTok", url="https://tiktok.com/@your_profile"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Наши соцсети:",
            reply_markup=reply_markup,
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text("Пожалуйста, выберите опцию с помощью кнопок.")
        return ConversationHandler.END

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["fio"] = update.message.text
    context.user_data["order_in_progress"] = True
    await update.message.reply_text("Введите электронную почту:")
    return ASKING_EMAIL

async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if context.user_data.get("order_in_progress"):
        orders[user_id] = {"fio": context.user_data["fio"]}
        orders[user_id]["email"] = text
        await update.message.reply_text("Введите контактный номер телефона:")
        return ASKING_PHONE
    else:
        await context.bot.send_message(
            ADMIN_CHAT_ID,
            f"❓ Вопрос от @{update.message.from_user.username or user_id}:\n{text}",
        )
        await update.message.reply_text("Спасибо! Мы скоро ответим.")
        return ConversationHandler.END

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    orders[user_id]["phone"] = update.message.text
    await update.message.reply_text("Введите адрес доставки:")
    return ASKING_ADDRESS

async def ask_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    user_id = query.from_user.id
    size = query.data
    orders[user_id]["size"] = size

    text = (
        f"Ваш заказ:\n"
        f"ФИО: {orders[user_id]['fio']}\n"
        f"Email: {orders[user_id]['email']}\n"
        f"Телефон: {orders[user_id]['phone']}\n"
        f"Адрес: {orders[user_id]['address']}\n"
        f"Размер: {size}\n\n"
        f"Итого к оплате: 1850 рублей (без доставки)"
    )

    keyboard = [
        [InlineKeyboardButton("Перейти к оплате", url="https://yoomoney.ru/to/4100118127237525/1850")],
        [InlineKeyboardButton("Задать вопрос", callback_data="ask_question")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text=text, reply_markup=reply_markup)

    await context.bot.send_message(
        ADMIN_CHAT_ID,
        f"🛒 Новый заказ от @{query.from_user.username or user_id}:\n{text}",
    )

    return CONFIRM

async def ask_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Напишите ваш вопрос, мы ответим в ближайшее время.")
    return ASKING_EMAIL

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отмена выполнена. Если нужно, начните сначала /start.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        states={
            ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASKING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
            ASKING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASKING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_address)],
            ASKING_SIZE: [CallbackQueryHandler(size_chosen)],
            CONFIRM: [CallbackQueryHandler(ask_question_callback, pattern="ask_question")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
