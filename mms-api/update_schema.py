import logging
import model2 as model
from google.appengine.ext import deferred
from google.appengine.ext import ndb

PAGE_SIZE = 100  # ideal batch size may vary based on entity size.
PRECISION = 2

def update_schema_product_stats_float_to_decimal(cursor=None, num_updated=0):

    logging.info('Starting update, updated until now: %d', num_updated)

    logging.error("raising stop task")

    raise deferred.PermanentTaskFailure()

    rs, next_cursor, more = model.ProductStats.query().fetch_page(PAGE_SIZE, start_cursor=cursor)

    to_put = []
    for r in rs:
        logging.debug("updating %s (%s - %s)",  r.timestamp, r.set, r.name)
        r.p_sell=int(round(r.p_sell * (10 ** PRECISION)))
        r.p_trend=int(round(r.p_trend * (10 ** PRECISION)))
        r.p_avg=int(round(r.p_avg * (10 ** PRECISION)))
        r.p_low=int(round(r.p_low * (10 ** PRECISION)))
        r.p_lowex=int(round(r.p_lowex * (10 ** PRECISION)))
        r.p_lowfoil=int(round(r.p_lowfoil * (10 ** PRECISION)))
        to_put.append(r)

    if to_put:
        ndb.put_multi(to_put)
        num_updated += len(to_put)
        logging.info('Put %d entities to Datastore for a total of %d updated', len(to_put), num_updated)

    if more and next_cursor:
        deferred.defer(update_schema_product_stats_float_to_decimal, cursor=next_cursor, num_updated=num_updated)
    else:
        logging.info('UpdateSchema complete with %d updates!', num_updated)



def update_schema_product_stats_float_to_decimal2(cursor=None, num_updated=0):

    logging.info('Starting update with cursor %s, updated until now: %d', cursor, num_updated)

    rs, next_cursor, more = model.ProductStats.query().fetch_page(PAGE_SIZE, start_cursor=cursor)

    to_put = []
    for r in rs:
        if any(map(lambda x: isinstance(x, float), [r.p_sell, r.p_low, r.p_avg, r.p_lowex, r.p_trend, r.p_lowfoil])):
            logging.debug("updating %s (%s - %s)",  r.timestamp, r.set, r.name)
            r.p_sell=int(round(r.p_sell * (10 ** PRECISION)))
            r.p_trend=int(round(r.p_trend * (10 ** PRECISION)))
            r.p_avg=int(round(r.p_avg * (10 ** PRECISION)))
            r.p_low=int(round(r.p_low * (10 ** PRECISION)))
            r.p_lowex=int(round(r.p_lowex * (10 ** PRECISION)))
            r.p_lowfoil=int(round(r.p_lowfoil * (10 ** PRECISION)))
            to_put.append(r)

    if to_put:
        ndb.put_multi(to_put)
        num_updated += len(to_put)
        logging.info('Put %d entities to Datastore for a total of %d updated', len(to_put), num_updated)

    if more and next_cursor:
        deferred.defer(update_schema_product_stats_float_to_decimal2, cursor=next_cursor, num_updated=num_updated)
    else:
        logging.info('UpdateSchema complete with %d updates!', num_updated)


#deferred.PermanentTaskFailure