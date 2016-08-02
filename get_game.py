from bs4 import BeautifulSoup
from urllib.request import urlopen
from urllib.parse import quote_plus
from random import randint

url = 'http://wiki.spounison.ru'


def get_random_game(request_string):
    soup = BeautifulSoup(urlopen(url), "html5lib")

    for i in soup.findAll('li'):
        if i.next.string.find(request_string) >= 0:
            page = urlopen(url + '/index.php/' + quote_plus('Категория:' + i.next.string.replace(' ', '_')))
            soup = BeautifulSoup(page, "html5lib")

    row = soup.find("div", {"class": "mw-content-ltr"}).find_all("li")

    page = urlopen(url + '/index.php/' + quote_plus(row[randint(0, len(row) - 1)].string.replace(' ', '_')))
    soup = BeautifulSoup(page, "html5lib")
    response = '*' + soup.find("h1", {"id": "firstHeading"}).text + '*' + '\n'
    response += soup.find("div", {"id": "mw-content-text"}).text.replace('\n', ' ')
    return response


def get_games_category():
    soup = BeautifulSoup(urlopen(url), "html5lib")
    response = []

    for item in soup.find_all(
            lambda tag: tag.name == 'li' and
            tag.next.string.find('Игры') >= 0):
        response.append(item.next.string)
    return response
