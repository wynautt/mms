import sys

sys.path.insert(0, "libs")

import requests
import logging
import httplib
import pickle
import json
import hashlib
import os

httplib.HTTPConnection.debuglevel = 0

requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.CRITICAL)
requests_log.propagate = True
stream_handler_simple = logging.StreamHandler()

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

log = logging.getLogger("basic_MKMAPI")
log.setLevel(logging.DEBUG)
log.addHandler(stream_handler_simple)

from requests_oauthlib import OAuth1


API_KEYS = {
    'awaken': dict(
        APP_TOKEN='xxx',
        APP_SECRET='xxx',
        ACCESS_TOKEN='xxx',
        ACCESS_SECRET='xxx'
    )
}


USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Iron/32.0.1750.1 Chrome/32.0.1750.1 Safari/537.36'
headers = {'User-Agent': USER_AGENT}

api_keys = API_KEYS['awaken']
APP_TOKEN = api_keys['APP_TOKEN']
APP_SECRET = api_keys['APP_SECRET']
ACCESS_TOKEN = api_keys['ACCESS_TOKEN']
ACCESS_SECRET = api_keys['ACCESS_SECRET']

MKM_API_BASE_URL = "https://www.mkmapi.eu/ws/v1.1/output.json/"


def get_full_url(*args):
    return MKM_API_BASE_URL + "/".join(str(i) for i in args)


def mkm_get(key):
    def decorate(f):
        def inner(*args, **kwargs):
            url = get_full_url(*f(*args, **kwargs))
            auth = OAuth1(APP_TOKEN, APP_SECRET, ACCESS_TOKEN, ACCESS_SECRET, realm=url)
            result = requests.get(url, auth=auth)
            log.debug("Getting %s with result %s" % (url, result))
            if key:
                return json.loads(result.content)[key]
            return json.loads(result.content)
        return inner
    return decorate


def save_object(obj, filename):
    with open(filename, 'wb') as output:
        pickle.dump(obj, output, pickle.HIGHEST_PROTOCOL)
        output.close()


def load_object(filename):
    with open(filename, 'rb') as input:
        obj = pickle.load(input)
        return obj


@mkm_get('product')
def get_products(name):
    return 'products', name, 1, 1, 'true'


@mkm_get('product')
def get_product(id):
    return 'product', id


@mkm_get('article')
def get_articles(id):
    return 'articles', id


def refresh_articles(articles_list):
    log.info("Refresing articles from: %s" % articles_list)
    articles_map = {}

    for name, sets, quant in articles_list:
        mkm_search_name = name.replace(' ', '+').replace(',', '%2C').replace("'", "")
        products = get_products(mkm_search_name)
        products = [x for x in products if x['expansion'] == sets]

        #TODO save data from all sets and filter when fetching from filesystem
        p = products[0]
        p_name = p['name']['1']['productName']
        p_id = p['idProduct']

        articles = get_articles(p_id)
        articles_map[name] = dict(pretty_name=p_name, articles=articles, quant=quant)

    return articles_map


def get_input_data(articles_list, refresh=False):
    articles_list_hashable = map(lambda x: (x[0], x[1]), articles_list)
    articles_list_hashable = sorted(articles_list_hashable)

    filename = hashlib.md5(json.dumps(articles_list_hashable, sort_keys=True)).hexdigest()

    if refresh or not os.path.isfile("input/%s.pkl" % filename):
        r = refresh_articles(articles_list)
        save_object(r, "input/%s.pkl" % filename)
        return r

    log.info("Getting articles from %s" % filename)
    r = load_object("input/%s.pkl" % filename)
    for name, sets, quant in articles_list:
        r[name]['quant'] = quant
    return r
