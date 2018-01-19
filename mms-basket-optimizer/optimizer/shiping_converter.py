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


def load_cost(dfile):
    with open(dfile, 'rb') as f:
        log.debug("reading data file %s:" % f.name)
        reader = csv.reader(f, delimiter='\t')

        result = []
        i = 0
        for row in reader:
            log.debug("row: %s", row)
            if i == 0:
                print "header"
            else:
                row = [x.decode('utf-8').replace(u'\u20ac', '').replace(',', '.').strip() for x in row]
                if row[5] > 0:
                    e = [row[6], float(row[2]), float(row[5])]
                    result.append(e)
            i += 1

        return result


def sort_cmp(x, y):
    if x[0] == y[0]:
        if x[2] < y[2]:
            return -1
        else:
            return 1

    if x[0] < y[0]:
        return -1
    return 1


r = load_cost("../results/shipping_costs.csv")
r = sorted(r, cmp=sort_cmp)

with open('shipping_costs_updated.csv', 'w') as output:
    for el in r:
        output.write(";".join([str(x) for x in el]))
        output.write('\n')



