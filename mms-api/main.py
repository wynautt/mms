import os
import time
import logging
import httplib

from decimal import Decimal

import random

from google.appengine.runtime import DeadlineExceededError
from google.appengine.api import memcache
from google.appengine.api import mail

import simplejson as json
import requests
from requests_oauthlib import OAuth1

import numpy as np


from jinja2 import Environment, FileSystemLoader
from bottle import Bottle, request, HTTPError

from utils import get_first, get_normalized_ranges

from bokeh.plotting import figure, gridplot
from bokeh.embed import components
from bokeh.models import HoverTool, PanTool, WheelZoomTool, BoxZoomTool, ResetTool, ResizeTool, PreviewSaveTool, CrosshairTool, Range1d, LinearAxis

from model2 import ProductStats, ProductInfo, ProductAlerts
from services import cron_get_next_job
import services


httplib.HTTPConnection.debuglevel = 0

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.CRITICAL)
requests_log.propagate = True


API_KEYS = {
    'api_user': dict(
        APP_TOKEN='xxx',
        APP_SECRET='xxx',
        ACCESS_TOKEN='xxx',
        ACCESS_SECRET='xxx'
    )
}


ALERT_SENDER = "daily-alerts@mms-api-1043.appspotmail.com"
USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Iron/32.0.1750.1 Chrome/32.0.1750.1 Safari/537.36'
MKM_API_BASE_URL = "https://www.mkmapi.eu/ws/v1.1/output.json/"

SET_ABBRV = {
    "khans of tarkir": "KTK",
    "battle for zendikar": "BFZ",
    "zendikar expeditions": "EXP",
    "magic origins": "ORI",
    "theros": "THS",
    "dragons of tarkir": "DTK",
    "oath of the gatewatch": "OGW"
}


def get_set_abbrv(set):
    return SET_ABBRV.get(set, set)


def get_random_mkm_tokens():
    key = random.choice(list(API_KEYS.keys()))
    logging.info("Using keys from %s: %s" % (key, API_KEYS[key]['APP_TOKEN']))
    return API_KEYS[key]




JINJA_ENVIRONMENT = Environment (
    loader=FileSystemLoader(os.path.dirname(__file__) + '/templates'),
    extensions=['jinja2.ext.autoescape'],
    autoescape=False)


bottle = Bottle(catchall=False)

# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

def get_full_url(*args):
    return MKM_API_BASE_URL + "/".join(str(i) for i in args)

#DECORATORS
########################################

def mkm_get(key=None):
    #print "decorator with key: " + key
    def decorate(f):
        #print "decorating function: " + f.__name__
        def inner(*args, **kwargs):
            #print "calling inner function with args"
            url = get_full_url(*f(*args, **kwargs))
            api_keys = get_random_mkm_tokens()
            APP_TOKEN = api_keys['APP_TOKEN']
            APP_SECRET = api_keys['APP_SECRET']
            ACCESS_TOKEN = api_keys['ACCESS_TOKEN']
            ACCESS_SECRET = api_keys['ACCESS_SECRET']
            auth = OAuth1(APP_TOKEN, APP_SECRET, ACCESS_TOKEN, ACCESS_SECRET, realm=url)
            result = requests.get(url, auth=auth, timeout=30)
            #check for 200 and proper json
            if key:
                return json.loads(result.content)[key]
            return json.loads(result.content)
        return inner
    return decorate


def persist(mapper, cls, key, duplicate=False, singleton=False):
    def wrapper(f):
        def inner(*args, **kwargs):
            items = f(*args, **kwargs)
            if singleton:
                items = [items]
            for item in items:
                new_item = mapper(item)
                #TODO lower case where with multiple types (string, int, etc...)
                #TODO use in with only one query
                if duplicate or cls.q("where %s = :1" % key, new_item[key]).count() == 0:
                    cls(**new_item).save()
            return items
        return inner
    return wrapper



def rate_limit(max_per_second=2):
    min_interval = 1.0 / float(max_per_second)
    def decorate(f):
        last_time_called = [0.0]
        def inner(*args, **kwargs):
            elapsed = time.clock() - last_time_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = f(*args, **kwargs)
            last_time_called[0] = time.clock()
            return ret
        return inner
    return decorate


@bottle.route('/')
def hello():
    """Return a friendly HTTP greeting."""
    return 'Hello World!<br><br>Sample requests:<br> <p>/card/fireball</p> <p>/card/scalding+tarn</p> <p> /card/channel </p>'


