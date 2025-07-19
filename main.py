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
orders = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("Оформить заказ"), KeyboardButton("Задать вопрос"), KeyboardButton("Наши соцсети")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Здравствуйте! Чем могу помочь?", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Оформить заказ":
        await update.message.reply_text("Пожалуйста, введите ФИО:")
        return ASKING_NAME
    elif text == "Задать вопрос":
        await update.message.reply_text("Напишите ваш вопрос, и мы ответим в ближайшее время.")
        return CONFIRM
    elif text == "Наши соцсети":
        text = (
            "Наши соцсети:\n"
            "Telegram: https://t.me/yourchannel\n"
            "Instagram: https://instagram.com/yourprofile\n"
            "TikTok: https://tiktok.com/@yourprofile"
        )
        await update.message.reply_text(text)
        # После показа соцсетей выводим главное меню заново
        keyboard = [
            [KeyboardButton("Оформить заказ"), KeyboardButton("Задать вопрос"), KeyboardButton("Наши соцсети")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Чем еще могу помочь?", reply_markup=reply_markup)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Пожалуйста, выберите одну из кнопок.")
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
    orders[query.from_user.id]["size"] = size

    order_text = (
        f"Новый заказ:\n"
        f"ФИО: {orders[query.from_user.id]['fio']}\n"
        f"Email: {orders[query.from_user.id]['email']}\n"
        f"Телефон: {orders[query.from_user.id]['phone']}\n"
        f"Адрес: {orders[query.from_user.id]['address']}\n"
        f"Размер: {size}\n\n"
        f"Итого к оплате: 1850 рублей (без доставки)"
    )

    # Отправляем уведомление админу
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=order_text)

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
        [InlineKeyboardButton("Задать вопрос", callback_data="ask_question")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup)
    return CONFIRM

async def ask_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Пожалуйста, напишите ваш вопрос, и мы ответим в ближайшее время.")
    return CONFIRM

async def receive_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    question = update.message.text
    # Отправляем вопрос админу
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Вопрос от пользователя {user_id}:\n{question}")
    await update.message.reply_text("Спасибо! Ваш вопрос принят. Мы ответим вам в ближайшее время.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

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
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_question),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
