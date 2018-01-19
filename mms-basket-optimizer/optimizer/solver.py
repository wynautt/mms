import csv
import logging
import copy
import random
import time
import math
import mem_utils
from input_generator import generate_input_file

from operator import itemgetter
from random import shuffle
from itertools import permutations, combinations

stream_handler_simple = logging.StreamHandler()

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

log = logging.getLogger("basic_solver")
log.setLevel(logging.DEBUG)
log.addHandler(stream_handler_simple)

INF = float("inf")

class Instance(object):

    def __init__(self, num_p, num_s, p, d, p_copies):
        self.num_p = num_p
        self.num_s = num_s
        self.p = p
        self.data = p
        self.d = d
        self.p_copies = p_copies
        self.p_order = range(0, len(p_copies))
        self.d_limit = map(lambda l: l[::2], d)
        self.d_cost = map(lambda l: l[1::2], d)
        #self.data = [[4, [[[19.3, 3], [INF, 0]], [[20, 1], [INF, 0]], [[18.3, 1], [20, 2], [22, 5], [INF, 0]]]],
        #             [1, [[[8, 1], [INF, 0]], [[8.1, 2], [INF, 0]], [[9, 6], [INF, 0]]]],
        #             [2, [[[15, 1], [16, 3], [19, 10], [INF, 0]], [[16, 3], [INF, 0]]]]
        #             ]

        #[
        #    [[[15.2, 1.0], [inf, 0]], [[16.0, 1.0], [inf, 0]]],
        #    [[[19.3, 1.0], [inf, 0]], [[20.1, 1.0], [inf, 0]]],
        #    [[[9.6, 1.0], [inf, 0]], [[8.0, 1.0], [inf, 0]]],
        #    [[[12.1, 1.0], [inf, 0]], [[11.67, 1.0], [inf, 0]]],
        #    [[[14.45, 1.0], [15.0, 5.0], [inf, 0]], [[14.45, 1.0], [inf, 0]]]

        #    [[[15.2, 1] [15.3, 1] [15.9, 1p], [inf, 0]], [[14.45, 1], [inf, 0]]]
        #]

    def __str__(self):
        return "distinct_p: %d\nnum_s: %d\ntotal_p: %d\norder: %s\ncopies: %s\nd:%s\ndata: %s" % \
               (self.num_p, self.num_s, sum(self.p_copies), self.p_order, self.p_copies, self.d, "too long to display")

    def pj_num_copies_required(self, j):
        return self.p_copies[j]

    def pj_num_copies_per_s(self, j):
        return map(lambda l: sum(map(lambda x, y: int(x * y), zip(*l)[1], zip(*l)[2])), self.data[j])

    def pj_num_copies_with_units_per_s(self, j, units):
        return map(lambda l: sum(zip(*filter(lambda x: int(x[2]) == units, l))[1]), self.data[j])

    def pj_best_p_per_s(self, j):
        return map(lambda l: l[0][0], self.data[j]), map(lambda l: int(l[0][2]), self.data[j])

    def pj_set_s_selected(self, j, i):
        self.data[j][i][0][1] -= 1
        if self.data[j][i][0][1] <= 0:
            if self.data[j][i][0][0] < INF:
                del self.data[j][i][0]

    def pj_remove_invalid_units(self, j, units_left):
        self.data[j] = map(lambda l: filter(lambda x: x[2] <= units_left, l), self.data[j])


class Solution(object):

    def __init__(self, num_p, num_s):
        self.T = [0] * num_s
        self.d = [0] * num_s
        self.R = [[] for i in range(num_p)]
        self.S = 0


