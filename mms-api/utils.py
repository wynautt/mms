def get_first(iterable, default=None):
    for item in iterable:
        return item
    return default


def get_normalized_ranges(min, max, p):
    return [int(min - min * p), int(max + max * p)]
