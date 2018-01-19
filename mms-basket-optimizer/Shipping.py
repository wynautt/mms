import sys
sys.path.insert(0, "libs")

#http://stackoverflow.com/questions/9413216/simple-digit-recognition-ocr-in-opencv-python

import os
import time
import json
import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup


USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Iron/32.0.1750.1 Chrome/32.0.1750.1 Safari/537.36'

url = 'https://www.magiccardmarket.eu/Help/Shipping_Costs'
headers = {'User-Agent': USER_AGENT}
params = {
    "origin": "BE",
    "destination": "BE",
}

r = requests.post(url, headers=headers, data=params)
content = r.content
#content = open('mkm/data/1.txt', 'r').read()
soup = BeautifulSoup(content, "html.parser")

form = soup.select('div.formLabel')

print form

print soup.select('select[name=origin] option')


#soup.findAll("td", {"valign" : "top"})

ori = []


for option in soup.select('select[name=origin] option'):
    ori.append([option['value'], option.string])


allParams = []
out = open('results/shipping_costs.csv', 'w')
out.write("Shipping Method\tCertified\tMax. Value\tMaximum Weigth\tStamp price\tPrice")
out.write("\n")

print len(ori)
print ori

for origin in ori:
    allParams.append({
         "origin": origin[0],
        "destination": "PT",
    })

    params = {
         "origin": origin[0],
        "destination": "PT",
    }

    r = requests.post(url, headers=headers, data=params)
    soup = BeautifulSoup(r.content, "html.parser")

    for i in soup.select("table.MKMTable.HelpShippingTable > tbody tr"):
    #print i.select("td")
        t = [td.string for td in i.select("td")]
        t.extend([origin[0], origin[1], "Portugal", "PT"])
        try:
            out.write("\t".join(t).encode("UTF-8"))
            out.write("\n")
            print "\t".join(t).encode("UTF-8")
        except (TypeError) as e:
            print "failed"

    time.sleep(1)

out.close()

print allParams


