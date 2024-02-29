import json
import logging
from typing import List, Optional, Type, Dict, Union
import subprocess

import fable_saga
from fable_saga.conversations import GeneratedConversation, ConversationAgent
import cattrs
import socketio
from aiohttp import web
from attr import define
from langchain.chat_models.base import BaseLanguageModel

from . import Runtime


logger = logging.getLogger(__name__)

# module level converter to convert between objects and dicts.
converter = cattrs.Converter(forbid_extra_keys=True)

"""
Sets up a server that can be used to generate actions for SAGA. Either HTTP or socketio can be used.
"""


@define(slots=True)
class ActionsRequest:
    """Request to generate actions."""
    context: str
    skills: List[fable_saga.Skill]
    retries: int = 0
    verbose: bool = False
    reference: Optional[str] = None
    model: Optional[str] = None


@define(slots=True)
class ActionsResponse:
    """Response from generating actions."""
    actions: Optional[fable_saga.GeneratedActions] = None
    error: str = None
    reference: Optional[str] = None


@define(slots=True)
class ConversationRequest:
    """Request to generate a conversation."""
    context: str
    persona_guids: List[str]
    retries: int = 0
    verbose: bool = False
    reference: Optional[str] = None
    model: Optional[str] = None


@define(slots=True)
class ConversationResponse:
    """Response from generating a conversation."""
    conversation: Optional[GeneratedConversation] = None
    error: str = None
    reference: Optional[str] = None


@define(slots=True)
class ErrorResponse:
    """Generic Error Response."""
    error: str = None


class ActionsEndpoint:

    def __init__(self, llm: BaseLanguageModel = None):
        super().__init__()
        self.agent = fable_saga.SagaAgent(llm)

    async def generate_actions(self, req: ActionsRequest) -> ActionsResponse:
        # Generate actions
        try:
            assert isinstance(req, ActionsRequest), f"Invalid request type: {type(req)}"
            actions = await self.agent.generate_actions(req.context, req.skills, req.retries, req.verbose, req.model)
            response = ActionsResponse(actions=actions, reference=req.reference)
            if actions.error is not None:
                response.error = f"Generation Error: {actions.error}"
            return response
        except Exception as e:
            logger.error(str(e))
            return ActionsResponse(actions=None, error=str(e), reference=req.reference)


class ConversationEndpoint:

    def __init__(self, llm: BaseLanguageModel = None):
        super().__init__()
        self.agent = ConversationAgent(llm)

    async def generate_conversation(self, req: ConversationRequest) -> ConversationResponse:
        # Generate conversation
        try:
            assert isinstance(req, ConversationRequest), f"Invalid request type: {type(req)}"
            conversation = await self.agent.generate_conversation(req.persona_guids, req.context, req.retries,
                                                                  req.verbose, req.model)
            response = ConversationResponse(conversation=conversation, reference=req.reference)
            if conversation.error is not None:
                response.error = f"Generation Error: {conversation.error}"
            return response
        except Exception as e:
            logger.error(str(e))
            return ConversationResponse(conversation=None, error=str(e), reference=req.reference)


async def generic_handler(data: Union[str, Dict], request_type: Type, process_function, response_type: Type):
    try:
        if isinstance(data, str):
            data = json.loads(data)
        # noinspection PyTypeChecker
        request = converter.structure(data, request_type)
        result = await process_function(request)
        assert isinstance(result, response_type), (f"Invalid response type: {type(result)},"
                                                   f" expected instance of {response_type}")
        response = converter.unstructure(result)
        logger.debug(f"Response: {response}")
        return response
    except json.decoder.JSONDecodeError as e:
        error = f"Error decoding JSON: {str(e)}"
    except cattrs.errors.ClassValidationError as e:
        error = f"Error validating request: {json.dumps(cattrs.transform_error(e))}"
    except Exception as e:
        error = f"Error processing request: {str(e)}"
    logger.error(error)
    response = response_type(error=error)
    output = converter.unstructure(response)
    return output

if __name__ == '__main__':

    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime', type=str, help='Path to the thistle gulch runtime and any additional arguments')
    parser.add_argument('--host', type=str, default='localhost', help='Host to listen on')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    parser.add_argument('--cors', type=str, default=None, help='CORS origin')
    args = parser.parse_args()

    runtime = None
    if args.runtime is not None:
        split_args = args.runtime.split()
        assert len(split_args) > 0
        import pathlib
        path = pathlib.Path(split_args[0])
        assert path.exists()
        assert path.is_file()
        runtime = Runtime(split_args[0], split_args[1:])
        runtime.start()

    # Create common server objects
    # Note: This is where you could override the LLM by passing the llm parameter to SagaServer.
    actions_endpoint = ActionsEndpoint()
    conversation_endpoint = ConversationEndpoint()

    app = web.Application()

    # Create socketio server
    if args.cors is None:
        args.cors = '*'
    sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins=args.cors)
    sio.attach(app)

    @sio.event
    def connect(sid, _):
        logger.info("connect:" + sid)

    @sio.event
    def disconnect(sid):
        logger.info("disconnect:" + sid)

    @sio.on('*')
    def catch_all(event, sid, *data):
        """Catch all unhandled events that have one message. (common)"""
        logger.error(f"Unhandled event: {event} {sid} {data}")

    @sio.on('generate-actions')
    async def generate_actions(sid, message_str: str):
        logger.debug(f"Request from {sid}: {message_str}")
        return await generic_handler(message_str, ActionsRequest, actions_endpoint.generate_actions,
                                     ActionsResponse)

    @sio.on('generate-conversation')
    async def generate_conversation(sid, message_str: str):
        logger.debug(f"Request from {sid}: {message_str}")
        return await generic_handler(message_str, ConversationRequest, conversation_endpoint.generate_conversation,
                                     ConversationResponse)

    # Setup logging
    formatter = logging.Formatter('%(asctime)s - saga.server - %(levelname)s - %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Run server
    web.run_app(app, host=args.host, port=args.port)

    if runtime:
        runtime.terminate()
