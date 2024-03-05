import logging
from subprocess import Popen
from typing import List, Optional, Dict, Callable, TYPE_CHECKING
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from .bridge import RuntimeBridge, GenericMessage


# This makes it easier to get the current api for now - we can change this later.
api = None
logger = logging.getLogger(__name__)


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


class Simulation:

    def __init__(self):
        # The current time - placeholder for now.
        self.sim_time = datetime(1880, 1, 1, 8)
        self.sim_id = None

    def load(self):
        """Load the simulation data """
        # TODO: Load the metadata from the runtime.
        pass

    async def tick(self, delta: timedelta):
        # TODO: Have the runtime send a TICK signal.
        pass

    async def receive_request(self, msg, callback):
        pass

    async def receive_message(self, msg):
        pass


class API:

    def __init__(self, bridge: "RuntimeBridge"):
        self.bridge = bridge

    async def resume(self, callback: Optional[Callable[["GenericMessage"], None]] = None):
        logger.info("Resuming simulation")
        await self.bridge.send_message('simulation-command', {
            'command': 'resume',
        }, callback)

    async def pause(self, callback: Optional[Callable[["GenericMessage"], None]] = None):
        await self.bridge.send_message('simulation-command', {
            'command': 'pause',
        }, callback)

    async def set_time(self, speed: str, callback: Optional[Callable[["GenericMessage"], None]] = None):
        await self.bridge.send_message('simulation-command', {
            'set-speed': speed,
        }, callback)
