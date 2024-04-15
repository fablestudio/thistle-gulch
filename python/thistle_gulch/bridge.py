import asyncio
import logging
from datetime import datetime
from typing import Callable, Optional, Awaitable, Dict, Any

import fable_saga.server as saga_server
import socketio
from aiohttp import web
from attr import define
from fable_saga.actions import ActionsAgent
from fable_saga.conversations import ConversationAgent
from fable_saga.server import BaseEndpoint, ActionsResponse

from thistle_gulch.runtime import Runtime
from . import (
    GenericMessage,
    IncomingMessageRouter,
    Route,
    logger,
    parse_runtime_path_and_args,
    converter,
    MessageSystem,
    IncomingRoutes,
)
from .data_models import PersonaContextObject

# Set the saga_server converter to allow extra keys in for now.
saga_server.converter.forbid_extra_keys = False


# Override the default saga_server request types to include a context_obj field when working with the runtime.
@define(slots=True)
class TGActionsRequest(saga_server.ActionsRequest):
    """Enhanced ActionsRequest with a context_obj."""

    context_obj: Optional[PersonaContextObject] = None


class TGActionsEndpoint(BaseEndpoint[TGActionsRequest, ActionsResponse]):
    """Server for SAGA."""

    def __init__(self, agent: saga_server.ActionsAgent):
        self.agent = agent

    async def handle_request(
        self, req: TGActionsRequest
    ) -> saga_server.ActionsResponse:
        # Generate actions
        try:
            assert isinstance(
                req, TGActionsRequest
            ), f"Invalid request type: {type(req)}"
            actions = await self.agent.generate_actions(
                req.context, req.skills, req.retries, req.verbose, req.model
            )

            response = saga_server.ActionsResponse(
                actions=actions, reference=req.reference, error=None
            )
            if actions.error:
                response.error = f"Generation Error: {actions.error}"
            return response
        except Exception as e:
            logger.exception(str(e))
            return saga_server.ActionsResponse(
                actions=None, error=str(e), reference=req.reference
            )


@define(slots=True)
class TGConversationRequest(saga_server.ConversationRequest):
    """Enhanced ConversationRequest with a context_obj."""

    context_obj: Optional[PersonaContextObject] = None


class TGConversationEndpoint(saga_server.ConversationEndpoint):
    """Server for SAGA."""

    def __init__(self, agent: saga_server.ConversationAgent):
        super().__init__(agent)

    async def generate_conversation(
        self, req: TGConversationRequest
    ) -> saga_server.ConversationResponse:
        # Generate conversation
        try:
            assert isinstance(
                req, TGConversationRequest
            ), f"Invalid request type: {type(req)}"
            conversation = await self.agent.generate_conversation(
                req.persona_guids,
                req.context,
                req.retries,
                req.verbose,
                req.model,
            )

            response = saga_server.ConversationResponse(
                conversation=conversation, reference=req.reference, error=None
            )
            if conversation.error:
                response.error = f"Generation Error: {conversation.error}"
            return response
        except Exception as e:
            logger.exception(str(e))
            return saga_server.ConversationResponse(
                conversation=None, error=str(e), reference=req.reference
            )


class OnReadyEndpoint(BaseEndpoint[GenericMessage, None]):

    def __init__(self, bridge: "RuntimeBridge"):
        self.bridge = bridge

    async def handle_request(self, msg: GenericMessage):
        """Handler for the simulation-ready message."""
        logger.debug(f"[Simulation Ready] received..")

        self.bridge.runtime.start_date = converter.structure(
            msg.data.get("start_date"), datetime
        )

        runtime_version = msg.data.get("runtime_version")
        if (
            runtime_version != "local.build"
            and runtime_version != self.bridge.runtime.required_version
        ):
            raise Exception(
                f"Incorrect Runtime version detected - "
                f"'{self.bridge.runtime.required_version}' was expected but '{runtime_version}' was found instead"
            )

        logger.debug(f"[Simulation Ready] Pausing simulation during initialization..")
        await self.bridge.runtime.api.pause()

        # Call the on_ready callback if it exists.
        if self.bridge.on_ready is not None:
            # pass the bridge instance to the on_ready callback so that it can send messages to the runtime.
            logger.debug(f"[Simulation Ready] Calling on_ready callback..")
            resume = await self.bridge.on_ready(self.bridge)
        else:
            logger.debug(f"[Simulation Ready] No on_ready callback registered..")
            resume = True

        if resume:
            logger.debug(f"[Simulation Ready] Resuming simulation..")
            await self.bridge.runtime.api.resume()


