import select
import subprocess

def worker_pool(popen_arg, num_workers, job_iterable,
                stop_when_jobs_done=True, stop_on_keyboard_interrupt=True):
    """
    Coroutine to manage a pool of workers that accept jobs as single lines
    of input on stdin and produces results as single lines of output.

    popen_arg - parameter to pass to subprocess.Popen when creating workers
    num_workers - maximum number of workers to create
    job_iterable - iterable producing (job id, job string) tuples
    stop_when_jobs_done - the generator exits when all jobs are done
    stop_on_keyboard_interrupt - the generator exits on KeyboardIterrupt

    job string should include a single trailing newline.

    accepted to send(): job iterable or None, when a new job iterable
    is sent it will replace the previous one used for assigning jobs.

    This generator blocks until there is a result from one of the workers.

    yields (current worker job id list, finished job id, job result) tuples

    worker job id list will include None if some workers are idle.
    job result will include trailing newline.

    when all workers
    """
    workers = []
    job_ids = []
    worker_fds = {}
    job_iter = iter(job_iterable)

    def assign_jobs():
        while len(workers) < num_workers or None in job_ids:
            job_id, job_str = next(job_iter, (None, None))
            if job_str is None:
                break
            if len(workers) < num_workers:
                # spin up new worker
                w = subprocess.Popen(popen_arg,
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                worker_fds[w.stdout] = len(workers)
                workers.append(w)
                job_ids.append(job_id)
            else:
                wnum = job_ids.index(None)
                w = workers[wnum]
                job_ids[wnum] = job_id
            w.stdin.write(job_str)
            w.stdin.flush()

    try:
        while True:
            assign_jobs()
            if all(i is None for i in job_ids):
                if stop_when_jobs_done:
                    return
                # allow new jobs to be submitted
                new_jobs = yield (job_ids, None, None)
                job_iter = iter(new_jobs)
                continue

            try:
                readable, _, _ = select.select(worker_fds, [], [])
            except KeyboardInterrupt:
                if stop_on_keyboard_interrupt:
                    return
                raise

            fd = readable[0]
            wnum = worker_fds[fd]
            w = workers[wnum]
            result = w.stdout.readline()
            finished = job_ids[wnum]
            job_ids[wnum] = None
            assign_jobs()

            new_jobs = yield (job_ids, finished, result)
            if new_jobs:
                job_iter = iter(new_jobs)

    finally:
        for w in workers:
            w.stdin.close()