@bottle.route('/__internal__/update')
def cron_update():
    logging.info("starting update")
    test_update_stats_with_expansions_one_by_one("khans of tarkir",
                                                 "battle for zendikar",
                                                 "zendikar expeditions",
                                                 "magic origins",
                                                 "theros",
                                                 "dragons of tarkir",
                                                 "oath of the gatewatch",
                                                 "shadows over innistrad",
                                                 "eternal masters",
                                                 "eldritch moon",
                                                 "kaladesh",
                                                 "kaladesh inventions",
                                                 "aether revolt")

@bottle.route('/__internal__/update/expansion/<expansion>')
def update_expansion(expansion):
    expansion = expansion.lower().replace(' ', '%20')
    get_all_cards_from_expansion(expansion)


@bottle.route('/__internal__/update_card/<name>')
def update_stats_with_set_and_name(name):
    name = name.lower()
    name = name.replace('%2F', '/')
    get_products(name=name.replace(' ', '+'))

@bottle.route('/__internal__/update_rarity')
def update_rariry():

    all = ProductInfo.query()
    for p in all:
        if p.rarity is None:
            logging.info("adding rarity 'rare' to %s" % p.name)
            p.rarity = 'rare'
            p.save()


@bottle.route('/card/<name>')
def get_info(name):
    url = "https://www.mkmapi.eu/ws/v1.1/output.json/products/%s/1/1/true" % name

    api_keys = get_random_mkm_tokens()
    APP_TOKEN = api_keys['APP_TOKEN']
    APP_SECRET = api_keys['APP_SECRET']
    ACCESS_TOKEN = api_keys['ACCESS_TOKEN']
    ACCESS_SECRET = api_keys['ACCESS_SECRET']

    auth = OAuth1(APP_TOKEN, APP_SECRET, ACCESS_TOKEN, ACCESS_SECRET, realm=url)
    r = requests.get(url, auth=auth)
    return r.content


@bottle.route('/info/<expansion>/<name>')
def get_product_info1(expansion, name):
    r = services.get_product_info(expansion=expansion, name=name)
    return dict(product=dict(id=r.id, name=r.name, expansion=r.set, rarity=r.rarity))


@bottle.route('/info/<expansion>')
def get_product_info2(expansion):
    if request.query.rarity:
        return get_product_info3(request.query.rarity, expansion)
    else:
        rs = services.get_expansion_products(expansion)
        return dict(product=[dict(id=r.id, name=r.name, expansion=r.set, rarity=r.rarity) for r in rs])


@bottle.route('/info/rarity/<rarity>/<expansion>')
def get_product_info3(rarity, expansion):
    rs = services.get_filtered_expansion_products(expansion, lambda x: x.rarity == rarity)
    return dict(product=[dict(id=r.id, name=r.name, expansion=r.set, rarity=r.rarity) for r in rs])


@rate_limit(max_per_second=1.0/30)
@bottle.route('/refresh/<set>/<name>')
def update_stats_with_set_and_name(set, name):

    name = name.lower()
    name = name.replace('%2F', '/')
    set = set.lower()

    time.sleep(random.randint(5, 120))

    product = memcache.get(key="product_%s_%s" % (set, name))

    if product is None:
        product = ProductInfo.get_by_set_and_name(set, name)
        if product:
            memcache.add(key="product_%s_%s" % (set, name), value=product)

    if not product:
        products = get_products(name=name.replace(' ', '+'))
        products = filter(lambda x: x['expansion'].lower() == set.lower(), products)
        product = get_first(products)
    else:
        product = get_product(product.id)

    if product and 'idProduct' in product:
        time.sleep(random.randint(5, 60))
        articles = get_articles(product['idProduct'])
        count_articles = sum(i['count'] for i in articles)
        count_foils = sum(i['count'] for i in articles if i['isFoil'])
        price_sell = product['priceGuide']['SELL']
        price_trend = product['priceGuide']['TREND']
        price_avg = product['priceGuide']['AVG']
        price_low = product['priceGuide']['LOW']
        price_lowex = product['priceGuide']['LOWEX']
        price_lowfoil = product['priceGuide']['LOWFOIL']

        _ = product_info_mapper(product)
        set, name = _['set'], _['name']

        p = ProductStats(name=name,
                         set=set,
                         c_total=count_articles,
                         c_foils=count_foils,
                         p_sell=price_sell,
                         p_trend=price_trend,
                         p_avg=price_avg,
                         p_low=price_low,
                         p_lowex=price_lowex,
                         p_lowfoil=price_lowfoil)
        p.save()


