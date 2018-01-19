from google.appengine.ext.ndb import *
from datetime import datetime as dt

from decimal import Decimal


#custom property with no support from GQL
class DecimalProperty(IntegerProperty):

    def __init__(self, precision=2, **kwargs):
        self.precision = precision
        super(DecimalProperty, self).__init__(**kwargs)

    def _validate(self, value):
        return Decimal(value)

    def _to_base_type(self, value):
        return int(round(value * (10 ** self.precision)))

    def _from_base_type(self, value):
        return Decimal(value) / (10 ** self.precision)


def model_ext(cls):
    cls.save = getattr(cls, 'put')
    cls.q = cls.gql
    return cls


@model_ext
class ProductStats(Model):
    name = StringProperty()
    set = StringProperty()

    c_total = IntegerProperty()
    c_foils = IntegerProperty()

    p_sell = DecimalProperty()
    p_trend = DecimalProperty()
    p_avg = DecimalProperty()
    p_low = DecimalProperty()
    p_lowex = DecimalProperty()
    p_lowfoil = DecimalProperty()

    timestamp = DateTimeProperty('ts', auto_now_add=True)

    @property
    def timestamp_str(self):
        return self.timestamp.strftime('%Y-%m-%d %H:%M:%S')

    @classmethod
    def get_by_set_and_name(cls, set, name):
        return cls.q("where set = :1 and name = :2 order by ts desc", set, name)


@model_ext
class ProductInfo(Model):
    id = IntegerProperty()
    name = StringProperty()
    set = StringProperty()
    rarity = StringProperty()

    @classmethod
    def get_by_set_and_name(cls, set, name):
        rs = cls.q("where set = :1 and name = :2", set, name)
        for r in rs:
            return r
        return None

    @classmethod
    def get_by_set(cls, set):
        qry = cls.q("where set = :1", set)
        return qry

    @classmethod
    def get_by_sets(cls, sets):
        qry = cls.q("where set in :1", sets)
        return qry


@model_ext
class LiveProperties(Model):
    key = StringProperty(indexed=False)
    value = StringProperty(indexed=False)

    @classmethod
    def get(cls, key):
        rs = cls.query(ancestor=Key("LiveProperties", key))
        #rs = cls.q("where key = :1", key)
        for r in rs:
            return r
        return None

    @classmethod
    @transactional(retries=1)
    def create(cls, key, value):
        r = cls.query(ancestor=Key("LiveProperties", key)).get()
        if not r:
            r = cls(parent=Key("LiveProperties", key), key=key, value=value)
            r.put()
        return r


@model_ext
class ProductAlerts(Model):
    name = StringProperty()
    set = StringProperty()
    to_email = StringProperty()
    is_active = BooleanProperty()


    @classmethod
    def get_all_active(cls, is_active=True):
        qry = cls.q("where is_active = :1", is_active)
        return qry