#!/usr/bin/python3
import logging
import get_game
import uni_forum
import init_bot
import telegram
import os
import pytz
from datetime import datetime, timedelta
from storer import Storer
from user_info import UserInfo
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, Job

STORED_FILE = os.getenv('UNI_STORED_FILE', 'unison_bot_shelve.db')

MENU, AWAIT_INPUT_GAME, AWAIT_MEETING_ANSWER = range(3)
state = dict()

users = {}
users_store = Storer(STORED_FILE)
forum_subscribers = dict()

meeting_subscribers = []
komsostav = []

posts_from_forum = []
last_check_new_posts = 0
UPDATE_FORUM_POSTS_TIMEOUT_SEC = 10. * 60
DEL_FORUM_POSTS_TIMEOUT_SEC = 24 * 60. * 60

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def log_params(method_name, update):
    logger.debug("Method: %s\nFrom: %s\n chat_id: %d\nText: %s" %
                 (method_name,
                  update.message.from_user,
                  update.message.chat_id,
                  update.message.text))


def get_description():
    return """/help - Show help
/start - Start message
/get_game - Returns a random game from selected partition
/start_forum_subscription - Start subscription on a forum posts
/stop_forum_subscription - Stop this subscription
/change_update_delay - Change delay for checking new posts
/start_meeting_subscription - Start subscription on a meetings
/stop_meeting_subscription - Stop this subscription"""


def start(bot, update):
    log_params('start', update)
    bot.sendMessage(update.message.chat_id, text='Hi! Use next commands:\n%s' % (get_description()))


def bot_help(bot, update):
    log_params('help', update)
    bot.sendMessage(update.message.chat_id, text="Supported commands:\n%s" % (get_description()))


def get_games(bot, update, args=None):
    log_params('get_games', update)
    chat_id = update.message.chat_id
    text = update.message.text

    if text[0] == '/' and args:
        list_response = get_game.get_games_category()
        category = ' '.join(args)
        if category in list_response:
            send_message_with_game(bot, update, category)
        else:
            bot.sendMessage(chat_id, text='Wrong topic')
            game_markup(bot, update)
    elif text[0] == '/':
        game_markup(bot, update)


def game_markup(bot, update):
    chat_id = update.message.chat_id
    list_response = get_game.get_games_category()
    custom_keyboard = [[]]
    for item in list_response:
        custom_keyboard.append([telegram.InlineKeyboardButton(item, callback_data=item)])
    reply_markup = telegram.InlineKeyboardMarkup(custom_keyboard)
    state[update.message.chat_id] = AWAIT_INPUT_GAME
    bot.sendMessage(chat_id, text='Choose topic', reply_markup=reply_markup)


def send_message_with_game(bot, update, category):
    chat_id = update.message.chat_id
    game = get_game.get_random_game(category)
    bot.sendMessage(chat_id, text=game, parse_mode=telegram.ParseMode.MARKDOWN)


def game_from_inline_markup(bot, query):
    game = get_game.get_random_game(query.data)
    bot.editMessageText(text=game, chat_id=query.message.chat_id, message_id=query.message.message_id,
                        parse_mode=telegram.ParseMode.MARKDOWN)


def start_meeting_subscription(bot, update):
    telegram_user = update.message.from_user
    chat_id = update.message.chat_id
    if meeting_subscribers.count(chat_id) != 0:
        bot.sendMessage(chat_id, text='You have already subscribed on meetings')
        return
    if telegram_user.id not in users:
        users[telegram_user.id] = UserInfo(telegram_user)
        state[chat_id] = MENU
    users[telegram_user.id].check_meetings = True
    meeting_subscribers.append(chat_id)
    bot.sendMessage(chat_id, text='Subscription on meeting started')
    log_params('start_meeting_subscription', update)
    users_store.store('users', users)


def stop_meeting_subscription(bot, update):
    chat_id = update.message.chat_id
    telegram_user = update.message.from_user
    if meeting_subscribers.count(chat_id) == 0:
        bot.sendMessage(chat_id, text='You have not started subscription on meeting')
        return
    users[telegram_user.id].job_check_posts = False
    meeting_subscribers.remove(chat_id)
    bot.sendMessage(chat_id, text='Subscription stopped')
    log_params('stop_meeting_subscription', update)
    users_store.store('users', users)


