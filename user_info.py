import logging
import pytz
from datetime import datetime

UPDATE_TIMEOUT_SEC = 2. * 60  # 10 min
logger = logging.getLogger(__name__)


class UserInfo:
    def __init__(self, user):
        self.user = user
        self.last_forum_post_check = datetime.now(tz=pytz.timezone('GMT'))
        self.job_check_posts = False
        self.job_posts_timeout = UPDATE_TIMEOUT_SEC
        self.sections = {}
