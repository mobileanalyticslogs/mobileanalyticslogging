from threading import Thread
from functools import wraps
from multiprocessing import Process


def run_async(func):
    """
    Run function in parallel
    :param func:
    :return:
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # TODO: If queue needed, just uncomment the following code,
        #  and get by [job.get() for job in [func(x,y...) for i in ITERATION]]
        # queue = Queue()
        # thread = Thread(target=func, args=(queue,) + args, kwargs=kwargs)
        # thread.start()
        # return queue
        thread = Thread(target=func, args=args, kwargs=kwargs)
        thread.start()
        # thread.join()
        return thread
    return wrapper


def run_async_multiprocessing(func):
    """
    Run function in parallel
    :param func:
    :return:
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        proc = Process(target=func, args=args, kwargs=kwargs)
        proc.start()
        return proc
    return wrapper
