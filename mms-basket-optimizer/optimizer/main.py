import logging
from MKMAPI import get_input_data
from input_generator import generate_input_file
from solver import solver

stream_handler_simple = logging.StreamHandler()

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

log = logging.getLogger("basic_main")
log.setLevel(logging.INFO)
log.addHandler(stream_handler_simple)

#----------------------------------
#----------CONFIGURATION-----------
#----------------------------------

INPUT = 'results/presale_lands_2'
REFRESH = True
ITERATIONS = 100
ONLY_USE_ITERATIONS = False


ARTICLES = [
    ('Port Town', 'Shadows over Innistrad', 4),
    ('Choked Estuary', 'Shadows over Innistrad', 4),
    ('Fortified Village', 'Shadows over Innistrad', 4),
    ('Game Trail', 'Shadows over Innistrad', 4),
    ('Foreboding Ruins', 'Shadows over Innistrad', 4),
]

#----------------------------------
#------END CONFIGURATION-----------
#----------------------------------


products = get_input_data(ARTICLES, REFRESH)
generate_input_file(INPUT + '.txt', products)

S, T, R, d, pretty, pretty_by_product = solver(INPUT + '.txt', iterations=ITERATIONS, iterations_only=ONLY_USE_ITERATIONS)
print "S=%s" % S
print "R=%s" % map(str, R)
print "d=%s" % d
print "T=%s" % T
print "Sum_T=%.2f" % sum(T)
print "Sum_d=%.2f" % sum(d)

for key, v in pretty.iteritems():
    if v['t'] > 0:
        print "Store=%s" % key
        print "T=%.2f, d=%.2f, ps=%s" % (v['t'], v['d'], v['p'])

print ""

for key, v in pretty_by_product.iteritems():
    print "Product=%s Stores=%s" % (key, v)


with open(INPUT + '_result.txt', 'w') as output:
    output.write("S=%s\n" % S)
    output.write("R=%s\n" % map(str, R))
    output.write("d=%s\n" % d)
    output.write("T=%s\n" % T)
    output.write("Sum_T=%.2f\n" % sum(T))
    output.write("Sum_d=%.2f\n" % sum(d))

    i, j = 1, 1
    for key, v in pretty.iteritems():
        if v['t'] > 0:
            output.write("Store[%d, %d]=%s\n" % (j, i, key))
            output.write("T=%.2f, d=%.2f, ps=%s\n" % (v['t'], v['d'], v['p']))
            j += 1
        i += 1
