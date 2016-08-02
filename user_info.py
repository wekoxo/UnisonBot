import uni_forum
import logging
import pytz
import telegram
from datetime import datetime

UPDATE_TIMEOUT_SEC = 10. * 60  # 10 min

logger = logging.getLogger(__name__)


class UserInfo:
    def __init__(self, user):
        self.user = user
        self.listener = None
        self.last_updated = None
        self.sections = {}
        self._int_update()

    def _int_update(self):
        self.last_updated = datetime.now(tz=pytz.timezone('GMT'))

    def set_listener(self, listener):
        if listener.__class__ != ForumListener:
            raise ValueError("Can't set %s as listener" % listener)
        self.listener = listener

    def check_new_posts(self):
        if self.last_updated:
            logger.info("Updating posts")
            post_list = uni_forum.get_posts(self.last_updated)
            for post in post_list:
                msg = ''
                for item in post:
                    if post.index(item) in {0, 1}:
                        msg += '*' + item + '*' + '\n'
                    else:
                        msg += item + '\n'
                self.listener.notify(msg)
            self.last_updated = datetime.now(tz=pytz.timezone('GMT'))
            return True
        else:
            logger.info("Can't update")
            return False


class ForumListener:
    def __init__(self, bot, chat_id):
        self.bot = bot
        self.chat_id = chat_id

    def notify(self, msg):
        self.bot.sendMessage(self.chat_id, text=msg, parse_mode=telegram.ParseMode.MARKDOWN)


#    def subscription_posts(bot_post=bot, update_post=update):
#        log_params('subscription_posts', update_post)
#        if notification.get(chat_id, 0) == 1:
#            post_list = uni_forum.get_posts(request_time[chat_id])
#            for post in post_list:
#                msg = ''
#                for item in post:
#                    if post.index(item) in {0, 1}:
#                        msg += '*' + item + '*' + '\n'
#                    else:
#                        msg += item + '\n'
#                bot_post.sendMessage(chat_id, text=msg, parse_mode=telegram.ParseMode.MARKDOWN)
#            request_time[chat_id] = datetime.now(tz=pytz.timezone('GMT'))
#
#    if notification.get(chat_id, 0) == 1:
#        bot.sendMessage(chat_id, text='You are already subscribed')
#    else:
#        log_params('start_subscription', update)
#        f_notification = open('notification.txt', 'a')
#        notification[chat_id] = 1
#       f_notification.write(str(chat_id) + ' 1 \n')
#        f_notification.close()


#        f_request_time = open('request_time.txt', 'a')
#        dt = datetime.now(tz=pytz.timezone('GMT'))
#        request_time[chat_id] = dt
#        f_request_time.write(str(chat_id) + ' ' + datetime.strftime(dt, '%Y-%m-%d %H:%M:%S') + ' \n')
#        f_request_time.close()

#        bot.sendMessage(update.message.chat_id, text='Subscription successfully added')
#        job_queue.put(subscription_posts, 900, repeat=True)
#f_notification = open('notification.txt', 'r')
#    f_request_time = open('request_time.txt', 'r')
#    for line in f_notification:
#        dict_line = line.split(' ')
#        notification[int(dict_line[0])] = int(dict_line[1])
#    f_notification.close()

#    for line in f_request_time:
#        dict_line = line.split(' ')
#        request_time[int(dict_line[0])] = datetime.strptime((dict_line[1] + ' ' + dict_line[2]), '%Y-%m-%d %H:%M:%S')
#    f_request_time.close()