import pickle
import itertools
import csv
import logging
from collections import OrderedDict

stream_handler_simple = logging.StreamHandler()

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

log = logging.getLogger("basic")
log.setLevel(logging.INFO)
log.addHandler(stream_handler_simple)


def save_object(obj, filename):
    with open(filename, 'wb') as output:
        pickle.dump(obj, output, pickle.HIGHEST_PROTOCOL)


def load_object(filename):
    with open(filename, 'rb') as input:
        obj = pickle.load(input)
        return obj


def flat(lst):
    return [item for sublist in lst for item in sublist]


def load_cost(dfile):
    with open(dfile, 'rb') as f:
        log.debug("reading data file %s:" % f.name)
        reader = csv.reader(f, delimiter=';')

        result = []
        for row in reader:
            log.debug("row: %s", row)
            e = dict(f=row[0], v=float(row[1]), p=float(row[2]))
            result.append(e)

        return result


def convert(dfile):
    """
    duplicates = [{"f": "a", "v": 25, "p": 2.1},
              {"f": "a", "v": 25, "p": 5.1},
              {"f": "a", "v": 100, "p": 22.1},
              {"f": "b", "v": 25, "p": 2.1},
              {"f": "b", "v": 25, "p": 3.1}]
    """

    duplicates = load_cost(dfile)
    r = dict()

    for e in duplicates:
        f = e['f']
        v = e['v']
        p = e['p']

        if f not in r:
            r[f] = dict()

        if v not in r[f]:
            r[f][v] = p

    for k, v in r.iteritems():
        _ = []
        for k1, v1 in v.iteritems():
            _.append((k1, v1))
        _ = sorted(_, key=lambda x: x[1])
        r[k] = flat(_)

    return r


def get_shipping_costs(costs_table, country):
    return costs_table[country]


SHIPPING_TABLES = convert("shipping_costs_updated.csv")

"""
products = {
    'chandra': dict(articles=load_object('chandras.pkl'), quant=4),
    'chandra1': dict(articles=load_object('chandras.pkl'), quant=41)
}
"""

products = load_object('articles.pkl')

def key_fn(el):
    return el['seller']['username']


def country_fn(el):
    return el['seller']['country']


def language_filter(languages={'English'}):
    return lambda x: x['language']['languageName'] in languages


def foil_filter(is_foil=False):
    return lambda x: x['isFoil'] == is_foil


def condition_filter(condition={'NM'}):
    return lambda x: x['condition'] in condition


def apply_filters(filter_lst, lst):
    for f in filter_lst:
        lst = [x for x in lst if f(x)]
    return list(lst)


stores = []
stores_country = []
results = OrderedDict()
for p_name, product in products.iteritems():
    data = apply_filters([language_filter(languages={'English'}), foil_filter(is_foil=False)], product['articles'])

    #data = filter(lambda el: el['language']['languageName'] in {"English"} and el['isFoil'] == False, chandras)

    data = sorted(data, key=key_fn)
    data = itertools.groupby(data, key_fn)

    result = {}
    for store, group in data:
        inner = []
        country = ""
        for el in group:
            country = el['seller']['country']
            if el['isPlayset']:
                #inner.append([el['price'] / (el['count'] * 4), el['count'] * 4])
                #inner.append([el['price'] / 4.0, el['count'] * 4])
                inner.append([el['price'], el['count'], 4])
            else:
                inner.append([el['price'], el['count'], 1])
        result[store] = dict(store=store, country=country, prices=sorted(inner, key=lambda x: x[0] / float(x[2])))
        if not store in stores:
            stores.append(store)
            stores_country.append(country)

        if country in {'CA', 'SG'}:
            print "%s: %s" % (store, country)

    results[product['pretty_name']] = (result, product['quant'])

with open('s_input4.txt', 'w') as output:
    for el in stores:
        output.write("%s" % (el))
        output.write('\n')

    output.write('\n')

    for p_name in results:
        output.write(p_name)
        output.write('\n')

    output.write('\n')

    for country in stores_country:
        output.write(" ".join([str(i) for i in get_shipping_costs(SHIPPING_TABLES, country)]))
        output.write('\n')

    output.write('\n')


    i = 0
    total = len(results)
    for p_name, (result, quant) in results.iteritems():
        i += 1
        output.write(str(quant))
        if i < total:
            output.write(' ')

    output.write('\n')
    output.write('\n')

    for p_name, (result, _) in results.iteritems():
        for store in stores:
            try:
                el_price = flat(result[store]['prices'])
                output.write("%s" % (" ".join(str(i) for i in el_price)))
            except KeyError:
                output.write('#not available in this store')
            output.write('\n')
        output.write('\n')

    output.write('\n')