@bottle.route('/refresh/<expansion>')
def test_update_stats_with_expansions(*expansions):

    cards = ProductInfo.get_by_sets(expansions)
    rares = filter(lambda x: x.rarity in ('rare', 'mythic', 'special'), cards)

    idx = cron_get_next_job(rotate_at=len(rares)) - 1
    if idx < 0:
        idx = len(rares) - 1
    card = rares[idx]
    logging.info("replaying last update [%s of %s] %s" % (idx, len(rares), card.name))
    expansion, name = card.set, card.name
    update_stats_with_set_and_name(expansion, name)
    logging.info("replaying last update [%s of %s] %s - ok" % (idx, len(rares), card.name))

    idx = (idx + 1) % len(rares)

    try:
        while True:
            card = rares[idx]
            logging.info("updating card [%s of %s] %s" % (idx, len(rares), card.name))
            expansion, name = card.set, card.name
            update_stats_with_set_and_name(expansion, name)
            logging.info("updating card [%s of %s] %s - ok" % (idx, len(rares), card.name))
            idx = cron_get_next_job(rotate_at=len(rares))
    except DeadlineExceededError:
        return "finishing cron job"


def test_update_stats_with_expansions_one_by_one(*expansions):

    rares = memcache.get(key="rares")

    if rares is None:
        cards = ProductInfo.get_by_sets(expansions)
        #todo: sorting
        rares = filter(lambda x: x.rarity in ('rare', 'mythic', 'special'), cards)
        memcache.add(key="rares", value=rares)

    idx = cron_get_next_job(rotate_at=len(rares))
    card = rares[idx]
    logging.info("updating card [%s of %s] %s" % (idx, len(rares), card.name))
    expansion, name = card.set, card.name
    update_stats_with_set_and_name(expansion, name)
    logging.info("updating card [%s of %s] %s - ok" % (idx, len(rares), card.name))


@bottle.route('/refresh/<expansion>')
def update_stats_with_expansion(expansion):

    cards = ProductInfo.get_by_set(expansion)

    rares = filter(lambda x: x.rarity in ('rare', 'mythic', 'special'), cards)

    logging.info("updating %s cards" % len(rares))

    for card in rares:
        expansion, name = card.set, card.name
        logging.info("updating %s" % name)
        update_stats_with_set_and_name(expansion, name)
        logging.info("updating %s: ok" % name)

    return "ok"


@bottle.route('/stats/<set>/<name>')
def get_stats_with_set_and_name(set, name):
    name = name.replace('%2F', '/')
    ps = ProductStats.q("where name = :1 and set = :2 order by ts desc", name.lower(), set.lower())
    result = []
    for p in ps:
        result.append([p.name, p.timestamp_str, p.c_total, p.c_foils, p.p_trend, p.p_lowfoil])
    return json.dumps(result)


@bottle.route('/stats/plot')
def plot1():
    # prepare some data
    x = [1, 2, 3, 4, 5]
    y = [6, 7, 2, 4, 5]
    y2 = [1000, 1010, 1020, 1050, 1150]

    TOOLS = 'box_zoom,box_select,crosshair,resize,reset'

    # create a new plot with a title and axis labels
    plot = figure(title="simple line example", x_axis_label='x', y_axis_label='y', y_range=(0, 10), tools=TOOLS)

    # add a line renderer with legend and line thickness
    plot.line(x, y, legend="Temp.", line_width=2, color="blue")

    plot.extra_y_ranges = {"foo": Range1d(start=900, end=1200)}
    plot.circle(x, y2, color="red", y_range_name="foo")
    plot.add_layout(LinearAxis(y_range_name="foo"), 'right')

    script, div = components(plot)

    plot_template = JINJA_ENVIRONMENT.get_template('plot.template')
    r = plot_template.render(plot_script=script, plot_divs=div)

    return r