def create_instance(dfile):
    with open(dfile, 'rb') as f:
        log.debug("reading data file %s:" % f.name)

        reader = csv.reader(f, delimiter=' ')
        data = []
        dtemp = []
        d_list = []
        s_names = []
        p_names = []
        p_ncopies = []
        mode = -2
        for row in reader:
            log.debug(row)
            if len(row) == 0:
                mode += 1
                if len(dtemp) > 0:
                    data.append(dtemp)
                dtemp = []
            elif mode == -2:
                s_names.append(" ".join(row))
            elif mode == -1:
                p_names.append(" ".join(row))
            elif mode == 0:
                d_list.append(map(float, row))
            elif mode == 1:
                p_ncopies = map(int, row)
            else:
                try:
                    l = map(float, row)
                    dtemp.append(map(list, zip(l[0::3], l[1::3], l[2::3])) + [[INF, 0, 1]])
                except ValueError as e:
                    #s does not have p
                    dtemp.append([] + [[INF, 0, 1]])

        num_p = len(data)
        num_s = len(data[0])

        if not len(s_names) == num_s:
            raise AssertionError("found %d s_names instead of %d" % (len(s_names), num_s))

        if not len(p_names) == num_p:
            raise AssertionError("found %d p_names instead of %d" % (len(p_names), num_p))

        if len(p_ncopies) > len(data):
            raise AssertionError("found more copies than p's. please add a newline at EOF or more p's entries")

        if len(p_ncopies) < len(data):
            raise AssertionError("found more p's than copies. please check if copies' list as the same size of p's entries")

        if not len(d_list) == num_s:
            raise AssertionError("found %d d entries instead of %d" % (len(d_list), num_s))

        for j, p in enumerate(data):
            if not len(p) == num_s:
                raise AssertionError("line %d contains %d columns instead of %d" % (j, len(p), num_s))

        inst = Instance(num_p, num_s, data, d_list, p_ncopies)

        available_copies = [sum(inst.pj_num_copies_per_s(i)) for i in range(inst.num_p)]
        #available_copies_with_4_units = [sum(inst.pj_num_copies_with_units_per_s(i, 4)) for i in range(inst.num_p)]
        #available_copies_with_1_units = [sum(inst.pj_num_copies_with_units_per_s(i, 1)) for i in range(inst.num_p)]
        #check if required % 4 units are available as single units
        available_greater_than_required = map(lambda available, required: available >= required, available_copies, inst.p_copies)
        if not all(available_greater_than_required):
            raise AssertionError("available is less than required for line %d" % (available_greater_than_required.index(False)))

        return inst, s_names, p_names


def get_d_min_with_idx(total, d_cost, d_limit):
    #return maximum cost ([-1]) if outside limits
    #can be removed with the introduction of +inf on limits and costs
    return next(((i, d_cost[i]) for i, limit in enumerate(d_limit) if total < limit), (-1, float("inf")))


def dmin(pj, T, d_current, d_limit):
    _ = map(lambda (i, t): get_d_min_with_idx(t + pj[i], d_current[i], d_limit[i]), enumerate(T))
    idx, d_costs = zip(*_)
    return idx, d_costs


def f(pj, T, d_current, d_solution, d_limit):
    d_min_idx, d_min = dmin(pj, T, d_current, d_limit)
    d_min = map(lambda x, y: x - y if x - y > 0 else 0, d_min, d_solution)
    return map(sum, zip(pj, d_min)), d_min_idx


def select_eligible_s(pj, pj_units, units_left, T, d_current, d_solution, d_limit):
    cj, d_min_idx = f(pj, T, d_current, d_solution, d_limit)

    i, _ = zip(*filter(lambda (i, x): x[0] <= units_left, enumerate(zip(pj_units, cj))))
    pj_units, cj = zip(*_)

    #if units_left >= max(pj_units): #if is pl7 and there is space left
    cj = map(lambda x, y: x / float(y), cj, pj_units)

    #i, cij = min(enumerate(cj), key=itemgetter(1))
    i, cij, pj_units = min(zip(i, cj, pj_units), key=itemgetter(1))

    #if units_left >= max(pj_units): #if is pl7 and there is space left
    #cij = cij * pj_units[i]
    cij = cij * pj_units

    return i, cij, d_min_idx, pj_units


def get_d_min(total, d_cost, d_limit):
    return 0 if total <= 0 else next((d_cost[i] for i, limit in enumerate(d_limit) if total < limit), float("inf"))