class OnSimulationTickEndpoint(BaseEndpoint[GenericMessage, None]):

    def __init__(self, bridge: "RuntimeBridge"):
        self.bridge = bridge

    async def handle_request(self, msg: GenericMessage):
        """Handler for the simulation-tick message."""
        logger.debug(f"[Simulation Tick] received..")

        # Call the on_tick callback if it exists.
        if self.bridge.on_tick is not None:
            current_time = converter.structure(msg.data.get("current_time"), datetime)
            # pass the bridge instance to the on_tick callback so that it can send messages to the runtime.
            logger.debug(f"[Simulation Tick] Calling on_tick callback..")
            await self.bridge.on_tick(self.bridge, current_time)
        else:
            logger.debug(f"[Simulation Tick] No on_tick callback registered..")


class OnSimulationEventEndpoint(BaseEndpoint[GenericMessage, GenericMessage]):

    def __init__(self, bridge: "RuntimeBridge"):
        self.bridge = bridge

    async def handle_request(self, msg: GenericMessage) -> GenericMessage:
        """Handler for the simulation-event message."""
        logger.debug(f"[Simulation Event] received..")

        event_name = msg.data.get("event_name", "")
        event_data = msg.data.get("event_data", {})
        response_data: Dict[Any, Any] = {}

        # Dedicated callback handling for on_action_complete
        if (
            self.bridge.on_action_complete is not None
            and event_name == "on-action-complete"
            and event_data
        ):
            persona_id = event_data.get("persona_id", "")
            completed_action = event_data.get("completed_action", "")
            # pass the bridge instance to the on_tick callback so that it can send messages to the runtime.
            logger.debug(f"[On Action Complete] Calling on_action_complete callback..")
            action = await self.bridge.on_action_complete(
                self.bridge, persona_id, completed_action
            )
            response_data['action'] = action

        # Call the on_event callback if it exists.
        if self.bridge.on_event is not None:
            # pass the bridge instance to the on_event callback so that it can send messages to the runtime.
            logger.debug(f"[Simulation Event] Calling on_event callback..")
            await self.bridge.on_event(self.bridge, event_name, event_data)
        else:
            logger.debug(f"[Simulation Event] No on_event callback registered..")

        return GenericMessage(
            IncomingRoutes.simulation_event.value + "-response",
            response_data,
            msg.reference,
        )


class OnSimulationErrorEndpoint(BaseEndpoint[GenericMessage, None]):

    def __init__(self, bridge: "RuntimeBridge"):
        self.bridge = bridge

    async def handle_request(self, msg: GenericMessage):
        """Handler for the on-error message."""
        logger.debug(f"[Simulation Error] received..")

        # Call the on_error callback if it exists.
        if self.bridge.on_error is not None:
            error = msg.data.get("error", "")
            # pass the bridge instance to the on_tick callback so that it can send messages to the runtime.
            logger.debug(f"[Simulation Error] Calling on_error callback..")
            await self.bridge.on_error(self.bridge, error)
        else:
            logger.debug(f"[Simulation Error] No on_error callback registered..")


@define
class BridgeConfig:
    host: str = "localhost"
    port: int = 8080
    cors: str = "*"
    runtime_path: Optional[str] = None


