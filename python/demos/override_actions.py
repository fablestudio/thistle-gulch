import asyncio.futures
from typing import Optional

import cattrs
import fable_saga.actions
from fable_saga import server as saga_server
from fable_saga.actions import Action
from langchain.prompts import PromptTemplate

from thistle_gulch import logger, IncomingRoutes, Route
from thistle_gulch.bridge import TGActionsEndpoint, RuntimeBridge, TGActionsRequest
from . import Demo, choose_from_list

CATEGORY = "Action Generation"


class PrintActionsAndPickFirstDemo(Demo):

    def __init__(self):
        super().__init__(
            name="Print Actions and Pick First",
            summary="Print the action options to the console and then only pass back the first action option.",
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
        bridge.router.add_route(
            Route(
                IncomingRoutes.generate_actions.value,
                PrintActionsAndPickFirst(fable_saga.actions.ActionsAgent()),
            )
        )


class SkipSagaAlwaysDoTheDefaultActionDemo(Demo):

    def __init__(self):
        super().__init__(
            name="Skip Saga Always Do The Default Action",
            summary="Override action options by always picking the default action.",
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
        bridge.router.add_route(
            Route(
                IncomingRoutes.generate_actions.value,
                SkipSagaAlwaysDoTheDefaultAction(fable_saga.actions.ActionsAgent()),
            )
        )


class ReplaceContextWithYamlDumpDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Replace Context with Yaml Dump",
            summary="Replace the context in the request with a YAML dump of the context object.",
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
        bridge.router.add_route(
            Route(
                IncomingRoutes.generate_actions.value,
                ReplaceContextWithYamlDump(fable_saga.actions.ActionsAgent()),
            )
        )


class OnActionComplete(Demo):
    def __init__(self):
        super().__init__(
            name="Action Complete",
            summary="Manually trigger a custom action for a character when the previous action is done",
            category=CATEGORY,
            function=self.on_action_complete_demo,
        )

    def on_action_complete_demo(self, bridge: RuntimeBridge):
        """
        When the sheriff's current action completes, the simulation is paused and the user is prompted to enter a new
        location for him to go. The simulation is then resumed and a custom action using the 'go_to' skill is returned
        to the Runtime. For a full list of available skills see:
        https://github.com/fablestudio/thistle-gulch?tab=readme-ov-file#skills-and-actions

        API calls:
            pause()
            resume()
            get_character_context()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/override_actions.py
        """

        sheriff_id = "wyatt_cooper"

        location_list = ["sheriff_station_building", "the_saloon", "bank_building"]

        future: asyncio.futures.Future

        async def on_ready(bridge) -> bool:
            await bridge.runtime.api.focus_character(sheriff_id)
            await bridge.runtime.api.follow_character(sheriff_id, 0.8)

            # Set the sheriff's next action to go to the sheriff's station building to start.
            # Once the sheriff arrives at the building, the on_action_complete callback will be triggered.
            action = fable_saga.actions.Action(
                skill="go_to",
                parameters={
                    "destination": "thistle_gulch." + location_list[0],
                    "goal": "Start the sheriff's day at the sheriff's station building",
                },
            )

            await bridge.runtime.api.override_character_action(sheriff_id, action)
            return True

        bridge.on_ready = on_ready

        async def on_action_complete(
            _, persona_id: str, completed_action: str
        ) -> Optional[Action]:

            # Return None so all characters other than the sheriff use the generate-actions endpoint instead
            if persona_id != sheriff_id:
                return None

            print(f"\n{persona_id}'s last action was: '{completed_action}'")

            # Pause the simulation while we wait for user input
            await bridge.runtime.api.pause()
            # wait for the future to complete
            nonlocal future
            future = asyncio.get_event_loop().create_future()

            await bridge.runtime.api.modal(
                "Next GOTO Location",
                f"The sheriff just completed the action: '{completed_action}'."
                + "\n"
                + "Choose the next location for the sheriff to go to.",
                location_list,
            )

            action = await future
            # Resume the simulation
            await bridge.runtime.api.resume()
            return action

        print("Registering custom on_action_complete callback.")
        bridge.on_action_complete = on_action_complete

        async def on_event(_, name: str, data: dict):
            nonlocal future
            # Return a new action for the character to replace the one that just completed
            if name == "modal-response":
                choice_idx = data["choice"]
                choice = location_list[choice_idx]

                future.set_result(
                    fable_saga.actions.Action(
                        skill="go_to",
                        parameters={
                            "destination": "thistle_gulch." + choice,
                            "goal": "Visit the user-chosen location",
                        },
                    )
                )

        bridge.on_event = on_event
