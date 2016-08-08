#!/usr/bin/python3
import logging
import get_game
import uni_forum
import telegram
import os
import pytz
from datetime import datetime
from storer import Storer
from user_info import UserInfo
from telegram.ext import Updater, CommandHandler, JobQueue, CallbackQueryHandler, Job

STORED_FILE = os.getenv('UNI_STORED_FILE', 'unison_bot_shelve.db')
TOKEN_FILENAME = os.getenv('UNI_TOKEN_FILE', 'token.lst')
KOMSOSTAV_FILENAME = os.getenv('UNI_KOMSOSTAV_FILE', 'komsostav.lst')

users = {}
users_store = Storer(STORED_FILE)
forum_subscribers = dict()
user_chat = dict()

job_queue = None

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
/get_game - Returns a random game from selected partition"""


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
        category = ''
        for i in args:
            category += i + ' '
        category = category.rstrip()
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
    bot.sendMessage(chat_id, text='Choose topic', reply_markup=reply_markup)


def send_message_with_game(bot, update, category):
    chat_id = update.message.chat_id
    game = get_game.get_random_game(category)
    bot.sendMessage(chat_id, text=game, parse_mode=telegram.ParseMode.MARKDOWN)


def game_from_inline_markup(bot, update):
    query = update.callback_query
    game = get_game.get_random_game(query.data)
    bot.editMessageText(text=game, chat_id=query.message.chat_id, message_id=query.message.message_id,
                        parse_mode=telegram.ParseMode.MARKDOWN)


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
    bot.sendMessage(chat_id, text='Subscription start')
    log_params('start_forum_subscription', update)
    users_store.store('users', users)


def add_forum_job(user_id, jobs):
    user_info = users[user_id]
    job = Job(check_new_posts_rss, user_info.job_posts_timeout, repeat=True, context=user_id)
    forum_subscribers[user_id] = job
    jobs.put(job)


def stop_forum_subscription(bot, update):
    chat_id = update.message.chat_id
    telegram_user = update.message.from_user
    if chat_id not in forum_subscribers:
        bot.sendMessage(chat_id, text='You have not started subscription')
        return
    job = forum_subscribers[chat_id]
    job.schedule_removal()
    users[telegram_user.id].job_check_posts = False
    del forum_subscribers[chat_id]
    bot.sendMessage(chat_id, text='Subscription stop')
    log_params('stop_forum_subscription', update)
    users_store.store('users', users)


def check_new_posts_rss(bot, job):
    user_info = users[job.context]
    up_time = user_info.last_forum_post_check
    post_list = uni_forum.get_posts_rss(up_time)
    users[job.context].last_forum_post_check = datetime.now(tz=pytz.timezone('GMT'))
    for post in post_list:
        msg = ''
        for item in post:
            if post.index(item) in {0, 1}:
                msg += '*' + item + '*' + '\n'
            else:
                msg += item + '\n'
        bot.sendMessage(job.context, text=msg)


def forum_auth(bot, update, args):
    if len(args) == 2:
        uni_forum.forum_auth(args[0], args[1])
    else:
        bot.sendMessage(update.message.chat_id, text='Two arguments required')


def read_token():
    f = open(TOKEN_FILENAME)
    token = f.readline().strip()
    f.close()
    return token


def read_komsostav():
    f = open(KOMSOSTAV_FILENAME)
    commander = f.readline().strip()
    commissar = f.readline().strip()
    f.close()
    return [commander, commissar]


def main():
    token = read_token()
    updater = Updater(token)
    global users
    users = users_store.restore('users')
    if users is None:
        users = {}
    job_queue = JobQueue(updater.bot)
    for user_id in users:
        user_info = users[user_id]
        if user_info.job_check_posts:
            add_forum_job(user_info.user.id, job_queue)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("help", bot_help))
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("get_game", get_games, pass_args=True))
    dp.add_handler(CommandHandler("start_subscription", start_forum_subscription, pass_job_queue=True))
    dp.add_handler(CommandHandler("stop_forum_subscription", stop_forum_subscription))
    dp.add_handler(CallbackQueryHandler(game_from_inline_markup))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
