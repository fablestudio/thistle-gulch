import cattrs
import fable_saga.actions
from fable_saga import server as saga_server
from langchain.prompts import PromptTemplate

from thistle_gulch import logger
from thistle_gulch.bridge import TGActionsEndpoint, RuntimeBridge, TGActionsRequest
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

    def print_actions_and_pick_first(self, bridge: RuntimeBridge):
        """Override the actions endpoint to print the action options to the console and then only pass back the first action option."""

        class PrintActionsAndPickFirst(TGActionsEndpoint):
            """Override the default ActionsEndpoint."""

            async def handle_request(
                self, req: TGActionsRequest
            ) -> saga_server.ActionsResponse:

                resp = await super().handle_request(req)
                assert resp.actions is not None, "Actions must not be None."

                # Print the action options to the console.
                logger.info(resp.actions.options)
                # Override action options by first printing the action options to the console. Then, only pass back the first action option.
                if len(resp.actions.options) > 1:
                    resp.actions.options = [resp.actions.options[0]]
                    resp.actions.scores = [resp.actions.scores[0]]

                return resp

        # Set the actions endpoint to the selected demo.
        bridge.config.actions_endpoint = PrintActionsAndPickFirst(
            saga_server.ActionsAgent()
        )


class SkipSagaAlwaysDoTheDefaultActionDemo(Demo):

    def __init__(self):
        super().__init__(
            name="Skip Saga Always Do The Default Action",
            description="Override action options by always picking the default action.",
            category=CATEGORY,
            function=self.skip_saga_always_do_the_default_action,
        )

    def skip_saga_always_do_the_default_action(self, bridge: RuntimeBridge):
        """Override the actions endpoint to always pick the default action without even using the Agent."""

        class SkipSagaAlwaysDoTheDefaultAction(TGActionsEndpoint):
            """Override the default ActionsEndpoint."""

            async def handle_request(
                self, req: TGActionsRequest
            ) -> saga_server.ActionsResponse:
                # Overrides the default handle_request.

                # Note: We are NOT using the agent to generate actions. Instead, we are always picking the default action manually.

                default_action = fable_saga.actions.Action(
                    skill="default_action",
                    parameters={
                        "goal": "The Override Action Options demo has chosen the default action."
                    },
                )
                actions = fable_saga.actions.GeneratedActions(
                    options=[default_action],
                    scores=[1.0],
                )

                response = saga_server.ActionsResponse(
                    actions=actions, reference=req.reference
                )
                if actions.error is not None:
                    response.error = f"Generation Error: {actions.error}"
                return response

        # Set the actions endpoint to the selected demo.
        bridge.config.actions_endpoint = SkipSagaAlwaysDoTheDefaultAction(
            fable_saga.actions.ActionsAgent()
        )


class ReplaceContextWithYamlDumpDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Replace Context with Yaml Dump",
            description="Replace the context in the request with a YAML dump of the context object.",
            category=CATEGORY,
            function=self.replace_context_with_yaml_dump,
        )

    def replace_context_with_yaml_dump(self, bridge: RuntimeBridge):
        """Override the actions endpoint to replace the context in the request with a YAML dump of the context object."""

        class ReplaceContextWithYamlDump(TGActionsEndpoint):
            """Override the default ActionsEndpoint."""

            def __init__(self, agent: saga_server.ActionsAgent):
                super().__init__(agent)
                # Set the prompt template to a custom template that includes the context as a YAML dump.
                self.agent.prompt_template = PromptTemplate.from_template(
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

            async def handle_request(
                self, req: TGActionsRequest
            ) -> saga_server.ActionsResponse:
                # Overrides the default handle_request.

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

        # Set the actions endpoint to the selected demo.
        bridge.config.actions_endpoint = ReplaceContextWithYamlDump(
            fable_saga.actions.ActionsAgent()
        )
