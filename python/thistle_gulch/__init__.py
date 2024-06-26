import json
import logging
import os
import sys
import traceback
import uuid
from datetime import datetime
from typing import Type, Awaitable, Any, Callable, Dict, TypeVar, Tuple, Optional, List
from enum import Enum

import cattrs
from attr import define
from fable_saga.server import BaseEndpoint, get_generic_types

logger = logging.getLogger(__name__)

# module level converter to convert between objects and dicts.
converter = cattrs.Converter(forbid_extra_keys=True)
# Register a hook to convert datetime objects to and from isoformat strings.
converter.register_unstructure_hook(datetime, lambda dt: dt.isoformat())
converter.register_structure_hook(datetime, lambda dt, _: datetime.fromisoformat(dt))


def random_reference() -> str:
    reference = uuid.uuid4().hex
    return reference


def json_strict_loads(s: str) -> Dict:
    ret = json.loads(s)
    if not isinstance(ret, dict):
        raise TypeError(f"Expected a JSON object, but got {type(ret)}")
    return ret


def parse_runtime_path_and_args(
    runtime_path_str: str, validate_path=True
) -> Tuple[str, List[str]]:
    split_args = runtime_path_str.split()
    assert len(runtime_path_str) > 0, f"Error: Empty runtime_path"

    runtime_arg_index = 1
    runtime_path_str = split_args[0]
    for runtime_arg_index in range(1, len(split_args)):
        arg = split_args[runtime_arg_index]
        # Detect the first runtime flag
        if arg.startswith("-"):
            break
        # Re-join the runtime path if it has space
        else:
            runtime_path_str += " " + arg

    # Validate runtime path
    if validate_path:
        import pathlib

        path = pathlib.Path(runtime_path_str)
        assert path.exists(), f"Error: --runtime path not found: '{runtime_path_str}'"
        assert (
            path.is_file()
        ), f"Error: --runtime path is not a file: '{runtime_path_str}'"

    runtime_args = split_args[runtime_arg_index:]
    return runtime_path_str, runtime_args


# def is_exe_running(exe_name: str) -> bool:
#     for process in psutil.process_iter():
#         if process.name() == exe_name:
#             return True
#     return False
#
#
# def kill_exe(exe_name: str):
#     for process in psutil.process_iter():
#         if process.name() == exe_name:
#             process.kill()
#
#
# def is_app_window_running(window_name: str) -> bool:
#     result = subprocess.check_output(f'tasklist /fi "WINDOWTITLE eq {window_name}"').decode('cp866', 'ignore')
#     return 'INFO: No tasks are running' not in result


def is_exe_build() -> bool:
    """
    Is the current python process launched from a built exe file?
    """
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_exe_dir() -> Optional[str]:
    return os.path.dirname(sys.executable) if is_exe_build() else None


@define(slots=True)
class GenericMessage:
    """A generic message that is received."""

    type: str
    data: dict = {}
    reference: Optional[str] = None
    error: Optional[str] = None


class MessageSystem(Enum):
    """The message system to use."""

    MESSAGES = "messages"
    ENDPOINTS = "endpoints"


class IncomingRoutes(Enum):
    """The message types to use."""

    generate_actions = "generate-actions"
    generate_conversations = "generate-conversation"
    simulation_ready = "simulation-ready"
    simulation_event = "simulation-event"
    simulation_tick = "simulation-tick"
    simulation_error = "simulation-error"


@define
class Route:
    msg_type: str
    endpoint: BaseEndpoint
    log_level: int = logging.DEBUG
    system: MessageSystem = MessageSystem.MESSAGES


class IncomingMessageRouter:

    def __init__(self):
        self.routes: Dict[str, Route] = {}

    def add_route(self, route: Route):
        self.routes[route.msg_type] = route

    async def handle_message(self, sid: str, message_str: str) -> Any:
        logger.debug(f"[Message] received from SID {sid}: {message_str}")
        ex: Exception
        try:
            # Convert the message to a dictionary and validate that it has a type and that the type has a known route.
            message = json.loads(message_str)
            logger.debug(
                f"[Message] sid: {sid}, type: {message.get('type', 'unknown')}, ref: {message.get('reference', 'unknown')}"
            )
            msg_type = message.get("type")
            if msg_type is None:
                raise ValueError("Message is missing a type.")
            if msg_type not in self.routes:
                raise ValueError(f"Unknown message type: {msg_type}")
            route = self.routes[msg_type]

            # Convert the message to the appropriate type and process it.
            request_type, response_type = get_generic_types(route.endpoint)
            request = converter.structure(message, request_type)
            logger.log(route.log_level, f"[Message] request: {request}")
            result = await route.endpoint.handle_request(request)
            logger.log(route.log_level, f"[Message] response: {result}")

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
        if ex is not None:
            logger.error(
                f"[Error] sid: {sid}, message: {message_str}, error: {error}, "
                f"stacktrace: {''.join(traceback.TracebackException.from_exception(ex).format())}"
            )

        response = GenericMessage("error", error=error)
        output = converter.unstructure(response)
        return output


if __name__ == "__main__":
    from . import bridge

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="<%(levelname)s> %(asctime)s - %(name)s - %(pathname)s:%(lineno)d\n    %(message)s",
    )
    bridge.main()
