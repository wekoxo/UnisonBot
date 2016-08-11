import requests
from bs4 import BeautifulSoup
import pytz
from datetime import datetime
import feedparser

url = "http://forum.spounison.ru"


def forum_auth(login, password):
    s = requests.Session()
    data = {"user": login, "passwrd": password}
    s.post(url + "/index.php?action=login2", data=data)
    r = s.get(url).text
    soup = BeautifulSoup(r, "html5lib")
    print(soup)
    return s


def get_forum_sections():
    sections_list = []
    s = requests.Session()
    soup = BeautifulSoup(s.get(url).text, "html5lib")
    for item in soup.find('div', {'id': 'main_content_section'}).find_all('tr', {'class': 'windowbg2'}):
        sections_list.append(item.find('td', {'class': 'info'}).find('a').text)
    return sections_list


def get_posts_rss(up_time):
    post_list = []
    feed = feedparser.parse(url + "/index.php?action=.xml;type=rss")
    s = requests.Session()
    for item in feed.entries:
        temp = item.published_parsed
        post_time = datetime(temp.tm_year, temp.tm_mon, temp.tm_mday, temp.tm_hour, temp.tm_min, temp.tm_sec)
        post_time_gmt = post_time.replace(tzinfo=pytz.timezone('GMT'))
        if post_time_gmt >= up_time:
            break
        message_id = item.link[item.link.find('#')+4:]
        soup = BeautifulSoup(s.get(item.link).text, "html5lib")
        author = soup.find('ul', {'id': 'msg_' + message_id + '_extra_info'}).parent.find('a').text
        post_list.append([item.tags[0].term, item.title_detail.value, item.summary, item.link, item.published, author])
    return post_list


def message_process(message):
    tags = {'<img': '/>',
            '<br': '/>',
            '<ul': '>',
            '</ul': '>',
            '<li': '>',
            '</li': '>',
            '<div': '>',
            '</div': '>',
            '<a': '>',
            '</a': '>'
            }
    for start_tag in tags:
        idx_start = message.find(start_tag)
        if idx_start >= 0:
            finish_tag = tags[start_tag]
            idx_finish = message.find(finish_tag, idx_start)
            message = message[:idx_start] + message[idx_finish + len(finish_tag):]
    return message
