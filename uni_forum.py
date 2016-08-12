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
    for item in feed.entries:
        temp = item.published_parsed
        post_time = datetime(temp.tm_year, temp.tm_mon, temp.tm_mday, temp.tm_hour, temp.tm_min, temp.tm_sec)
        post_time_gmt = post_time.replace(tzinfo=pytz.timezone('GMT'))
        if post_time_gmt < up_time:
            break
        s = requests.Session()
        message_id = item.link[item.link.find('#')+4:]
        soup = BeautifulSoup(s.get(item.link).text, "html5lib")
        post_text = soup.find('div', {'id': 'msg_' + message_id}, {'class': 'inner'}).text
        author = soup.find('ul', {'id': 'msg_' + message_id + '_extra_info'}).parent.find('a').text
        post_list.append([item.tags[0].term, item.title_detail.value, item.summary, item.link, item.published, author,
                          post_text])
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
            '</a': '>',
            '<blockquote': '>',
            '</blockquote': '>',
            '<span': '>',
            '</span': '>'
            }
    idx_tag = message.find('<b>')
    if idx_tag >= 0:
        message = message[:idx_tag] + '*' + message[idx_tag + 3:]
        idx_tag = message.find('</b>')
        message = message[:idx_tag] + '*' + message[idx_tag + 4:]

    idx_tag = message.find('<i>')
    if idx_tag >= 0:
        message = message[:idx_tag] + '_' + message[idx_tag + 3:]
        idx_tag = message.find('</i>')
        message = message[:idx_tag] + '_' + message[idx_tag + 4:]

    for start_tag in tags:
        idx_start = message.find(start_tag)
        while idx_start >= 0:
            finish_tag = tags[start_tag]
            idx_finish = message.find(finish_tag, idx_start)
            message = message[:idx_start] + message[idx_finish + len(finish_tag):]
            idx_start = message.find(start_tag)
    return message


def create_message_from_post(post):
    msg = ''
    msg += '*' + post[5] + ':*' + '\n'
    msg += '*' + post[0] + '*' + '\n'
    msg += '*' + post[1] + '*' + '\n'
    msg += '' + message_process(post[6]) + '\n'
    # msg += '\t' + post[4] + '\n'
    return msg
