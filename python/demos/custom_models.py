from typing import Optional

import fable_saga.actions
import fable_saga.server
import langchain_core.callbacks
from langchain.chains import LLMChain

from thistle_gulch.bridge import TGActionsRequest, RuntimeBridge, TGActionsEndpoint
from thistle_gulch import logger
from . import Demo

CATEGORY = "Custom Models"

debug = False


class DebugCallback(langchain_core.callbacks.AsyncCallbackHandler):
    def on_llm_new_token(self, token: str, **kwargs):
        """Run on new LLM token. Only available when streaming is enabled."""
        print(token, end="", flush=True)


class UseOllamaDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Use an Ollama Model",
            description="Use Ollama to generate actions and conversations. You must have the Ollama server running.",
            category=CATEGORY,
            function=self.use_llama2_model,
        )

    def use_llama2_model(self, bridge: RuntimeBridge):
        """Server for SAGA."""

        default_model = "codellama:13b-instruct"
        model = input(
            "Enter the running ollama model name (default: codellama:13b-instruct): "
        )

        ask_debug = input("Enable generation debug mode? (y/N): ")
        if ask_debug.lower() == "y":
            debug = True

        model = model if model else default_model
        print(f"Using model: {model}")

        class UseLlama2Model(TGActionsEndpoint):
            """Server for SAGA."""

            def __init__(self, agent: fable_saga.actions.ActionsAgent):
                super().__init__(agent)
                from langchain_community.llms import Ollama

                self.llm = Ollama(
                    model=model, callbacks=[DebugCallback()] if debug else None
                )

                self.agent = fable_saga.actions.ActionsAgent(self.llm)

                def generate_chain(_: Optional[str]) -> LLMChain:
                    return LLMChain(llm=self.llm, prompt=self.agent.prompt_template)

                self.agent.__setattr__("generate_chain", generate_chain)

            async def generate_actions(
                self, req: TGActionsRequest
            ) -> fable_saga.server.ActionsResponse:
                # Generate actions
                try:
                    assert isinstance(
                        req, TGActionsRequest
                    ), f"Invalid request type: {type(req)}"
                    actions = await self.agent.generate_actions(
                        req.context, req.skills, req.retries, req.verbose, req.model
                    )

                    logger.info(actions.options)
                    response = fable_saga.server.ActionsResponse(
                        actions=actions, reference=req.reference, error=None
                    )
                    if actions.error is not None:
                        response.error = f"Generation Error: {actions.error}"
                    return response
                except Exception as e:
                    logger.exception(str(e))
                    return fable_saga.server.ActionsResponse(
                        actions=None, error=str(e), reference=req.reference
                    )

        # Set the actions endpoint to the selected demo.
        bridge.config.actions_endpoint = UseLlama2Model(
            fable_saga.actions.ActionsAgent()
        )
