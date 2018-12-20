# clockblocks

_Clockblocks_ is a python library for controling the flow of time, designed with musical applications in mind. A `Clock` acts like thread, but with the advantage that when multiple clocks are coordinated under the same master clock they remain precisely coordinated and do not experience drift. Furthermore, processing time is taken into account when "wait" is called in a given Clock. For example, the following program:

```python
import clockblocks
import time
import math

clock = clockblocks.Clock()
start = time.time()

while True:
    print("Current time: {}".format(round(time.time() - start, 4)))
    # do some pointless and time-consuming calculations
    for i in range(1000000):
        math.log((i+1)**0.7)
    clock.wait(2)
```
 
... generates the output:

```console
Current time: 0.0
Current time: 2.0001
Current time: 4.0001
Current time: 6.0
Current time: 8.0001
Current time: 10.0
```

Whereas a traditional thread:

```python
import time
import math

start = time.time()

while True:
    print("Current time: {}".format(round(time.time() - start, 4)))
    # do some pointless and time-consuming calculations
    for i in range(1000000):
        math.log((i+1)**0.7)
    time.sleep(2)
```


...will gradually drift because of the intensive calculations, outputting:

```console
Current time: 0.0
Current time: 2.3772
Current time: 4.7623
Current time: 7.1397
Current time: 9.5151
Current time: 11.893
```

In addition, _clockblocks_ offers useful musical functionality, like sudden and gradual changes of tempo. Perhaps the most exciting feature of _clockblocks_ is that clocks moving at different tempos can be nested within each other. In this case, each clock distorts time for those underneath it: a clock whose tempo is oscillating between slow and fast, nested within a clock that is accelerating, will generate a time stream whose tempo oscillates faster and faster.
