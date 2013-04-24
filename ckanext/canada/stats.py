import time

def completion_stats(skip=1):
    """
    Generate completions/second reports on each iteration.

    skip - number of completion reports to skip at the beginning
    """
    count = 0
    start = time.time()
    while True:
        if count < skip:
            yield '---'
        else:
            yield '%f/s' % ((time.time() - start) / count)
        count += 1
