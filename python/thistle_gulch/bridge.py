import asyncio
from typing import Callable, Optional, Awaitable

import socketio
from aiohttp import web
from attr import define
import fable_saga.server as saga_server

from thistle_gulch.runtime import Runtime
from . import GenericMessage, IncomingMessageRouter, Route, logger, parse_runtime_path_and_args
from .data_models import PersonaContextObject

# Set the saga_server converter to allow extra keys in for now.
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


@define(slots=True)
class BridgeConfig:
    host: str = 'localhost'
    port: int = 8080
    cors: str = '*'
    runtime_path: str = None
    # Reuse the SAGA Actions and Conversation (Servers) as endpoints.
    actions_endpoint = saga_server.SagaServer()
    conversation_endpoint = saga_server.ConversationServer()


class RuntimeBridge:

    def __init__(self, config: BridgeConfig):
        self.config = config
        self.router = IncomingMessageRouter()
        self.on_ready: Optional[Callable[[RuntimeBridge], Awaitable[None]]] = None
        self.emit_lock = asyncio.Lock()
        self.runtime: Optional[Runtime] = None

        # Set up the async web server via aiohttp - this is the server that will handle the socketio connections.
        self.app = web.Application()

        # Set up socketio
        sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins=config.cors)
        sio.attach(self.app)
        self.sio = sio

        # Validate the runtime path and create a runtime instance.
        if self.config.runtime_path is not None:
            runtime_exec, runtime_args = parse_runtime_path_and_args(self.config.runtime_path)

            # Create the runtime instance.
            # TODO: Refactor to allow multiple runtimes running at the same time, linking sim_id and sid to the runtime.
            runtime = Runtime(sio, runtime_exec, runtime_args)
            # Associate the runtime with the socketio server so it can send messages to the runtime.
            runtime.sio = sio
            self.runtime = runtime


        ###
        # BASIC SOCKETIO EVENT HANDLERS
        ###

        @sio.event
        async def connect(sid, _):
            logger.info("[Socketio] Connected: " + sid)
            # Associate the sid with the runtime via its on_connect method.
            if self.runtime is None:
                logger.warning("Runtime is connecting to a runtime that it didn't create. Creating a new runtime.")
                self.runtime = Runtime(sio)
            await self.runtime.on_connect(sid)

        @sio.event
        async def disconnect(sid):
            logger.info("[Socketio] Disconnected: " + sid)
            await self.runtime.on_disconnect(sid)

        # Set up the socketio event handlers. These are basically channels that the server listens on.
        # The first one is a catch-all for unhandled events.
        @sio.on('*')
        def catch_all(event, sid, *data):
            """Catch all unhandled events that have one message. (common)"""
            logger.error(f"[Socketio] Unhandled event: {event} {sid} {data}")

        ###
        # STANDARD SAGA SERVER ENDPOINTS (LEGACY)
        ###

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

        ###
        # NEW RUNTIME BRIDGE ENDPOINTS (USES SINGLE STANDARD MESSAGES CHANNEL AND ROUTER)
        ###
        @sio.on('messages')
        async def on_incoming_messages(sid, message_str: str):
            return await self.router.handle_message(sid, message_str)

        # Add routes
        async def on_ready_handler(sid: str, ready_response: GenericMessage):
            """Handler for the simulation-ready message."""
            logger.info(f"[Simulation Ready] received..")

            # Call the on_ready callback if it exists.
            if self.on_ready is not None:
                # pass the bridge instance to the on_ready callback so that it can send messages to the runtime.
                logger.info(f"[Simulation Ready] Calling on_ready callback..")
                await self.on_ready(self)
            else:
                logger.info(f"[Simulation Ready] No on_ready callback registered..")

            logger.info(f"[Simulation Ready] Resuming simulation..")
            await self.runtime.api.resume()

        self.router.add_route(Route('simulation-ready', GenericMessage, on_ready_handler))

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


def main(auto_run=True) -> RuntimeBridge:
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
    if auto_run:
        bridge.run()
    return bridge
