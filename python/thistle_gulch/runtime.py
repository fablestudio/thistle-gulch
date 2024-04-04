import asyncio
import json
from datetime import datetime
from subprocess import Popen
from typing import Optional, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    import socketio

from . import GenericMessage, converter, logger, random_reference
from .api import API


class Runtime:
    def __init__(
        self,
        sio: "socketio.AsyncServer",
        path: Optional[str] = None,
        args: Optional[List[str]] = None,
    ):
        self.required_version = "1.47.0-beta"
        self.sio = sio
        self.path = path
        self.args = args if args else []
        self.process: Optional[Popen[bytes]] = None
        self.emit_lock = asyncio.Lock()
        self.sid: Optional[str] = None
        self.api = API(self)
        self.start_date: datetime

    def start(self):
        if self.process and self.process.poll() is None:
            logger.warning("[Runtime] Process already started.")
            return
        if self.path is None:
            raise ValueError("[Runtime] Can't start because path is None.")
        # Start the runtime process.
        logger.info(f"[Runtime] Starting process: {self.path} {' '.join(self.args)}")
        self.process = Popen([self.path] + self.args)

    def terminate(self):
        logger.info("[Runtime] Shutting Down ...")
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
            logger.info("[Runtime] Process terminated.")
        else:
            logger.warning("[Runtime] No process to terminate.")

    def __enter__(self):
        self.start()

    def __exit__(self, *args):
        self.terminate()

    async def on_connect(self, sid: str):
        """Connect to the runtime."""
        # TODO: Decide what to do when the runtime disconnects and reconnects.
        self.sid = sid

    async def on_disconnect(self, sid):
        """Disconnect from the runtime."""
        # TODO: Decide what to do when the runtime disconnects.
        pass

    async def receive_message(self, msg):
        pass

    async def receive_request(self, msg, callback):
        pass

    async def send_message(self, msg_type, data, timeout=5) -> GenericMessage:
        """
        Send a request to the runtime.
        :param msg_type: type of message.
        :param data: data to send with the message.
        :param timeout: [Optional] function to call when the server responds.
        :return: A GenericMessage object.
        """

        # Create a Future object that we will use to wait for the callback response
        future: asyncio.Future[Tuple[str, str]] = asyncio.Future()

        # Define a callback function that will be called when the emit() receives a response
        async def callback(resp_type: str, resp_data_str: str):
            self.emit_lock.release()
            # If the future is already done (cancelled), then we don't need to do anything.
            if future.done():
                return None
            # Set the future result, which will unblock the send_message function.
            future.set_result((resp_type, resp_data_str))

        if self.sid is None:
            err = f"[Message Request] Error: simulation sid is None."
            logger.error(err)
            raise ValueError(err)

        # Create a reference for the message so that we can match the response to the request.
        reference = random_reference()
        # Create a GenericMessage object and serialize it to a string so that it can be sent to the Runtime.
        request_msg = GenericMessage(type=msg_type, data=data, reference=reference)
        serialized_message = json.dumps(converter.unstructure(request_msg))

        # Acquire the emit lock to prevent multiple emits from happening at the same time.
        await self.emit_lock.acquire()
        try:
            await self.sio.emit(
                "messages",
                (request_msg.type, serialized_message),
                to=self.sid,
                callback=callback,
            )
        except Exception as e:
            err = f"[Message Request] Error sending message: {str(e)}"
            logger.error(err)
            # Release the emit lock if an error occurs.
            self.emit_lock.release()
            raise e

        # Wait for the future to have a result, with timeout
        try:
            # Wait for the Future object to have a result, with timeout
            response_type, response_data_str = await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError as e:
            # Handle the case where the future times out
            err = f"[Message Response] Response timed out after {timeout} seconds"
            logger.error(err)
            raise e
        except Exception as e:
            # Handle other exceptions that could occur
            err = f"[Message Response] Response exception: {str(e)}"
            logger.error(err)
            raise e

        # Parse the response_data and set the future result.
        try:
            data = json.loads(response_data_str)
        except json.JSONDecodeError as e:
            err = f"[Message Response] {response_type} Error decoding JSON: {str(e)}"
            logger.error(err)
            raise e

        if data.get("error"):
            err = (
                f'[Message Response] {response_type} Runtime Error: {data.get("error")}'
            )
            logger.error(err)
            raise ValueError(err)

        # Validate that the response_data is a dictionary.
        if not isinstance(data, dict):
            err = f"[Message Response] Error: data not a dictionary."
            logger.error(err)
            raise ValueError(err)

        # Convert to a GenericMessage.
        response = GenericMessage(type=response_type, data=data, reference=reference)
        return response
