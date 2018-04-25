
last_check_in = (time.time(), None, None)


def check_in(name, spot, no_print=False):
    global last_check_in
    time_since_last = time.time() - last_check_in[0]
    if not no_print and time_since_last > 0.0001:
        print("{}:{} took {} seconds since {}:{}".format(name, spot, time_since_last, last_check_in[1], last_check_in[2]))
    last_check_in = (time.time(), name, spot)
