import time
import math

start = time.time()

while True:
    print("Current time: {}".format(round(time.time() - start, 4)))
    # do some pointless and time-consuming calculations
    for i in range(1000000):
        math.log((i+1)**0.7)
    time.sleep(2)