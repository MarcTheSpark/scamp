import dill
import time

manager = Manager()
l = manager.list([])


def addx(x):
    def out(y):
        return x + y
    return out


bob = addx(6)

l.append(dill.dumps(bob))


def use_bob():
    for pickled_func in l:
        func = dill.loads(pickled_func)
        print(func(43))


Process(target=use_bob).start()
time.sleep(1)
exit()



# from clockblocks import sleep_precisely
# import sched, time
# import threading
#
# s = sched.scheduler(time.time, sleep_precisely)
# def print_time(a='default'):
#     print("From print_time", time.time(), a)
#
# def print_some_times():
#     print(time.time())
#     s.enter(10, 1, print_time)
#     s.enter(5, 2, print_time, argument=('positional',))
#     s.enter(5, 1, print_time, kwargs={'a': 'keyword'})
#     s.enter(5, 1, print_time, kwargs={'a': 'keyword'})
#     s.enter(5, 1, print_time, kwargs={'a': 'keyword'})
#     s.run(blocking=True)
#     print(time.time())
#
#
# print_some_times()
# exit()
