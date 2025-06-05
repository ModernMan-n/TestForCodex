import json
from functools import wraps
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, MessageHandler,
                          Filters, ConversationHandler, CallbackContext)

# Load persistent data
DATA_FILE = 'data.json'
SCHEDULE_FILE = 'schedule.json'


def load_data():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def restricted(func):
    """Decorator to restrict commands to the bot owner"""
    ADMIN_ID = 123456789  # replace with real admin id

    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            update.message.reply_text("Access denied")
            return
        return func(update, context, *args, **kwargs)

    return wrapped


# --- Command Handlers ---

def start(update: Update, context: CallbackContext):
    data = load_data()
    user_id = update.effective_user.id
    if user_id not in data['users']:
        data['users'].append(user_id)
        save_data(data)
    update.message.reply_text(
        "Добро пожаловать в наше танцевальное комьюнити! \n"
        "Используйте /about, /schedule, /signup_course, /signup_event, /faq"
    )


def about(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Мы танцевальное комьюнити, объединяющее людей, которые любят двигаться."
    )


def schedule(update: Update, context: CallbackContext):
    with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
        sched = json.load(f)
    text = f"Расписание на {sched['month']}:\n" + "\n".join(sched['schedule'])
    update.message.reply_text(text)


# Conversation states
CHOOSING_GROUP = 1
CHOOSING_EVENT = 2


def signup_course_start(update: Update, context: CallbackContext):
    data = load_data()
    buttons = [[g] for g in data['courses'].keys()]
    update.message.reply_text(
        "Выберите группу:",
        reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True)
    )
    return CHOOSING_GROUP


def signup_course_choose(update: Update, context: CallbackContext):
    group = update.message.text
    data = load_data()
    if group not in data['courses']:
        update.message.reply_text("Нет такой группы")
        return ConversationHandler.END
    course = data['courses'][group]
    user_id = update.effective_user.id
    if user_id in course['attendees']:
        update.message.reply_text("Вы уже записаны")
        return ConversationHandler.END
    if len(course['attendees']) >= course['capacity']:
        update.message.reply_text("К сожалению, мест нет")
        return ConversationHandler.END
    course['attendees'].append(user_id)
    save_data(data)
    update.message.reply_text(f"Вы записаны в {group}!")
    return ConversationHandler.END


def signup_event_start(update: Update, context: CallbackContext):
    data = load_data()
    buttons = [[e] for e in data['events'].keys()]
    update.message.reply_text(
        "Выберите мероприятие:",
        reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True)
    )
    return CHOOSING_EVENT


def signup_event_choose(update: Update, context: CallbackContext):
    event = update.message.text
    data = load_data()
    if event not in data['events']:
        update.message.reply_text("Нет такого мероприятия")
        return ConversationHandler.END
    e = data['events'][event]
    user_id = update.effective_user.id
    if user_id in e['attendees']:
        update.message.reply_text("Вы уже записаны")
        return ConversationHandler.END
    if len(e['attendees']) >= e['capacity']:
        update.message.reply_text("К сожалению, мест нет")
        return ConversationHandler.END
    e['attendees'].append(user_id)
    save_data(data)
    update.message.reply_text(f"Вы записаны на {event}!")
    return ConversationHandler.END


def faq(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Стоимость: уточняйте у администратора.\n"
        "Расписание: /schedule\n"
        "Можно ли прийти из другого города? Да!"
    )


@restricted
def broadcast(update: Update, context: CallbackContext):
    msg = " ".join(context.args)
    if not msg:
        update.message.reply_text("Использование: /broadcast <текст>")
        return
    data = load_data()
    for user_id in data['users']:
        context.bot.send_message(chat_id=user_id, text=msg)
    update.message.reply_text("Рассылка отправлена")


def main(token: str):
    updater = Updater(token=token, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('about', about))
    dp.add_handler(CommandHandler('schedule', schedule))
    dp.add_handler(CommandHandler('faq', faq))
    dp.add_handler(CommandHandler('broadcast', broadcast))

    course_conv = ConversationHandler(
        entry_points=[CommandHandler('signup_course', signup_course_start)],
        states={
            CHOOSING_GROUP: [MessageHandler(Filters.text & ~Filters.command, signup_course_choose)]
        },
        fallbacks=[]
    )
    dp.add_handler(course_conv)

    event_conv = ConversationHandler(
        entry_points=[CommandHandler('signup_event', signup_event_start)],
        states={
            CHOOSING_EVENT: [MessageHandler(Filters.text & ~Filters.command, signup_event_choose)]
        },
        fallbacks=[]
    )
    dp.add_handler(event_conv)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    # Replace 'YOUR_TOKEN' with your actual bot token
    main('YOUR_TOKEN')
