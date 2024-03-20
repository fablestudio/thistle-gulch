import logging
from datetime import datetime, timedelta
import json
from typing import Type, Awaitable, Any, Callable, Dict, TypeVar
import cattrs
from attr import define
import uuid
import traceback
import sys

T = TypeVar('T')

logger = logging.getLogger(__name__)

# module level converter to convert between objects and dicts.
converter = cattrs.Converter(forbid_extra_keys=True)
# Register a hook to convert datetime objects to and from isoformat strings.
converter.register_unstructure_hook(datetime, lambda dt: dt.isoformat())
converter.register_structure_hook(datetime, lambda dt: dt.fromisoformat(dt))


def random_reference() -> str:
    reference = uuid.uuid4().hex
    return reference


def parse_runtime_path_and_args(runtime_path_str: str, validate_path=True) -> (str, str):
    split_args = runtime_path_str.split()
    assert len(runtime_path_str) > 0, f"Error: Empty runtime_path"

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
    if validate_path:
        import pathlib
        path = pathlib.Path(runtime_path_str)
        assert path.exists(), f"Error: --runtime path not found: \"{runtime_path_str}\""
        assert path.is_file(), f"Error: --runtime path is not a file: \"{runtime_path_str}\""

    runtime_args = split_args[runtime_arg_index:]
    return runtime_path_str, runtime_args


@define(slots=True)
class GenericMessage:
    """ A generic message that is received."""
    type: str
    data: dict = {}
    reference: str = None
    error: str = None


class Route:
    def __init__(self, msg_type: str, msg_class: Type[T], process_function: Callable[[str, T], Awaitable[None]]):
        self.msg_type = msg_type
        self.msg_class = msg_class
        self.process_function = process_function


class IncomingMessageRouter:

    def __init__(self):
        self.routes: Dict[str, Route] = {}

    def add_route(self, route: Route):
        self.routes[route.msg_type] = route

    async def handle_message(self, sid: str, message_str: str) -> Any:
        logger.debug(f"[Message] received from SID {sid}: {message_str}")
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
            result = await self.routes[message['type']].process_function(sid, request)

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
        response = GenericMessage('error', error=error)
        output = converter.unstructure(response)
        return output


if __name__ == '__main__':
    from . import bridge
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format='<%(levelname)s> %(asctime)s - %(name)s - %(pathname)s:%(lineno)d\n    %(message)s')
    bridge.main()
