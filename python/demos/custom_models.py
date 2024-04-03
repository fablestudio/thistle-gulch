import json
from typing import Dict, Any, List

import fable_saga.actions
import fable_saga.conversations
import fable_saga.server as saga_server
import langchain_core.callbacks
from langchain_core.outputs import LLMResult
from cattrs import unstructure

from thistle_gulch.bridge import (
    RuntimeBridge,
    TGActionsEndpoint,
    Route,
    IncomingRoutes,
    TGActionsRequest,
)
from . import Demo

CATEGORY = "Custom Models"


class OllamaActionsEndpoint(TGActionsEndpoint):
    """Endpoint for generating actions using Ollama.

    This overrides the actions generation prompt to keep it very simple for now. The original, it seems, was too complex
    for Ollama(mistral:7b-instruct) to handle."""

    async def handle_request(
        self, req: TGActionsRequest
    ) -> saga_server.ActionsResponse:

        new_context = ""
        if req.context_obj is not None:
            new_context += f"CHARACTERS\n"
            for persona in req.context_obj.personas:
                new_context += f"{persona.name} (guid: {persona.persona_guid}) \n"

            persona_guid = unstructure(req.context_obj.participants[0])
            this_persona = [
                p for p in req.context_obj.personas if p.persona_guid == persona_guid
            ][0]
            new_context += "TASK:\n"
            new_context += f"You are the character {this_persona.name} (guid: {this_persona.persona_guid}).\n"
            new_context += f"Your backstory: {this_persona.backstory}\n"

        req.context = new_context
        print("Context:", req.context)
        resp = await super().handle_request(req)
        assert resp.actions is not None, "Actions must not be None."
        print("Actions:", resp.actions.options)
        return resp


class DebugCallback(langchain_core.callbacks.AsyncCallbackHandler):

    def __init__(self):
        self.response: str = ""
        self.last_token: str = ""

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ):
        # Reset the response and last good response.
        self.response = ""
        """Run on LLM start."""
        print("\n-> Generating with Ollama..", flush=True)

    def on_llm_end(self, response: LLMResult, **kwargs):
        """Run on LLM end."""
        print(
            "\n-> Done!  How bad was it? See WARNING above.",
            flush=True,
        )

    def on_llm_new_token(self, token: str, **kwargs):
        """Run on new LLM token. Only available when streaming is enabled."""
        self.response += token
        # The json mode of ollama (mistra:instruct at least) sends a lot of newlines at the end of the response.
        # We don't want to print them.
        if token == "\n" and self.last_token == "\n":
            return
        print(token, end="", flush=True)
        self.last_token = token


class UseOllamaDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Use an Ollama Model",
            summary="Use Ollama to generate actions and conversations. You must have the Ollama server running.",
            category=CATEGORY,
            function=self.use_llama2_model,
        )
        self.callback = DebugCallback()

    def use_llama2_model(self, bridge: RuntimeBridge):
        """Server for SAGA."""

        print(
            "\nWARNING: You must have the Ollama server running with the correct model to use this demo! "
            "Also, the default model works decently, but it's not as good as even GPT-3.5-tubo. It works very intermittently. "
            "If you are interested in co-working on a fine-tuned Ollama model, please reach out to us on Discord."
        )

        default_model = "mistral:instruct"
        model = input(
            f"\nEnter the running ollama model name (default: {default_model}): "
        )

        ask_debug = input("\nEnable generation debug mode? (Y/n): ")
        gen_debug = not ask_debug.lower() == "n"

        print("\nWhich endpoints do you want to override?:")
        print("0. Both [Default]")
        print("1. Action Generation")
        print("2. Conversation Generation")
        ask_endpoints = input()

        model = model if model else default_model
        print(f"\nUsing model: {model}")

        from langchain_community.llms import Ollama

        ollama = Ollama(
            model=model,
            callbacks=[DebugCallback()] if gen_debug else None,
            format="json",
        )

        # Create the override endpoints (we may not need both).
        override_conversations = Route(
            IncomingRoutes.generate_conversations.value,
            saga_server.ConversationEndpoint(
                fable_saga.conversations.ConversationAgent(ollama)
            ),
        )
        override_actions = Route(
            IncomingRoutes.generate_actions.value,
            OllamaActionsEndpoint(fable_saga.actions.ActionsAgent(ollama)),
        )

        # Set the endpoints to use the ollama model.
        if ask_endpoints == "1":
            bridge.router.add_route(override_actions)
        elif ask_endpoints == "2":
            bridge.router.add_route(override_conversations)
        else:
            bridge.router.add_route(override_actions)
            bridge.router.add_route(override_conversations)
