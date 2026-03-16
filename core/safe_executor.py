import threading


class FunctionThread(threading.Thread):

    def __init__(self, func):
        super().__init__()
        self.func = func
        self.error = None

    def run(self):
        try:
            self.func()
        except Exception as e:
            self.error = e


def run_with_timeout(func, timeout=2):

    thread = FunctionThread(func)

    thread.start()

    thread.join(timeout)

    if thread.is_alive():
        return "timeout"

    if thread.error:
        return "error"

    return "success"