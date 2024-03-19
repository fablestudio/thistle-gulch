import asyncio
import json
import logging
import sys
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Callable, Union, Dict, Type, Any, TypeVar, Optional

T = TypeVar('T')

import cattrs
import socketio
from aiohttp import web
from attr import define
import fable_saga.server as saga_server

import thistle_gulch
from . import Runtime, Simulation, API
from .data_models import PersonaContextObject

logger = logging.getLogger(__name__)

# module level converter to convert between objects and dicts.
converter = cattrs.Converter(forbid_extra_keys=True)
saga_server.converter.forbid_extra_keys = False


# Override the default saga_server request types to include a context_obj field when working with the runtime.
@define(slots=True)
class TGActionsRequest(saga_server.ActionsRequest):
    """Enhanced ActionsRequest with a context_obj."""
    context_obj: PersonaContextObject = None


@define(slots=True)
class TGConversationRequest(saga_server.ConversationRequest):
    """Enhanced ConversationRequest with a context_obj."""
    context_obj: PersonaContextObject = None

"""
Sets up a server that can be used to generate actions for SAGA. Either HTTP or socketio can be used.
"""


@define(slots=True)
class GenericMessage:
    """ A generic message that is received."""
    type: str
    data: dict = {}
    reference: str = None
    error: str = None


@define(slots=True)
class BridgeConfig:
    host: str = 'localhost'
    port: int = 8080
    cors: str = '*'
    runtime_path: str = None
    # Reuse the SAGA Actions and Conversation (Servers) as endpoints.
    actions_endpoint = saga_server.SagaServer()
    conversation_endpoint = saga_server.ConversationServer()


class Route:
    def __init__(self, msg_type: str, msg_class: Type[T], process_function: Callable[[T], Any]):
        self.msg_type = msg_type
        self.msg_class = msg_class
        self.process_function = process_function


class IncomingMessageRouter:

    def __init__(self):
        self.routes: Dict[str, Route] = {}

    def add_route(self, route: Route):
        self.routes[route.msg_type] = route

    async def handle_message(self, sid: str, message_str: str) -> Any:
        logger.debug(f"[Message] received from {sid}: {message_str}")
        try:
            # Convert the message to a dictionary and validate that it has a type and that the type has a known route.
            message = json.loads(message_str)
            logger.info(
                f"[Message] sid: {sid}, type: {message.get('type', 'unknown')}, ref: {message.get('reference', 'unknown')}")
            msg_type = message.get('type')
            if msg_type is None:
                raise ValueError("Message is missing a type.")
            if msg_type not in self.routes:
                raise ValueError(f"Unknown message type: {msg_type}")

            # Convert the message to the appropriate type and process it.
            request_type = self.routes[message['type']].msg_class
            request = converter.structure(message, request_type)
            result = await self.routes[message['type']].process_function(request)

            # If the result is None, then we don't send a response.
            if result is None:
                return

            # Convert the result to a response and send it back.
            response = converter.unstructure(result)
            return response
        except json.decoder.JSONDecodeError as e:
            error = f"Error decoding JSON: {str(e)}"
            ex = e
        except cattrs.errors.ClassValidationError as e:
            error = f"Error validating request: {json.dumps(cattrs.transform_error(e))}"
            ex = e
        except Exception as e:
            error = f"Error processing request: {str(e)}"
            ex = e
        # If we get here, then there was an error.
        logger.error(f"[Error] sid: {sid}, message: {message_str}, error: {error}, "
                     f"stacktrace: {''.join(traceback.TracebackException.from_exception(ex).format())}")
        response = saga_server.ErrorResponse(error=error)
        output = converter.unstructure(response)
        return output


