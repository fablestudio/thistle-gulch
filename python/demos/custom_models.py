import os

import fable_saga.actions
import fable_saga.conversations
import fable_saga.server as saga_server

from langchain_core.prompts import PromptTemplate
from cattrs import unstructure

from thistle_gulch.bridge import (
    RuntimeBridge,
    TGActionsEndpoint,
    Route,
    IncomingRoutes,
    TGActionsRequest,
)
from . import Demo, formatted_input, yes_no_validator, DebugCallback

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


class UseOllamaDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Use an Ollama Model",
            summary="Use Ollama to generate actions and conversations. It's a local server that supports running multiple open models.",
            category=CATEGORY,
            function=self.use_ollama_model,
        )
        self.callback = DebugCallback()

    def use_ollama_model(self, bridge: RuntimeBridge):
        """WARNING: You must have the Ollama server running with the correct model to use this demo!

        This demo will override the default actions and conversation generation endpoints to use the Ollama server.
        You will need to have the Ollama server running with the correct model before running this demo. Setup is
        pretty simple, and you can download and install it here:
            https://ollama.com/download

        Once you have it installed, you need to load the model you want to use. The default model is `mistral:instruct`,
        but you can find more models here: https://ollama.com/library. Be careful, some models are very large and may
        take a long time to download and are very slow to run, even with a large GPU.

        To run the default model, use the following command on your command line:
        > ollama load mistral:instruct

        That will take a few minutes to download the right model.

        The default model works decently, but it's not as good as even GPT-3.5-tubo. It works very intermittently.
        If you are interested in co-working on a fine-tuned Ollama model, please reach out to us on Discord.

        Key API calls:
            bridge.router.add_route() # Shows how to override the endpoints using custom LLMs.
            Ollama() # Shows how to use a custom LLM model using LangChain LLMs.
            DebugCallback() # Shows how to use a custom callback to debug the generation process.


        See the LangChain docs and this Demo source code on Github for more information:
            https://python.langchain.com/docs/integrations/llms/ollama/
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/custom_models.py
        """

        default_model = "mistral:instruct"
        model = formatted_input(
            f"\nEnter the running ollama model name (default: {default_model})",
            default=default_model,
        )

        ask_debug = formatted_input(
            "\nEnable generation debug mode? (Y/n)",
        )
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


class UseAnthropic(Demo):
    """Server for SAGA."""

    def __init__(self):
        super().__init__(
            name="Use an Anthropic Model (Claude)",
            summary="Use Anthropic to generate actions and conversations. You must have an Anthropic API Key.",
            category=CATEGORY,
            function=self.override_model_to_use_anthpropic,
        )

    def override_model_to_use_anthpropic(self, bridge: RuntimeBridge):
        """
        This demo will override the default actions and conversation generation endpoints to use the Anthropic server.
        You will need to have an Anthropic API Key to use this demo. You can get an API key by creating an account at
        https://console.anthropic.com/ and following the instructions. Once you have an API key, set it as an
        environment variable using `export ANTHROPIC_API_KEY=your_api_key`. If you don't have the Anthropic library
        installed, you can install it using `poetry install --with anthropic` or the demo will prompt you to install it.

        Key API calls:
            bridge.router.add_route()
            Anthropic() # Shows how to use a custom LLM model using LangChain LLMs.
            DebugCallback() # Shows how to use a custom callback to debug the generation process.

        See the LangChain docs and this Demo source code on Github for more information:
            https://python.langchain.com/docs/integrations/llms/anthropic/
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/custom_models.py
            https://docs.anthropic.com/claude/docs/intro-to-claude
        """

        # Check if the user has Anthropic installed.
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            print(
                "You must install thistle-gulch using `--with anthropic` to use this demo."
            )
            install = formatted_input(
                "Do you want to install it now? (Y/n)",
                validator=yes_no_validator,
                default="y",
            )
            if install:
                os.system("poetry install --with anthropic")
                print("Trying to import ...")
                from langchain_anthropic import ChatAnthropic
            else:
                print("Exiting.")
                exit(1)

        # Check if the user has an API key.
        api_key = os.environ["ANTHROPIC_API_KEY"]
        if not api_key:
            print(
                "You must set the ANTHROPIC_API_KEY environment variable to use this demo."
            )
            print(
                "Create an account at https://console.anthropic.com/ and get an API key."
            )
            print(
                "Then, set the environment variable with `export ANTHROPIC_API_KEY=your_api_key`."
            )
            print(
                "More details here: https://docs.anthropic.com/claude/docs/quickstart-guide#step-3-optional-set-up-your-api-key"
            )
            print("Exiting.")
            return

        # Ask the user to select a model.
        supported_models = [
            "claude-3-haiku-20240307",
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229",
        ]
        print("Available Anthropic Models ($ to $$$)")
        for i, model in enumerate(supported_models):
            print(f"{i}. {model}")

        def model_validator(val):
            val = int(val)
            if val < 0 or val >= len(supported_models):
                raise ValueError(
                    "Invalid input. Please enter a number between 0 and",
                    len(supported_models),
                )
            return val

        model_idx = formatted_input(
            "Enter the number of the model to use",
            validator=model_validator,
            default="0",
        )
        model_name = supported_models[model_idx]
        print(f"\nUsing model: {model_name}")

        if formatted_input(
            "\nEnable generation debug mode? (Y/n)",
            validator=yes_no_validator,
            default="y",
        ):
            llm = ChatAnthropic(
                model_name=model_name, callbacks=[DebugCallback()], streaming=True
            )
        else:
            llm = ChatAnthropic(model_name=model_name, streaming=True)

        # Create the override actions and conversation endpoints.
        actions_agent = fable_saga.actions.ActionsAgent(llm)
        # Add additional guidance to the actions agent, so it only generates valid JSON. Since Claude doesn't have a
        # dedicated JSON response format, we need to add this guidance to the prompt template.
        # This is how Anthropic documents it: https://docs.anthropic.com/claude/docs/control-output-format
        extra_guidance = "\nUse JSON Format. Do not respond with any additional text, ONLY generate valid JSON.\n"

        if isinstance(actions_agent.prompt_template, PromptTemplate):
            actions_agent.prompt_template.template += extra_guidance
        actions_endpoint = TGActionsEndpoint(actions_agent)

        conversation_agent = fable_saga.conversations.ConversationAgent(llm)
        # Add additional guidance to the conversation agent, so it only generates valid JSON.
        if isinstance(conversation_agent.prompt_template, PromptTemplate):
            conversation_agent.prompt_template.template += (
                "\n Generate a full conversation from the context and personas."
                + extra_guidance
            )
        conversations_endpoint = saga_server.ConversationEndpoint(conversation_agent)

        # Set the routes to use the Anthropic model.
        bridge.router.add_route(
            Route(IncomingRoutes.generate_actions.value, actions_endpoint)
        )
        bridge.router.add_route(
            Route(IncomingRoutes.generate_conversations.value, conversations_endpoint)
        )
