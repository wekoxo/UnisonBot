import requests
import base64
from bs4 import BeautifulSoup
import feedparser
import pytz
from datetime import datetime


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


def get_posts(up_time):
    post_list = []
    feed = feedparser.parse(url + "/index.php?action=.xml;type=rss")
    for item in feed.entries:
        temp = item.published_parsed
        post_time = datetime(temp.tm_year, temp.tm_mon, temp.tm_mday, temp.tm_hour, temp.tm_min, temp.tm_sec)
        post_time_gmt = post_time.replace(tzinfo=pytz.timezone('GMT'))
        if post_time_gmt >= up_time:
            post_list.append([item.tags[0].term, item.title_detail.value, item.summary, item.link, item.published])
    return post_list
