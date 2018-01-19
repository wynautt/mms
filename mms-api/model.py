from google.appengine.ext.ndb import *


class Product(object):

    class ProductModel(Model):
        name = StringProperty()
        set = StringProperty()
        count_articles = IntegerProperty()
        count_foils = IntegerProperty()

        price_trend = FloatProperty()
        timestamp = DateTimeProperty(auto_now_add=True)


    def __init__(self, name, set, price_trend, count_articles, count_foils):
        self._model = self.ProductModel(name=name, set=set, price_trend=price_trend, count_articles=count_articles, count_foils=count_foils)

    def __getattr__(self, item):
        return getattr(self._model, item)

    def save(self):
        return self._model.put()

    @classmethod
    def query(cls, query_str, *args, **kwargs):
        return cls.ProductModel.gql(query_str, *args, **kwargs)






