#!/usr/bin/python3
import logging
import get_game
import uni_forum
import telegram
import os
from storer import Storer
from user_info import UserInfo, ForumListener
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

POSTS_CHECK_INTERVAL_SEC = 900  # 15 min
STORED_FILE = os.getenv('UNI_STORED_FILE', 'unison_bot_shelve.db')
TOKEN_FILENAME = os.getenv('UNI_TOKEN_FILE', 'token.lst')

# Define the different states a chat can be in
MENU, AWAIT_INPUT_GAME = range(2)

users = {}
storer = Storer(STORED_FILE)
state = dict()
job_queue = None

# Enable Logging
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
    chat_state = state.get(chat_id, MENU)

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
            state[chat_id] = AWAIT_INPUT_GAME
    elif text[0] == '/':
        game_markup(bot, update)
        state[chat_id] = AWAIT_INPUT_GAME


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
    state[chat_id] = MENU


def game_from_category(bot, update):
    query = update.callback_query
    game = get_game.get_random_game(query.data)
    bot.editMessageText(text=game, chat_id=query.message.chat_id, message_id=query.message.message_id,
                        parse_mode=telegram.ParseMode.MARKDOWN)


def start_forum_subscription(bot, update):
    telegram_user = update.message.from_user
    if telegram_user.id not in users:
        users[telegram_user.id] = UserInfo(telegram_user)
        users[telegram_user.id].set_listener(ForumListener(bot=bot, chat_id=update.message.chat_id))
        bot.sendMessage(update.message.chat_id, text='Subscription start')
        log_params('start_forum_subscription', update)
        storer.store('users', users)


def check_new_posts(update):
    for user in users.values():
        user.check_new_posts()


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


def main():
    global users
    users = storer.restore('users')
    if users is None:
        users = {}

    global job_queue

    token = read_token()
    updater = Updater(token)

    job_queue = updater.job_queue
    job_queue.put(check_new_posts, POSTS_CHECK_INTERVAL_SEC, repeat=True)
    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add handlers for Telegram messages
    dp.addHandler(CommandHandler("help", bot_help))
    dp.addHandler(CommandHandler("start", start))
    dp.addHandler(CommandHandler("get_game", get_games, pass_args=True))
    dp.addHandler(CommandHandler("start_subscription", start_forum_subscription))
    dp.addHandler(CallbackQueryHandler(game_from_category))

    game_ans_handler = MessageHandler([Filters.text], get_games)
    dp.addHandler(game_ans_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