def is_valid(S, R, ps, d_cost, d_limit, num_s, p_copies):
    c_T = [0] * num_s
    c_d = [0] * num_s

    for i, p in enumerate(ps):
        track = [0] * num_s
        track_count_for_s = [0] * num_s
        k = 0
        while k < p_copies[i]:
        #for k in range(p_copies[i]):
            s_idx = R[i][k]
            pos_in_s = track[s_idx]
            while p[s_idx][pos_in_s][2] > p_copies[i] - k:
                pos_in_s += 1
            c_T[s_idx] += p[s_idx][pos_in_s][0]
            track_count_for_s[s_idx] += 1
            if track_count_for_s[s_idx] >= p[s_idx][pos_in_s][1]:
                track[s_idx] = pos_in_s + 1
                track_count_for_s[s_idx] = 0
            k += int(p[s_idx][pos_in_s][2])

    for j, s in enumerate(c_T):
        c_d[j] = get_d_min(c_T[j], d_cost[j], d_limit[j])

    c_S = sum(c_T) + sum(c_d)

    return c_S, c_T, c_d


def shuffle(instance):
    l = zip(instance.data, instance.p_copies, instance.p_order)
    random.shuffle(l)
    instance.data, instance.p_copies, instance.p_order = zip(*l)
    instance.data = list(instance.data)
    return instance

def unshuffle(instance):
    l = zip(instance.data, instance.p_copies, instance.p_order)
    l = sorted(l, key=lambda e: e[2])
    instance.data, instance.p_copies, instance.p_order = zip(*l)
    instance.data = list(instance.data)
    return instance

def all_permutations(instance):
    l = zip(instance.data, instance.p_copies, instance.p_order)
    for x in permutations(l):
        instance.data, instance.p_copies, instance.p_order = zip(*x)
        instance.data = list(instance.data)
        yield instance

def sort_instance(instance, key=lambda x: avg([l[0][0] for l in x[0]]), reverse=False):
    instance.data, instance.p_copies, instance.p_order = zip(*sorted(zip(instance.data, instance.p_copies, instance.p_order), key=key, reverse=reverse))
    instance.data = list(instance.data)
    return instance


def avg(lst):
    return sum(lst) / float(len(lst))


