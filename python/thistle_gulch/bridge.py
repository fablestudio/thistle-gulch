import asyncio
import logging
import os
from datetime import datetime
from typing import Callable, Optional, Awaitable, Dict, Any, List

from langchain_core.language_models.llms import BaseLLM
import fable_saga
import fable_saga.server as saga_server
import socketio
import yaml
import cattrs
from aiohttp import web
from attr import define

import fable_saga.server as saga_server
from fable_saga import StreamingDebugCallback
from fable_saga.actions import ActionsAgent, Action
from fable_saga.conversations import ConversationAgent
from fable_saga.server import BaseEndpoint, ActionsResponse

import thistle_gulch
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
from .data_models import (
    PersonaContextObject,
    Persona,
    WorldContextObject,
    PersonaConfig,
)

# Set the saga_server converter to allow extra keys in for now.
saga_server.converter.forbid_extra_keys = False


def get_abs_path(file_name: str) -> str:
    """Append the file name to the project or exe root"""
    root_path: Optional[str] = (
        thistle_gulch.get_exe_dir()
        if thistle_gulch.is_exe_build()
        else os.path.dirname(os.path.dirname(thistle_gulch.__file__))
    )
    return f"{root_path}/{file_name}"


def load_yaml(file_path: str) -> Optional[Any]:
    """Load yaml data from the given absolute path"""
    if not os.path.exists(file_path):
        logger.error(f"Failed to find config file at '{file_path}'")
        return None

    with open(file_path, "r") as f:
        for config_data in yaml.load(f, Loader=yaml.FullLoader):
            return config_data

    return None


# Override the default saga_server request types to include a context_obj field when working with the runtime.
@define(slots=True)
class TGActionsRequest(saga_server.ActionsRequest):
    """Enhanced ActionsRequest with a context_obj."""

    context_obj: Optional[PersonaContextObject] = None