class RuntimeBridge:

    def __init__(self, config: BridgeConfig):
        self.config = config
        self.runtime = None
        self.simulation = Simulation()
        self.router = IncomingMessageRouter()
        self.on_ready: Optional[Callable[[API], None]] = None

        # Add routes
        async def on_ready_handler(ready_response: GenericMessage):
            """Handler for the simulation-ready message."""
            logger.info(f"[Simulation Ready] received..")
            thistle_gulch.api = API(self)
            if self.on_ready is not None:
                # pass the bridge instance to the on_ready callback so that it can send messages to the runtime.
                self.on_ready(thistle_gulch.api)
            else:
                async def on_set_start_date_handler(response: GenericMessage):
                    """Handler for the set-start-date message."""
                    if response.error is None:
                        await thistle_gulch.api.resume()

                start_date = datetime.fromisoformat(ready_response.data.get("start_date"))
                # Override the start date here as needed. e.g. start_date = start_date + timedelta(hours=9)
                await thistle_gulch.api.set_start_date(start_date.isoformat(), on_set_start_date_handler)
            return None
        self.router.add_route(Route('simulation-ready', GenericMessage, on_ready_handler))

        # Add some dummy routes for testing.
        async def dummy_handler(request: GenericMessage):
            print(request)
            return None

        async def dummy_handler_with_response(request: GenericMessage):
            print(request)
            return GenericMessage(type='heartbeat-ack', data={'ack': 'ack'}, reference=request.reference)

        async def dummy_handler_independent_response(request: GenericMessage):
            await asyncio.sleep(.2)

            def test_callback(response: GenericMessage):
                print(response)

            await self.send_message('heartbeat-independent', {'ack': 'ack'}, test_callback)

        self.router.add_route(Route('heartbeat', GenericMessage, dummy_handler_independent_response))
        self.router.add_route(Route('heartbeat-ack', GenericMessage, dummy_handler_with_response))


        # Validate the runtime path and create a runtime instance.
        if self.config.runtime_path is not None:
            split_args = self.config.runtime_path.split()
            assert len(split_args) > 0, f"Error: Empty --runtime path"

            runtime_arg_index = 1
            runtime_path_str = split_args[0]
            for runtime_arg_index in range(1, len(split_args)):
                arg = split_args[runtime_arg_index]
                # Detect the first runtime flag
                if arg.startswith("-"):
                    break
                # Re-join the runtime path if it has spaces
                else:
                    runtime_path_str += " " + arg

            # Validate runtime path
            import pathlib
            path = pathlib.Path(runtime_path_str)
            assert path.exists(), f"Error: --runtime path not found: \"{runtime_path_str}\""
            assert path.is_file(), f"Error: --runtime path is not a file: \"{runtime_path_str}\""

            runtime_args = split_args[runtime_arg_index:]
            self.runtime = Runtime(runtime_path_str, runtime_args)

        # Set up the async web server via aiohttp - this is the server that will handle the socketio connections.
        self.app = web.Application()

        # Set up socketio
        sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins=config.cors)
        sio.attach(self.app)
        self.sio = sio

        @sio.event
        def connect(sid, _):
            self.simulation.sim_id = sid
            logger.info("Runtime [Connected]: " + sid)

        @sio.event
        def disconnect(sid):
            self.simulation.sim_id = None
            logger.info("Runtime [Disconnected]: " + sid)

        # Set up the socketio event handlers. These are basically channels that the server listens on.
        # The first one is a catch-all for unhandled events.
        @sio.on('*')
        def catch_all(event, sid, *data):
            """Catch all unhandled events that have one message. (common)"""
            logger.error(f"Unhandled event: {event} {sid} {data}")

        # This is the main event that the server listens on when talking to the runtime.
        @sio.on('messages')
        async def on_incoming_messages(sid, message_str: str):
            return await self.router.handle_message(sid, message_str)

        # These are the events that the server listens on when emulating the SAGA server. [Deprecated]
        @sio.on('generate-actions')
        async def generate_actions(sid, message_str: str):
            logger.info(f"[Generate Actions] Request from {sid}")
            logger.debug(f"[Generate Actions] Request from {sid}: {message_str}")
            return await saga_server.generic_handler(message_str, TGActionsRequest,
                                                     self.config.actions_endpoint.generate_actions,
                                                     saga_server.ActionsResponse)

        # These are the events that the server listens on when emulating the SAGA server. [Deprecated]
        @sio.on('generate-conversation')
        async def generate_conversation(sid, message_str: str):
            logger.info(f"[Generate Conversation] Request from {sid}")
            logger.debug(f"[Generate Conversation] Request from {sid}: {message_str}")
            return await saga_server.generic_handler(message_str, TGConversationRequest,
                                                     self.config.conversation_endpoint.generate_conversation,
                                                     saga_server.ConversationResponse)

    def run(self):
        print("""
  _______ _     _     _   _         _____       _      _     
 |__   __| |   (_)   | | | |       / ____|     | |    | |    
    | |  | |__  _ ___| |_| | ___  | |  __ _   _| | ___| |__  
    | |  | '_ \| / __| __| |/ _ \ | | |_ | | | | |/ __| '_ \ 
    | |  | | | | \__ \ |_| |  __/ | |__| | |_| | | (__| | | |
    |_|  |_| |_|_|___/\__|_|\___|  \_____|\__,_|_|\___|_| |_|
""")

        if self.runtime:
            logger.info('Runtime [Starting] ' + self.config.runtime_path)
            self.runtime.start()
        else:
            logger.info('Runtime [Skipping as None is provided]')

        # This blocks until the server is stopped.
        logger.info('Bridge [Starting]')
        web.run_app(self.app, host=self.config.host, port=self.config.port)

        logger.info('Bridge [Stopped]')

        if self.runtime:
            logger.info('Runtime [Stopping])')
            self.runtime.terminate()
            logger.info('Runtime [Stopped]')

    async def send_message(self, msg_type, data, callback: Optional[Callable[[T], Any]]):
        """
               Send a request to the runtime.
               :param msg_type: type of message.
               :param data: data to send with the message.
               :param callback: [Optional] function to call when the server responds.
               """

        async def convert_response_to_message(response_type: str, response_data: str):
            if response_data is None:
                response_data = '{}'
                logging.error(f'[Message Response] {response_type} response_data is None.')
            data = json.loads(response_data)
            response_message = GenericMessage(response_type, data=data)
            response_message.error = data.get('error')
            if response_message.error:
                logger.error(f"{response_message.type} Error: {response_message.error}")
            await callback(response_message)

        if self.simulation.sim_id is None:
            logging.error('Error: simulation client id is None.')
            if callback is not None:
                callback(GenericMessage(type='error', error='simulation_client_id is None.'))
            return

        reference = uuid.uuid4().hex
        msg = GenericMessage(type=msg_type, data=data, reference=reference)
        serialized_message = json.dumps(converter.unstructure(msg))

        if callback is not None:
            await self.sio.emit('messages', (msg.type, serialized_message), to=self.simulation.sim_id,
                                callback=convert_response_to_message)

        else:
            await self.sio.emit('messages', (msg.type, serialized_message), to=self.simulation.sim_id)


def main():

    dummy_config = BridgeConfig()

    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime', type=str, help='Path to the thistle gulch runtime and any additional arguments')
    parser.add_argument('--host', type=str, default=dummy_config.host, help='Host to listen on')
    parser.add_argument('--port', type=int, default=dummy_config.port, help='Port to listen on')
    parser.add_argument('--cors', type=str, default=dummy_config.cors, help='CORS origin')
    args = parser.parse_args()

    # Run the bridge server.
    real_config = BridgeConfig(host=args.host, port=args.port, cors=args.cors, runtime_path=args.runtime)
    bridge = RuntimeBridge(real_config)
    bridge.run()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format='<%(levelname)s> %(asctime)s - %(name)s - %(pathname)s:%(lineno)d\n    %(message)s')
    main()