def solve(instance, iterations=100, permutations_limit=9, iterations_only=False):
    iteration = [0]

    def solve_aux(instance):
        instance = copy.deepcopy(instance)
        solution = Solution(instance.num_p, instance.num_s)
        d = map(lambda l: l + [float("inf")], instance.d_cost)
        d_current = copy.deepcopy(d)
        d_limit = map(lambda l: l + [float("inf")], instance.d_limit)

        log.info("Iteration %s" % (iteration[0]))
        log.info("Mem Usage: %s" % mem_utils.memory_usage_psutil())
        iteration[0] += 1

        j = 0
        while j < instance.num_p:
            k = 0
            required = instance.pj_num_copies_required(j)
            while k < required:
            #for _ in range(instance.pj_num_copies_required(j)):
                units_left = required - k
                instance.pj_remove_invalid_units(j, units_left)
                pj, pj_units = instance.pj_best_p_per_s(j)
                i, cij, d_min_idx, units_added = select_eligible_s(pj, pj_units, units_left, solution.T, d_current, solution.d, d_limit)
                instance.pj_set_s_selected(j, i)
                #solution.R[j].append(i)
                solution.R[j].extend([i] * units_added)
                solution.T[i] += pj[i]
                solution.S += cij
                solution.d[i] = d[i][d_min_idx[i]]
                d_current[i][d_min_idx[i]] = 0
                k += units_added
            j += 1

        _, solution.R = zip(*sorted(zip(instance.p_order, solution.R), key=lambda cons: cons[0]))
        return solution.S, solution.R, solution.d

    if not iterations_only and instance.num_p <= permutations_limit:
        log.info("Initializing solver with %d permutations (for %d products) for instance:\n%s" % (math.factorial(instance.num_p), instance.num_p, instance))
    else:
        log.info("Initializing solver with %d (+2) iterations for instance:\n%s" % (iterations, instance))

    inst1 = copy.deepcopy(instance)
    sort_instance(inst1, reverse=False)

    inst2 = copy.deepcopy(instance)
    sort_instance(inst2, reverse=True)

    def next_instance():
        #limit permutation to 9 products (362880 entries)
        if not iterations_only and instance.num_p <= permutations_limit:
            #for x in all_permutations(copy.deepcopy(instance)):
            for x in all_permutations(instance):
                yield x
        else:
            for _ in range(0, iterations):
                #yield shuffle(c
                yield shuffle(instance)

    log.info("Mem usage before starting solver: %s" % mem_utils.memory_usage_psutil())
    log.info("---- Starting solver ----")

    current_instances = [inst1, inst2]
    current_solutions = map(lambda x: solve_aux(x), current_instances)

    i_min, sol_min = min(enumerate(current_solutions), key=lambda x: x[1][0])
    i_max, sol_max = max(enumerate(current_solutions), key=lambda x: x[1][0])

    inst_min = current_instances[i_min]
    inst_max = current_instances[i_max]

    #for i in range(0, iterations):
    for current_inst in next_instance():
        #current_inst = shuffle(copy.deepcopy(instance))
        current_solution = solve_aux(current_inst)
        log.debug("Solution: S=%s, R=%s, d=%s" % current_solution)
        i_min, sol_min = min(enumerate([sol_min, current_solution]), key=lambda x: x[1][0])
        i_max, sol_max = max(enumerate([sol_max, current_solution]), key=lambda x: x[1][0])
        inst_min = [inst_min, current_inst][i_min]
        inst_max = [inst_max, current_inst][i_max]

    Smin, Rmin, dmin = sol_min
    Smax, Rmax, dmax = sol_max

    inst_min = unshuffle(inst_min)
    inst_max = unshuffle(inst_max)

    log.info("Best solution: S=%s, R=%s, d=%s" % (Smin, Rmin, dmin))
    log.info("Check solution S=%s, T=%s, d=%s" % is_valid(Smin, Rmin, inst_min.data, instance.d_cost, instance.d_limit, instance.num_s, inst_min.p_copies))

    log.debug("Worse solution: S=%s, R=%s, d=%s" % (Smax, Rmax, dmax))
    log.debug("Check solution S=%s, T=%s, d=%s" % is_valid(Smax, Rmax, inst_max.data, instance.d_cost, instance.d_limit, instance.num_s, inst_max.p_copies))

    log.debug("Max: %s" % Smax)
    log.debug("Min: %s" % Smin)
    log.debug("|Max-Min|: %s" % (Smax - Smin))

    _, Tmin, _ = is_valid(Smin, Rmin, inst_min.data, instance.d_cost, instance.d_limit, instance.num_s, inst_min.p_copies)
    return Smin, Tmin, Rmin, dmin


def solver(dfile, iterations=100, permutations_limit=9, iterations_only=False):
    log.info("Mem Usage: %s" % mem_utils.memory_usage_psutil())
    start_time = time.time()
    inst, s_names, p_names = create_instance(dfile)
    S, T, R, d = solve(inst, iterations=iterations, permutations_limit=permutations_limit, iterations_only=iterations_only)

    s_list = map(lambda e: dict(s=e[0], t=e[1], d=e[2], p=dict()), zip(s_names, T, d))

    p_list = zip(p_names, R)

    for p_e in p_list:
        p_R = p_e[1]
        p_name = p_e[0]
        for e in p_R:
            if p_name in s_list[e]['p']:
                s_list[e]['p'][p_name] += 1
            else:
                s_list[e]['p'][p_name] = 1

    pretty_result = dict()
    for e in s_list:
        pretty_result[e['s']] = e


    pretty_result_by_p = dict()
    for e in s_list:
        for p in e['p']:
	    if not p in pretty_result_by_p:
	        pretty_result_by_p[p] = dict()
	    pretty_result_by_p[p][e['s']] = e['p'][p]


    end_time = time.time()
    log.info("Run in %s seconds (%s minutes)" % (end_time - start_time, (end_time - start_time) / 60))
    log.info("Mem Usage: %s" % mem_utils.memory_usage_psutil())
    return S, T, R, d, pretty_result, pretty_result_by_p