class TGActionsEndpoint(BaseEndpoint[TGActionsRequest, ActionsResponse]):
    """Server for SAGA."""

    def __init__(
        self, agent: saga_server.ActionsAgent, model_override: Optional[str] = None
    ):
        self.agent = agent
        self.model_override = model_override

    async def handle_request(
        self, req: TGActionsRequest
    ) -> saga_server.ActionsResponse:
        # Generate actions
        try:
            assert isinstance(
                req, TGActionsRequest
            ), f"Invalid request type: {type(req)}"

            # Disable request model overrides now that we're using a config
            # Override the model or use the one included in the request
            # model = self.model_override if self.model_override else req.model

            actions = await self.agent.generate_actions(
                req.context, req.skills, req.retries, req.verbose,  # model
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


class TGConversationEndpoint(
    BaseEndpoint[TGConversationRequest, saga_server.ConversationResponse]
):
    """Server for SAGA."""

    def __init__(
        self, agent: saga_server.ConversationAgent, model_override: Optional[str] = None
    ):
        self.agent = agent
        self.model_override = model_override

    async def handle_request(
        self, req: TGConversationRequest
    ) -> saga_server.ConversationResponse:
        # Generate conversation
        try:
            assert isinstance(
                req, TGConversationRequest
            ), f"Invalid request type: {type(req)}"

            # Disable request model overrides now that we're using a config
            # Override the model or use the one included in the request
            # model = self.model_override if self.model_override else req.model

            conversation = await self.agent.generate_conversation(
                req.persona_guids,
                req.context,
                req.retries,
                req.verbose,
                # model,
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

        runtime_version = msg.data.get("runtime_version", "")
        if runtime_version != "local.build" and not runtime_version.startswith(
            self.bridge.runtime.required_version
        ):
            raise Exception(
                f"Incorrect Runtime version detected - "
                f"'{self.bridge.runtime.required_version}' was expected but '{runtime_version}' was found instead"
            )

        logger.debug(f"[Simulation Ready] Pausing simulation during initialization..")
        await self.bridge.runtime.api.pause()

        world_context = await self.bridge.runtime.api.get_world_context()

        # Uncomment to update personas config to latest from Runtime
        # file_path = (
        #     os.path.dirname(os.path.dirname(thistle_gulch.__file__))
        #     + "/personas_config.yaml"
        # )
        # with open(file_path, "w") as f:
        #     yaml.dump(
        #         world_context.personas,
        #         f,
        #         default_style="",
        #         default_flow_style=False,
        #         width=10000,
        #         sort_keys=False,
        #     )

        if self.bridge.persona_configs:
            logger.debug(f"[Simulation Ready] Configuring personas..")
            for persona_cfg in self.bridge.persona_configs:
                if not persona_cfg.persona_guid:
                    continue

                # Verify that this persona_guid is valid
                existing_persona = next(
                    (
                        p
                        for p in world_context.personas
                        if p.persona_guid == persona_cfg.persona_guid
                    ),
                    None,
                )
                if existing_persona is None:
                    logger.error(
                        f"[Simulation Ready] While configuring personas: persona_guid not found: '{persona_cfg.persona_guid}'"
                    )
                    continue

                if persona_cfg.summary:
                    await self.bridge.runtime.api.update_character_property(
                        persona_cfg.persona_guid, "summary", persona_cfg.summary
                    )

                if persona_cfg.description:
                    await self.bridge.runtime.api.update_character_property(
                        persona_cfg.persona_guid, "description", persona_cfg.description
                    )

                if persona_cfg.backstory:
                    await self.bridge.runtime.api.update_character_property(
                        persona_cfg.persona_guid, "backstory", persona_cfg.backstory
                    )

                if persona_cfg.actions_enabled or persona_cfg.conversations_enabled:
                    await self.bridge.runtime.api.enable_agent(
                        persona_cfg.persona_guid,
                        persona_cfg.actions_enabled,
                        persona_cfg.conversations_enabled,
                    )

                if persona_cfg.memories:
                    await self.bridge.runtime.api.character_memory_clear(persona_cfg.persona_guid)
                    for memory_cfg in persona_cfg.memories:
                        memory = await self.bridge.runtime.api.character_memory_add(
                            persona_guid=persona_cfg.persona_guid,
                            timestamp=memory_cfg.timestamp,
                            summary=memory_cfg.summary,
                            entity_ids=memory_cfg.entity_ids,
                            position=memory_cfg.position,
                            importance_weight=memory_cfg.importance_weight,
                        )

        # Call the on_ready callback if it exists.
        if self.bridge.on_ready is not None:
            # pass the bridge instance to the on_ready callback so that it can send messages to the runtime.
            logger.debug(f"[Simulation Ready] Calling on_ready callback..")
            resume = await self.bridge.on_ready(self.bridge, world_context)
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

        event_name: str = msg.data.get("event_name", "")
        event_data: Dict[Any, Any] = msg.data.get("event_data", {})
        response_data: Dict[Any, Any] = {}

        # Check if the event has an event_future associated with it.
        # If it does, set the result of the future and remove it from the event_futures dict.
        # This is used for waiting on events in the runtime that were triggered by another api call. (eg. modals)
        event_futures = self.bridge.runtime.event_futures
        if msg.reference in event_futures:
            event_futures[msg.reference].set_result(event_data)
            del event_futures[msg.reference]

        # on_action_complete callback
        elif (
            self.bridge.on_action_complete is not None
            and event_name == "on-action-complete"
            and event_data
        ):
            persona_guid = event_data.get("persona_guid", "")
            completed_action = event_data.get("completed_action", "")
            # pass the bridge instance to the on_tick callback so that it can send messages to the runtime.
            logger.debug(f"[On Action Complete] Calling on_action_complete callback..")
            action = await self.bridge.on_action_complete(
                self.bridge, persona_guid, completed_action
            )
            if action is not None:
                response_data["action"] = action

        # on_character_focused callback
        elif (
            self.bridge.on_character_focused is not None
            and event_name == "on-character-focused"
            and event_data
        ):
            persona_guid = event_data.get("persona_guid", "")
            # pass the bridge instance to the on_tick callback so that it can send messages to the runtime.
            logger.debug(
                f"[On Character Focused] Calling on_character_focused callback.."
            )
            await self.bridge.on_character_focused(self.bridge, persona_guid)

        # on_character_unfocused callback
        elif (
            self.bridge.on_character_unfocused is not None
            and event_name == "on-character-unfocused"
            and event_data
        ):
            persona_guid = event_data.get("persona_guid", "")
            # pass the bridge instance to the on_tick callback so that it can send messages to the runtime.
            logger.debug(
                f"[On Character Unfocused] Calling on_character_unfocused callback.."
            )
            await self.bridge.on_character_unfocused(self.bridge, persona_guid)

        # on_sim_object_selected callback
        elif (
            self.bridge.on_sim_object_selected is not None
            and event_name == "on-sim-object-selected"
            and event_data
        ):
            guid = event_data.get("guid", "")
            # pass the bridge instance to the on_tick callback so that it can send messages to the runtime.
            logger.debug(
                f"[On Sim Object Selected] Calling on_sim_object_selected callback.."
            )
            await self.bridge.on_sim_object_selected(self.bridge, guid)

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


@define(slots=True)
class PersonasConfig:
    personas: List[Persona] = []


@define(slots=True)
class LlmConfig:
    action_generation_model: Optional[str] = None
    conversation_generation_model: Optional[str] = None


@define(slots=True)
def dynamic_model_loader(model_cfg: dict) -> BaseLLM:

    """Load a model dynamically based on the configuration."""
    if model_cfg.get("import") is None or model_cfg.get("class") is None:
        raise Exception("Model configuration must include 'import' and 'class' fields.")

    # Import the module and get the class.
    module = __import__(model_cfg["import"], fromlist=[model_cfg["class"]])
    model_class = getattr(module, model_cfg["class"])

    # Create an instance of the class with the provided parameters.
    llm: BaseLLM = model_class(**model_cfg.get("params", {}))

    # Add the fable_saga callbacks to the model.
    if llm.callbacks is None:
        llm.callbacks = [
            fable_saga.StreamingDebugCallback(),
            fable_saga.SagaCallbackHandler(),
        ]
    return llm


@define(slots=True)
class BridgeConfig:
    host: str = "localhost"
    port: int = 8080
    cors: str = "*"
    runtime_path: Optional[str] = None
    action_llm: dict = {}
    conversation_llm: dict = {}


class RuntimeBridge:

    def __init__(self, config: BridgeConfig, persona_configs: List[PersonaConfig]):
        self.config = config
        self.persona_configs = persona_configs
        self.router = IncomingMessageRouter()
        self.on_ready: Optional[
            Callable[[RuntimeBridge, WorldContextObject], Awaitable[bool]]
        ] = None
        self.on_tick: Optional[Callable[[RuntimeBridge, datetime], Awaitable[None]]] = (
            None
        )
        self.on_event: Optional[
            Callable[[RuntimeBridge, str, dict], Awaitable[None]]
        ] = None
        self.on_action_complete: Optional[
            Callable[[RuntimeBridge, str, str], Awaitable[Optional[Action]]]
        ] = None
        self.on_character_focused: Optional[
            Callable[[RuntimeBridge, str], Awaitable[None]]
        ] = None
        self.on_character_unfocused: Optional[
            Callable[[RuntimeBridge, str], Awaitable[None]]
        ] = None
        self.on_sim_object_selected: Optional[
            Callable[[RuntimeBridge, str], Awaitable[None]]
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

        # No runtime was provided - if this project is running as an app find the included runtime build
        if not self.config.runtime_path:
            default_exe_path = thistle_gulch.get_exe_dir()
            if default_exe_path:
                runtime_exec_path = f"{default_exe_path}/ThistleGulch.exe"
                if os.path.exists(runtime_exec_path):
                    self.config.runtime_path = runtime_exec_path

        # Validate the runtime path and create a runtime instance.
        if self.config.runtime_path:
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

        if self.config.runtime_path:
            self.runtime.start()
        else:
            logger.warning("[Bridge] Skipping Runtime Start as no path was provided")

        # Set the routes for SAGA stuff if not already defined using the defaults.
        # This allows custom routes to be added before the server is started and
        # avoiding using OpenAI. If langchain_openai in not installed, this will fail.
        if IncomingRoutes.generate_actions.value not in self.router.routes:
            llm = dynamic_model_loader(self.config.action_llm)
            self.router.add_route(
                Route(
                    IncomingRoutes.generate_actions.value,
                    TGActionsEndpoint(
                        ActionsAgent(llm=llm),
                    ),
                    logging.DEBUG,
                    MessageSystem.ENDPOINTS,
                )
            )
        if IncomingRoutes.generate_conversations.value not in self.router.routes:
            llm = dynamic_model_loader(self.config.conversation_llm)
            self.router.add_route(
                Route(
                    IncomingRoutes.generate_conversations.value,
                    TGConversationEndpoint(
                        ConversationAgent(llm=llm),
                    ),
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
    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runtime",
        type=str,
        help="Path to the thistle gulch runtime and any additional arguments",
    )
    parser.add_argument("--host", type=str, help="Host to listen on")
    parser.add_argument("--port", type=int, help="Port to listen on")
    parser.add_argument("--cors", type=str, help="CORS origin")
    parser.add_argument(
        "--bridge_config",
        type=str,
        default="bridge_config.yaml",
        help="Path to a config file",
    )
    parser.add_argument(
        "--personas_config",
        type=str,
        default="personas_config.yaml",
        help="Path to a personas config file",
    )
    args = parser.parse_args()

    # Load the bridge config file from disk
    bridge_config = BridgeConfig()
    if args.bridge_config:
        bridge_config_path = args.bridge_config.replace("\\", "/")
        # If it's a file name, get the absolute path
        if "/" not in bridge_config_path:
            bridge_config_path = get_abs_path(bridge_config_path)
        # Load and structure the yaml
        bridge_config_yaml = load_yaml(bridge_config_path)
        if bridge_config_yaml:
            bridge_config = cattrs.structure(bridge_config_yaml, BridgeConfig)

    # Load the personas config file from disk
    personas_config = []
    if args.personas_config:
        personas_config_path = args.personas_config.replace("\\", "/")
        # If it's a file name, get the absolute path
        if "/" not in personas_config_path:
            personas_config_path = get_abs_path(personas_config_path)
        # Load and structure the yaml
        personas_config_yaml = load_yaml(personas_config_path)
        if personas_config_yaml:
            personas_config = cattrs.structure(personas_config_yaml.get("personas"), List[PersonaConfig])

    # Command-line arguments override the config values on disk
    if args.host:
        bridge_config.host = args.host
    if args.port:
        bridge_config.port = args.port
    if args.cors:
        bridge_config.cors = args.cors
    if args.runtime:
        bridge_config.runtime_path = args.runtime

    # Run the bridge server.
    bridge = RuntimeBridge(bridge_config, personas_config)
    if auto_run:
        bridge.run()
    return bridge
