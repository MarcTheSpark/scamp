multi_thread_log = []


def log_multi(clock, position, *comment_args):
    # useful for keeping track of the order of events between different threads
    comment = ""
    for i in range(0, len(comment_args), 2):
        if i != 0:
            comment += ", "
        if i+1 < len(comment_args):
            comment += "{}={}".format(comment_args[i], comment_args[i+1])
        else:
            comment += comment_args[i]
    multi_thread_log.append("{} at checkpoint {}: {}".format(clock.name, position, comment))


def print_multi_log(how_many):
    # prints out a trace of the last events logged
    print("--- MULTI-THREAD_LOG ---")
    for comment in multi_thread_log[-how_many:]:
        print(comment)
    print("--- END LOG ---")