@bottle.route('/plot/<set>/<name>')
def get_stats_plot_from_set_and_name(set, name):
    name = name.replace('%2F', '/')
    ps = ProductStats.q("where name = :1 and set = :2 order by ts", name.lower(), set.lower())
    rawdata = map(lambda x: [x.timestamp, x.c_total, x.c_foils, x.p_trend, x.p_lowfoil], ps)

    if not rawdata:
        raise HTTPError(status=404)

    dates, total, foils, trend, lowfoil = map(np.array, zip(*rawdata))
    #aapl_dates = np.array(AAPL['date'], dtype=np.datetime64)

    window_size = 3
    window = np.ones(window_size, dtype=Decimal)/Decimal(window_size)
    avg_total, avg_trend, avg_foils, avg_lowfoil = map(lambda x: np.convolve(x, window, 'same'), [total, trend, foils, lowfoil])

    hover = HoverTool(
        tooltips=[
            ("(x,y)", "($x, $y)"),
        ]
    )

    p = figure(width=750, height=350, x_axis_type="datetime", tools=[HoverTool(), PanTool(), BoxZoomTool(), WheelZoomTool(), ResizeTool(), PreviewSaveTool(), ResetTool()])#, y_range=(1000, 1800))
    p.yaxis.axis_label='Availability'
    p.circle(dates, total, size=4)
    p.line(dates, avg_total, color='navy', legend='avg')

    p1 = figure(width=750, height=350, x_range=p.x_range, x_axis_type="datetime")#, y_range=(1, 25))
    p1.yaxis.axis_label='Price Trend'
    p1.circle(dates, trend, size=4)
    p1.line(dates, avg_trend, color='navy', legend='avg')

    p_f = figure(width=750, height=350, x_axis_type="datetime", tools=[HoverTool(), PanTool(), BoxZoomTool(), WheelZoomTool(), ResizeTool(), PreviewSaveTool(), ResetTool()])#, y_range=(1000, 1800))
    p_f.yaxis.axis_label='Availability Foils'
    p_f.circle(dates, foils, size=4)
    p_f.line(dates, avg_foils, color='navy', legend='avg')

    p1_f = figure(width=750, height=350, x_range=p_f.x_range, x_axis_type="datetime")#, y_range=(1, 25))
    p1_f.yaxis.axis_label='Price Low Foils'
    p1_f.circle(dates, lowfoil, size=4)
    p1_f.line(dates, avg_lowfoil, color='navy', legend='avg')

    p = gridplot([[p1, p1_f], [p, p_f]])

    script, div = components(p)

    plot_template = JINJA_ENVIRONMENT.get_template('plot.template')
    r = plot_template.render(plot_script=script, plot_divs=div)

    return r


@bottle.route('/plot2/<set>/<name>')
def get_stats_plot2_from_set_and_name(set, name):
    name = name.replace('%2F', '/')
    ps = ProductStats.q("where name = :1 and set = :2 order by ts", name.lower(), set.lower())
    rawdata = map(lambda x: [x.timestamp, x.c_total, x.c_foils, x.p_trend, x.p_lowfoil], ps)

    if not rawdata:
        raise HTTPError(status=404)

    dates, total, foils, trend, lowfoil = map(np.array, zip(*rawdata))
    #aapl_dates = np.array(AAPL['date'], dtype=np.datetime64)

    total_range, foils_range, trend_range, lowfoil_range = map(lambda x: get_normalized_ranges(int(min(x)), int(max(x)), 0.2), zip(*rawdata)[1:])

    window_size = 3
    window = np.ones(window_size, dtype=Decimal)/Decimal(window_size)
    avg_total, avg_trend, avg_foils, avg_lowfoil = map(lambda x: np.convolve(x, window, 'same'), [total, trend, foils, lowfoil])

    hover = HoverTool(
        tooltips=[
            ("(x,y)", "($x, $y)"),
        ]
    )

    TOOLS = "pan,wheel_zoom,box_zoom,reset,resize,crosshair,box_select"

    p1 = figure(width=950, height=350, x_axis_type="datetime", y_range=(trend_range[0], trend_range[1]), tools=[HoverTool(), CrosshairTool(), PanTool(), BoxZoomTool(), WheelZoomTool(), ResizeTool(), PreviewSaveTool(), ResetTool()])
    p1.yaxis.axis_label='Price Trend'
    p1.circle(dates, trend, size=4)
    p1.line(dates, avg_trend, color='navy', legend='Price Avg')

    p1.extra_y_ranges = {"foo": Range1d(start=total_range[0], end=total_range[1])}
    p1.circle(dates, total, color="red", y_range_name="foo")
    p1.line(dates, avg_total, color='red', legend='Availability Avg', y_range_name="foo")
    p1.add_layout(LinearAxis(y_range_name="foo", axis_label="Availability"), 'right')

    #Foils
    p1_f = figure(width=950, height=350, x_axis_type="datetime", y_range=(lowfoil_range[0], lowfoil_range[1]), tools=[HoverTool(), CrosshairTool(), PanTool(), BoxZoomTool(), WheelZoomTool(), ResizeTool(), PreviewSaveTool(), ResetTool()])
    p1_f.yaxis.axis_label='Price Low Foils'
    p1_f.circle(dates, lowfoil, size=4)
    p1_f.line(dates, avg_lowfoil, color='navy', legend='Price Avg')

    p1_f.extra_y_ranges = {"foo": Range1d(start=foils_range[0], end=foils_range[1])}
    p1_f.circle(dates, foils, color="red", y_range_name="foo")
    p1_f.line(dates, avg_foils, color='red', legend='Availability Avg', y_range_name="foo")
    p1_f.add_layout(LinearAxis(y_range_name="foo", axis_label="Availability"), 'right')

    #p = gridplot([[p, p1], [p_f, p1_f]])
    #p = hplot(p1, p1_f)
    p = gridplot([[p1, None], [p1_f, None]])

    script, div = components(p)

    plot_template = JINJA_ENVIRONMENT.get_template('plot.template')
    r = plot_template.render(plot_script=script, plot_divs=div)

    return r


