from subprocess import Popen
from typing import List, Optional


class Runtime:
    def __init__(self, path: str, args: Optional[List[str]] = None):
        self.path = path
        self.args = args if args else []
        self.process = None

    def start(self):
        self.process = Popen([self.path] + self.args)

    def terminate(self):
        self.process.terminate()
        self.process.wait()

    def __enter__(self):
        self.start()

    def __exit__(self, *args):
        self.terminate()
