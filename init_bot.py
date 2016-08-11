import os

TOKEN_FILENAME = os.getenv('UNI_TOKEN_FILE', 'token.lst')
KOMSOSTAV_FILENAME = os.getenv('UNI_KOMSOSTAV_FILE', 'komsostav.lst')


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