class RuntimeBridge:

    def __init__(self, config: BridgeConfig):
        self.config = config
        self.router = IncomingMessageRouter()
        self.on_ready: Optional[Callable[[RuntimeBridge], Awaitable[bool]]] = None
        self.on_tick: Optional[Callable[[RuntimeBridge, datetime], Awaitable[None]]] = (
            None
        )
        self.on_event: Optional[
            Callable[[RuntimeBridge, str, dict], Awaitable[None]]
        ] = None
        self.on_action_complete: Optional[
            Callable[[RuntimeBridge, str, str], Awaitable[GenericMessage]]
        ] = None

        # By default, we just log every error unless the user overrides the callback
        async def on_error(_, msg: str):
            logger.error(msg)

        self.on_error: Callable[[RuntimeBridge, str], Awaitable[None]] = on_error

        self.emit_lock = asyncio.Lock()

        # Set up the async web server via aiohttp - this is the server that will handle the socketio connections.
        self.app = web.Application()

        # Set up socketio
        sio = socketio.AsyncServer(
            async_mode="aiohttp", cors_allowed_origins=config.cors
        )
        sio.attach(self.app)
        self.sio = sio

        # Validate the runtime path and create a runtime instance.
        if self.config.runtime_path is not None:
            runtime_exec, runtime_args = parse_runtime_path_and_args(
                self.config.runtime_path
            )

            # Create the runtime instance.
            # TODO: Refactor to allow multiple runtimes running at the same time, linking sim_id and sid to the runtime.
            self.runtime = Runtime(sio, runtime_exec, runtime_args)
        else:
            logger.warning("No runtime path provided. Runtime will not be started.")
            self.runtime = Runtime(sio)

        ###
        # BASIC SOCKETIO EVENT HANDLERS
        ###

        @sio.event
        async def connect(sid, _):
            logger.info("[Socketio] Connected: " + sid)
            # Associate the sid with the runtime via its on_connect method.
            if self.runtime is None:
                logger.warning(
                    "Runtime is connecting to a runtime that it didn't create. Creating a new runtime."
                )
                self.runtime = Runtime(sio)
            await self.runtime.on_connect(sid)

        @sio.event
        async def disconnect(sid):
            logger.info("[Socketio] Disconnected: " + sid)
            await self.runtime.on_disconnect(sid)

        ###
        # OLD RUNTIME BRIDGE ENDPOINTS (USE INDIVIDUAL CHANNELS AND ROUTERS)
        ###

        @sio.on("*")
        async def catch_all(event, sid, *data):
            """Set up the socketio event handlers. These are basically channels that the server listens on.
            This is a catch-all for otherwise unhandled events with a matching @sio.on(NAME).
            """

            # Check if the event is handled by the router.
            route = self.router.routes.get(event)
            if not route:
                logger.error(f"[Socketio] Unhandled event: {event} {sid} {data}")
                return
            if len(data) != 1 or not isinstance(data[0], str):
                logger.error(
                    f"[Socketio] Unhandled event: {event} {sid} {data}: expected 1 data item, got {len(data)}"
                )
                return
            message_str = data[0]
            # Process the message using the route's process_function.
            logger.debug(f"[Endpoint] Received {event} from {sid}")
            resp = await saga_server.generic_handler(
                message_str,
                route.endpoint,
            )
            return resp

        ###
        # NEW RUNTIME BRIDGE ENDPOINTS (USES SINGLE STANDARD MESSAGES CHANNEL AND ROUTER)
        ###
        @sio.on("messages")
        async def on_incoming_messages(sid, message_str: str):
            return await self.router.handle_message(sid, message_str)

        ###
        # ADD ROUTES
        ###
        self.router.add_route(
            Route(
                IncomingRoutes.simulation_ready.value,
                OnReadyEndpoint(self),
                logging.INFO,
            )
        )
        self.router.add_route(
            Route(IncomingRoutes.simulation_tick.value, OnSimulationTickEndpoint(self))
        )
        self.router.add_route(
            Route(
                IncomingRoutes.simulation_event.value, OnSimulationEventEndpoint(self)
            )
        )
        self.router.add_route(
            Route(
                IncomingRoutes.simulation_error.value, OnSimulationErrorEndpoint(self)
            )
        )

    def run(self):
        print(
            """
  _______ _     _     _   _         _____       _      _     
 |__   __| |   (_)   | | | |       / ____|     | |    | |    
    | |  | |__  _ ___| |_| | ___  | |  __ _   _| | ___| |__  
    | |  | '_ \| / __| __| |/ _ \ | | |_ | | | | |/ __| '_ \ 
    | |  | | | | \__ \ |_| |  __/ | |__| | |_| | | (__| | | |
    |_|  |_| |_|_|___/\__|_|\___|  \_____|\__,_|_|\___|_| |_|
"""
        )

        if self.config.runtime_path is not None:
            self.runtime.start()
        else:
            logger.warning("[Bridge] Skipping Runtime Start as no path was provided")

        # Set the routes for SAGA stuff if not already defined using the defaults.
        # This allows custom routes to be added before the server is started and
        # avoiding using OpenAI. If langchain_openai in not installed, this will fail.
        if IncomingRoutes.generate_actions.value not in self.router.routes:
            self.router.add_route(
                Route(
                    IncomingRoutes.generate_actions.value,
                    TGActionsEndpoint(ActionsAgent()),
                    logging.DEBUG,
                    MessageSystem.ENDPOINTS,
                )
            )
        if IncomingRoutes.generate_conversations.value not in self.router.routes:
            self.router.add_route(
                Route(
                    IncomingRoutes.generate_conversations.value,
                    saga_server.ConversationEndpoint(ConversationAgent()),
                    logging.DEBUG,
                    MessageSystem.ENDPOINTS,
                )
            )

        # This blocks until the server is stopped.
        logger.info("[Bridge] Starting")
        web.run_app(self.app, host=self.config.host, port=self.config.port)
        logger.info("[Bridge] Stopped")

        if self.runtime:
            self.runtime.terminate()


def main(auto_run=True) -> RuntimeBridge:
    dummy_config = BridgeConfig()

    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runtime",
        type=str,
        help="Path to the thistle gulch runtime and any additional arguments",
    )
    parser.add_argument(
        "--host", type=str, default=dummy_config.host, help="Host to listen on"
    )
    parser.add_argument(
        "--port", type=int, default=dummy_config.port, help="Port to listen on"
    )
    parser.add_argument(
        "--cors", type=str, default=dummy_config.cors, help="CORS origin"
    )
    args = parser.parse_args()

    # Run the bridge server.
    real_config = BridgeConfig(
        host=args.host, port=args.port, cors=args.cors, runtime_path=args.runtime
    )
    bridge = RuntimeBridge(real_config)
    if auto_run:
        bridge.run()
    return bridge