def create_meeting(bot, update, args=None):
    chat_id = update.message.chat_id
    telegram_user = update.message.from_user
    if komsostav.count(telegram_user.id):
        bot.sendMessage(chat_id, text="You can't do that")
        return
    text = update.message.text
    if text[0] == '/' and args:
        bot.sendMessage(chat_id, text="Done! New meeting created!")
        meeting_description = '*Новый сбор: *\n' + ' '.join(args)
        for subscriber in meeting_subscribers:
            custom_keyboard = [[telegram.InlineKeyboardButton('Приду', callback_data='Yes'),
                                telegram.InlineKeyboardButton('Не приду', callback_data='No')]]
            reply_markup = telegram.InlineKeyboardMarkup(custom_keyboard)
            state[subscriber] = AWAIT_MEETING_ANSWER
            bot.sendMessage(subscriber, text=meeting_description, reply_markup=reply_markup,
                            parse_mode=telegram.ParseMode.MARKDOWN)
    elif text[0] == '/':
        bot.sendMessage(chat_id, text="Type this command with description of the meeting")


def answer_for_meting(bot, query):
    user = users[query.message.chat_id].user
    person = user.first_name + ' ' + user.last_name + ' ' + user.name
    meeting_description = query.message.text[13:]
    if query.data == 'Yes':
        bot.editMessageText(text='*Отлично!*\n' + meeting_description, chat_id=query.message.chat_id,
                            message_id=query.message.message_id, parse_mode=telegram.ParseMode.MARKDOWN)
        answer_to_komsostav(bot, person, 'придет')
    if query.data == 'No':
        bot.editMessageText(text='*Жаль :(*\n' + meeting_description, chat_id=query.message.chat_id,
                            message_id=query.message.message_id, parse_mode=telegram.ParseMode.MARKDOWN)
        answer_to_komsostav(bot, person, 'не придет')


def answer_to_komsostav(bot, person, answer):
    for kom in komsostav:
        bot.sendMessage(kom, text=person + ' ' + answer + ' на сбор.')


def callback_query(bot, update):
    query = update.callback_query
    if state[query.message.chat_id] == AWAIT_INPUT_GAME:
        game_from_inline_markup(bot, query)
    if state[query.message.chat_id] == AWAIT_MEETING_ANSWER:
        answer_for_meting(bot, query)
    state[query.message.chat_id] = MENU


def start_forum_subscription(bot, update, job_queue):
    telegram_user = update.message.from_user
    chat_id = update.message.chat_id
    if chat_id in forum_subscribers:
        bot.sendMessage(chat_id, text='You have already subscribed')
        return
    if telegram_user.id not in users:
        users[telegram_user.id] = UserInfo(telegram_user)
    users[telegram_user.id].job_check_posts = True
    add_forum_job(telegram_user.id, job_queue)
    bot.sendMessage(chat_id, text='Subscription started')
    log_params('start_forum_subscription', update)
    users_store.store('users', users)


def add_forum_job(user_id, job_queue):
    user_info = users[user_id]
    job = Job(check_new_posts_from_list, user_info.job_posts_timeout, repeat=True, context=user_id)
    forum_subscribers[user_id] = job
    job_queue.put(job)


def del_forum_job(user_id):
    job = forum_subscribers[user_id]
    job.schedule_removal()
    del forum_subscribers[user_id]


def change_forum_delay(bot, update, args=None):
    telegram_user = update.message.from_user
    chat_id = update.message.chat_id
    if chat_id not in forum_subscribers:
        bot.sendMessage(chat_id, text='You have not active subscription')
        return
    if not args:
        bot.sendMessage(chat_id, text='Please write delay (in minutes) for the update')
        return
    try:
        delay = int(' '.join(args))
    except:
        bot.sendMessage(chat_id, text='Wrong format of number. It must be integer')
        return
    if delay < 10 or delay > 24*60:
        bot.sendMessage(chat_id, text='Delay must be less than 24 hours and more than 10 minutes')
        return
    job = forum_subscribers[telegram_user.id]
    job.interval = delay * 60
    users[telegram_user.id].job_posts_timeout = delay * 60
    bot.sendMessage(chat_id, text='Success! Update delay to ' + str(delay) + ' minutes.')
    users_store.store('users', users)


