from clockblocks import Clock, wait, fork
import random

random.seed(0)

c = Clock()
c.fast_forward_in_time(float("inf"))

output = []


def part_a():
    while True:
        output.append(f"A, {c.time()}")
        wait(random.choice([1, 2, 3]))


def part_b():
    while True:
        output.append(f"B, {c.time()}")
        wait(random.choice([1, 2, 3]))


c1 = fork(part_a)
c2 = fork(part_b)
wait(100)
c1.kill()
c2.kill()
c1 = fork(part_b)
c2 = fork(part_a)
wait(100)
c1.kill()
c2.kill()


def test_results():
    return [output]
