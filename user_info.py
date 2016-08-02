import uni_forum
import logging
import pytz
import telegram
from datetime import datetime

UPDATE_TIMEOUT_SEC = 1. * 60  # 10 min

logger = logging.getLogger(__name__)


class UserInfo:
    def __init__(self, user):
        self.user = user
        self.listener = None
        self.last_updated = None
        self.job_check_posts = None
        self.job_posts_timeout = UPDATE_TIMEOUT_SEC
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