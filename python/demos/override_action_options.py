from typing import Optional

import cattrs
import fable_saga
import thistle_gulch.bridge
from fable_saga import server as saga_server
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from thistle_gulch import logger
from . import Demo

CATEGORY = "Action Generation"


class PrintActionsAndPickFirstDemo(Demo):

    def __init__(self):
        super().__init__(
            name="Print Actions and Pick First",
            description="Print the action options to the console and then only pass back the first action option.",
            category=CATEGORY,
            function=self.print_actions_and_pick_first,
        )

    def print_actions_and_pick_first(self, bridge: thistle_gulch.bridge.RuntimeBridge):
        """Server for SAGA."""

        class PrintActionsAndPickFirst(saga_server.SagaServer):
            """Server for SAGA."""

            def __init__(self, llm: saga_server.BaseLanguageModel = None):
                super().__init__()
                self.agent = fable_saga.SagaAgent(llm)

            async def generate_actions(
                self, req: saga_server.ActionsRequest
            ) -> saga_server.ActionsResponse:
                # Generate actions
                try:
                    assert isinstance(
                        req, thistle_gulch.bridge.TGActionsRequest
                    ), f"Invalid request type: {type(req)}"
                    actions = await self.agent.generate_actions(
                        req.context, req.skills, req.retries, req.verbose, req.model
                    )
                    logger.info(actions.options)
                    # Override action options by first printing the action options to the console. Then, only pass back the first action option.
                    if len(actions.options) > 1:
                        actions.options = [actions.options[0]]
                        actions.scores = [actions.scores[0]]

                    response = saga_server.ActionsResponse(
                        actions=actions, reference=req.reference, error=None
                    )
                    if actions.error is not None:
                        response.error = f"Generation Error: {actions.error}"
                    return response
                except Exception as e:
                    logger.error(str(e))
                    return saga_server.ActionsResponse(
                        actions=None, error=str(e), reference=req.reference
                    )

        # Set the actions endpoint to the selected demo.
        bridge.config.actions_endpoint = PrintActionsAndPickFirst()


class SkipSagaAlwaysDoTheDefaultActionDemo(Demo):

    def __init__(self):
        super().__init__(
            name="Skip Saga Always Do The Default Action",
            description="Override action options by always picking the default action.",
            category=CATEGORY,
            function=self.skip_saga_always_do_the_default_action,
        )

    def skip_saga_always_do_the_default_action(
        self, bridge: thistle_gulch.bridge.RuntimeBridge
    ):
        """Server for SAGA."""

        class SkipSagaAlwaysDoTheDefaultAction(saga_server.SagaServer):
            """Server for SAGA."""

            def __init__(self, llm: saga_server.BaseLanguageModel = None):
                super().__init__()
                self.agent = fable_saga.SagaAgent(llm)

            async def generate_actions(
                self, req: saga_server.ActionsRequest
            ) -> saga_server.ActionsResponse:
                # Generate actions
                try:
                    assert isinstance(
                        req, thistle_gulch.bridge.TGActionsRequest
                    ), f"Invalid request type: {type(req)}"

                    # Override action options by always picking the default action.
                    default_action = fable_saga.Action(
                        skill="default_action",
                        parameters={
                            "goal": "The Override Action Options demo has chosen the default action."
                        },
                    )
                    actions = fable_saga.GeneratedActions(
                        options=[default_action],
                        scores=[1.0],
                    )

                    response = saga_server.ActionsResponse(
                        actions=actions, reference=req.reference
                    )
                    if actions.error is not None:
                        response.error = f"Generation Error: {actions.error}"
                    return response
                except Exception as e:
                    logger.error(str(e))
                    return saga_server.ActionsResponse(
                        actions=None, error=str(e), reference=req.reference
                    )

        # Set the actions endpoint to the selected demo.
        bridge.config.actions_endpoint = SkipSagaAlwaysDoTheDefaultAction()


class ReplaceContextWithYamlDumpDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Replace Context with Yaml Dump",
            description="Replace the context in the request with a YAML dump of the context object.",
            category=CATEGORY,
            function=self.replace_context_with_yaml_dump,
        )

    def replace_context_with_yaml_dump(
        self, bridge: thistle_gulch.bridge.RuntimeBridge
    ):
        """Server for SAGA."""

        class ReplaceContextWithYamlDump(saga_server.SagaServer):
            """Server for SAGA."""

            def __init__(self, llm: saga_server.BaseLanguageModel = None):
                super().__init__()
                self.agent = fable_saga.SagaAgent(llm)
                self.agent.generate_actions_prompt = PromptTemplate.from_template(
                    """
        {context}
        
        # Task
        Generate a list of different action options that your character should take next using the following skills:
        ```json
        {skills}
        ```
        
        # Output
        Generate a list of different action options that your character should take. Then score each option. Only generate valid JSON.
        Use the following JSON format to specify the parameters:
        ```json
        {{"options": [
            {{"skill": <choice of skill>, "parameters": {{<skill parameters as json>}}}}
        ],"scores": [<list[float]: scores for each action in the order listed. -1.0 is terrible, 0 is neutral, and 1.0 the best action ever.>]
        ]}}
        ```
        """
                )

                self.context_template = """
        You are a Storyteller AI tasked with directing a TV show set in a western town in the late 1800s. For every character 
        in the town you will generate actions from the list of skills, so not all characters should be part of the plot and can 
        instead perform their default skill. Always generate exactly one option using the "default_action" skill if a 
        "default action" is provided in the character's context information below. Failure to do so will result in a penalty.
        The skills chosen should drive the plot toward an interesting and satisfying conclusion over the allotted time period
        without ending prematurely. Heavily weight any recent conversations provided (especially the latest one) to drive the plot
        and the chosen skill options.""".replace(
                    "\n", " "
                )
                self.context_template += "\n\n# Context\n ```Yaml\n{context_dump}\n```"

            async def generate_actions(
                self, req: saga_server.ActionsRequest
            ) -> saga_server.ActionsResponse:
                # Generate actions
                try:
                    assert isinstance(
                        req, thistle_gulch.bridge.TGActionsRequest
                    ), f"Invalid request type: {type(req)}"

                    # Get a dictionary representation of the context object so that we can turn it into a YAML string.
                    ctx_obj = cattrs.unstructure(req.context_obj)

                    # Use the YAML library to dump the context object to a string and then replace the context in the request.
                    import yaml

                    yaml_dump = yaml.dump(ctx_obj)
                    new_context = self.context_template.format(context_dump=yaml_dump)

                    actions = await self.agent.generate_actions(
                        new_context, req.skills, req.retries, req.verbose, req.model
                    )
                    response = saga_server.ActionsResponse(
                        actions=actions, reference=req.reference
                    )
                    if actions.error is not None:
                        response.error = f"Generation Error: {actions.error}"
                    return response
                except Exception as e:
                    logger.exception(str(e))
                    return saga_server.ActionsResponse(
                        actions=None, error=str(e), reference=req.reference
                    )

        # Set the actions endpoint to the selected demo.
        bridge.config.actions_endpoint = ReplaceContextWithYamlDump()


class UseLlama2ModelDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Use Llama2 Model",
            description="Use the Llama2 model to generate actions.",
            category=CATEGORY,
            function=self.use_llama2_model,
        )

    def use_llama2_model(self, bridge: thistle_gulch.bridge.RuntimeBridge):
        """Server for SAGA."""

        default_model = "codellama:13b-instruct"
        model = input(
            "Enter the running ollama model name (default: codellama:13b-instruct): "
        )

        ask_debug = input("Enable generation debug mode? (y/N): ")

        model = model if model else default_model
        print(f"Using model: {model}")

        class UseLlama2Model(saga_server.SagaServer):
            """Server for SAGA."""

            def __init__(self):
                super().__init__()
                from thistle_gulch.llms import AsyncOllama

                self.llm = AsyncOllama(model=model)
                if ask_debug.lower() == "y":
                    self.llm.debug_generation = True

                self.agent = fable_saga.SagaAgent(self.llm)

                def generate_chain(_: Optional[str]) -> LLMChain:
                    return LLMChain(
                        llm=self.llm, prompt=self.agent.generate_actions_prompt
                    )

                self.agent.__setattr__("actions_endpoint", generate_chain)

            async def generate_actions(
                self, req: saga_server.ActionsRequest
            ) -> saga_server.ActionsResponse:
                # Generate actions
                try:
                    assert isinstance(
                        req, thistle_gulch.bridge.TGActionsRequest
                    ), f"Invalid request type: {type(req)}"
                    actions = await self.agent.generate_actions(
                        req.context, req.skills, req.retries, req.verbose, req.model
                    )

                    logger.info(actions.options)
                    response = saga_server.ActionsResponse(
                        actions=actions, reference=req.reference, error=None
                    )
                    if actions.error is not None:
                        response.error = f"Generation Error: {actions.error}"
                    return response
                except Exception as e:
                    logger.exception(str(e))
                    return saga_server.ActionsResponse(
                        actions=None, error=str(e), reference=req.reference
                    )

        # Set the actions endpoint to the selected demo.
        bridge.config.actions_endpoint = UseLlama2Model()