def stop_forum_subscription(bot, update):
    chat_id = update.message.chat_id
    telegram_user = update.message.from_user
    if chat_id not in forum_subscribers:
        bot.sendMessage(chat_id, text='You have not started subscription')
        return
    del_forum_job(chat_id)
    users[telegram_user.id].job_check_posts = False
    bot.sendMessage(chat_id, text='Subscription stopped')
    log_params('stop_forum_subscription', update)
    users_store.store('users', users)


def check_new_posts_from_list(bot, job):
    user_info = users[job.context]
    up_time = user_info.last_forum_post_check
    post_list = []
    is_message_send = False
    for post in posts_from_forum:
        post_time = datetime.strptime(post[4], '%a, %d %b %Y %H:%M:%S %Z')
        post_time_gmt = post_time.replace(tzinfo=pytz.timezone('GMT'))
        if post_time_gmt > up_time:
            post_list.append(post)
    for post in post_list:
        msg = uni_forum.create_message_from_post(post)
        bot.sendMessage(job.context, text=msg, parse_mode=telegram.ParseMode.MARKDOWN)
        is_message_send = True
    if is_message_send:
        users[job.context].last_forum_post_check = datetime.now(tz=pytz.timezone('GMT'))
        users_store.store('users', users)


def del_posts_from_list(bot, job):
    now_time = datetime.now(tz=pytz.timezone('GMT'))
    i = 0
    while True:
        posts_list_len = len(posts_from_forum)
        if i == posts_list_len:
            break
        post = posts_from_forum[i]
        post_time = datetime.strptime(post[4], '%a, %d %b %Y %H:%M:%S %Z').replace(tzinfo=pytz.timezone('GMT'))
        if now_time - post_time >= timedelta(days=1):
            posts_from_forum.remove(post)
        else:
            i += 1


def check_new_posts_rss(bot, job):
    global last_check_new_posts
    global posts_from_forum
    post_list = uni_forum.get_posts_rss(last_check_new_posts)
    posts_from_forum.extend(post_list)
    last_check_new_posts = datetime.now(tz=pytz.timezone('GMT'))


def forum_auth(bot, update, args):
    if len(args) == 2:
        uni_forum.forum_auth(args[0], args[1])
    else:
        bot.sendMessage(update.message.chat_id, text='Two arguments required')


def main():
    token = init_bot.read_token()
    updater = Updater(token)

    global komsostav
    komsostav = init_bot.read_komsostav()

    global users
    users = users_store.restore('users')
    if users is None:
        users = {}

    global last_check_new_posts
    last_check_new_posts = datetime.now(tz=pytz.timezone('GMT'))
    for user_id in users:
        user_info = users[user_id]
        if user_info.last_forum_post_check < last_check_new_posts:
            last_check_new_posts = user_info.last_forum_post_check

    job_queue = updater.job_queue
    job = Job(check_new_posts_rss, UPDATE_FORUM_POSTS_TIMEOUT_SEC, repeat=True)
    check_new_posts_rss(updater.bot, job)
    job_queue.put(job)
    job_del_posts = Job(del_posts_from_list, DEL_FORUM_POSTS_TIMEOUT_SEC, repeat=True)
    job_queue.put(job_del_posts)

    for user_id in users:
        user_info = users[user_id]
        if user_info.job_check_posts:
            add_forum_job(user_info.user.id, job_queue)
        if user_info.check_meetings:
            meeting_subscribers.append(user_info.user.id)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("help", bot_help))
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("get_game", get_games, pass_args=True))
    dp.add_handler(CommandHandler("start_forum_subscription", start_forum_subscription, pass_job_queue=True))
    dp.add_handler(CommandHandler("stop_forum_subscription", stop_forum_subscription))
    dp.add_handler(CommandHandler("start_meeting_subscription", start_meeting_subscription))
    dp.add_handler(CommandHandler("stop_meeting_subscription", stop_meeting_subscription))
    dp.add_handler(CommandHandler("create_meeting", create_meeting, pass_args=True))
    dp.add_handler(CommandHandler("change_update_delay", change_forum_delay, pass_args=True))
    dp.add_handler(CallbackQueryHandler(callback_query))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