@bottle.route('/subscribe/<email>/<set>/<name>')
def subscribe_product_alerts(set, name, email):
    set = set.lower()
    name = name.lower()
    name = name.replace('%2F', '/')

    if mail.is_email_valid(email):
        alert = ProductAlerts(set=set,
                              name=name,
                              to_email=email,
                              is_active=True)
        alert.save()
        return "ok"

    return "not ok"


def gen_key(set, name):
    return "%s-%s" % (set, name)


@bottle.route('/__internal__/send_product_alert_reports')
def send_product_alert_reports():
    alerts = ProductAlerts.get_all_active()
    reports_for_products = dict()
    reports_for_emails = dict()

    for i in alerts:
        report = reports_for_products.get(gen_key(i.set, i.name))
        if report is None:
            report = generate_report_for_product(i.set, i.name)
            reports_for_products[gen_key(i.set, i.name)] = report

        if reports_for_emails.get(i.to_email) is None:
            reports_for_emails[i.to_email] = []

        reports_for_emails[i.to_email].append(report)

    template = JINJA_ENVIRONMENT.get_template('alert_email.template')
    for email in reports_for_emails.keys():
        body = template.render(data=reports_for_emails[email])
        logging.info("Sending email to %s with data %s" % (email, body))
        mail.send_mail(ALERT_SENDER, email, "[MMS API] Daily Analysis", "", html=body)
        #return body

    return "ok"


def generate_report_for_product(set, name):
    all_stats = ProductStats.get_by_set_and_name(set, name)
    all_stats_projection = [[s.p_trend, s.c_total, s.p_sell, s.p_low, s.p_avg] for s in all_stats]

    report = dict()
    if len(all_stats_projection) >= 2:
        report['daily_p_trend_var'] = round((all_stats_projection[0][0] - all_stats_projection[1][0]) / all_stats_projection[1][0] * 100, 2)
        report['daily_c_total_var'] = round((all_stats_projection[0][1] - all_stats_projection[1][1]) / float(all_stats_projection[1][1]) * 100, 2)

    if len(all_stats_projection) >= 7:
        report['weekly_p_trend_var'] = round((all_stats_projection[0][0] - all_stats_projection[6][0]) / all_stats_projection[6][0] * 100, 2)
        report['weekly_c_total_var'] = round((all_stats_projection[0][1] - all_stats_projection[6][1]) / float(all_stats_projection[6][1]) * 100, 2)

    for _ in all_stats:
        report['current_value'] = _
        break

    report['set'] = get_set_abbrv(set)
    report['name'] = name

    return report


def product_info_mapper(product):
    """

    :param product: MKM API Product
    :return:
    """
    return dict(id=product['idProduct'],
                name=product['name']['1']['productName'].lower(),
                set=product['expansion'].lower(),
                rarity=product['rarity'].lower())


@persist(mapper=product_info_mapper, cls=ProductInfo, key='id')
@mkm_get('product')
def get_products(name):
    return 'products', name, 1, 1, 'true'


@mkm_get('article')
def get_articles(id):
    return 'articles', id


@mkm_get('product')
def get_product(id):
    return 'product', id


@persist(mapper=product_info_mapper, cls=ProductInfo, key='id')
@mkm_get('card')
def get_all_cards_from_expansion(name):
    return 'expansion', 1, name




# Define an handler for 404 errors.
@bottle.error(404)
def error_404(error):
    """Return a custom 404 error."""
    return 'Sorry, nothing at this URL.'


from google.appengine.ext import deferred
from update_schema import update_schema_product_stats_float_to_decimal2

@bottle.route("/__internal__/update_schema")
def update_schema():
    deferred.defer(update_schema_product_stats_float_to_decimal2)
    #update_schema_product_stats_float_to_decimal()
    return "update started"


@bottle.route("/__internal__/count")
def _count():
    c = ProductStats.query().count()
    #update_schema_product_stats_float_to_decimal()
    return dict(count=c)



@bottle.route("/__internal__/query/<query>")
def _query(query):
    try:
        rs = services.execute_query(query)
        return dict(result=[[r.set, r.name] for r in rs])
    except Exception as e:
        return e.message


