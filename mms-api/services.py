from model2 import *


@transactional(retries=1)
def cron_get_next_job(rotate_at):
    job_idx = LiveProperties.get("cron_idx") or LiveProperties.create("cron_idx", "0")
    value = int(job_idx.value)
    job_idx.value = str((value + 1) % rotate_at) #str(value + 1) if value < rotate_at - 1 else "0"
    job_idx.put()
    return value



def get_product_info(expansion, name):
    return ProductInfo.get_by_set_and_name(expansion, name)


def get_expansion_products(expansion):
    return ProductInfo.get_by_set(expansion)


def get_filtered_expansion_products(expansion, fn):
    return filter(fn, get_expansion_products(expansion))


def execute_query(query_str):
    return gql(query_str)