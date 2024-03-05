import json
import logging
import textwrap

import cattrs
import fable_saga
from fable_saga import server as saga_server

import thistle_gulch.bridge

logger = logging.getLogger(__name__)

class PrintActionsAndPickFirst:
    """ Server for SAGA. """
    def __init__(self, llm: saga_server.BaseLanguageModel = None):
        super().__init__()
        self.agent = fable_saga.SagaAgent(llm)

    async def generate_actions(self, req: thistle_gulch.bridge.TGActionsRequest) -> saga_server.ActionsResponse:
        # Generate actions
        try:
            assert isinstance(req, saga_server.ActionsRequest), f"Invalid request type: {type(req)}"
            actions = await self.agent.generate_actions(req.context, req.skills, req.retries, req.verbose, req.model)

            # Override action options by first printing the action options to the console. Then, only pass back the first action option.
            print(json.dumps(cattrs.unstructure(actions.options), indent=2))
            if len(actions.options) > 1:
                actions.options = [actions.options[0]]
                actions.scores = [actions.scores[0]]

            response = saga_server.ActionsResponse(actions=actions, reference=req.reference)
            if actions.error is not None:
                response.error = f"Generation Error: {actions.error}"
            return response
        except Exception as e:
            logger.error(str(e))
            return saga_server.ActionsResponse(actions=None, error=str(e), reference=req.reference)


class SkipSagaAlwaysDoTheDefaultAction:
    """ Server for SAGA. """
    def __init__(self, llm: saga_server.BaseLanguageModel = None):
        super().__init__()
        self.agent = fable_saga.SagaAgent(llm)

    async def generate_actions(self, req: saga_server.ActionsRequest) -> saga_server.ActionsResponse:
        # Generate actions
        try:
            assert isinstance(req, thistle_gulch.bridge.TGActionsRequest), f"Invalid request type: {type(req)}"

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
                error=None
            )

            response = saga_server.ActionsResponse(actions=actions, reference=req.reference)
            if actions.error is not None:
                response.error = f"Generation Error: {actions.error}"
            return response
        except Exception as e:
            logger.error(str(e))
            return saga_server.ActionsResponse(actions=None, error=str(e), reference=req.reference)


class ReplaceContextWithYamlDump:
    """ Server for SAGA. """
    def __init__(self, llm: saga_server.BaseLanguageModel = None):
        super().__init__()
        self.agent = fable_saga.SagaAgent(llm)
        self.context_template = "[DETAILS]\n"
        self.context_template += """
You are a Storyteller AI tasked with directing a TV show set in a western town in the late 1800s. For every character 
in the town you will generate actions from the list of skills, so not all characters should be part of the plot and can 
instead perform their default skill. Always generate exactly one option using the ""default_action"" skill if a 
""default action"" is provided in the character's context information below. Failure to do so will result in a penalty.
The skills chosen should drive the plot toward an interesting and satisfying conclusion over the allotted time period
without ending prematurely. Heavily weight any recent conversations provided (especially the latest one) to drive the plot
and the chosen skill options.""".replace("\n", " ")
        self.context_template += "\n\n[CONTEXT]\n{context_dump}"

    async def generate_actions(self, req: thistle_gulch.bridge.TGActionsRequest) -> saga_server.ActionsResponse:
        # Generate actions
        try:
            assert isinstance(req, saga_server.ActionsRequest), f"Invalid request type: {type(req)}"

            # Get a dictionary representation of the context object so we can turn it into a YAML string.
            ctx_obj = cattrs.unstructure(req.context_obj)

            # Use the YAML library to dump the context object to a string and then replace the context in the request.
            import yaml
            yaml_dump = yaml.dump(ctx_obj)
            new_context = self.context_template.format(context_dump=yaml_dump)

            actions = await self.agent.generate_actions(new_context, req.skills, req.retries, req.verbose, req.model)
            response = saga_server.ActionsResponse(actions=actions, reference=req.reference)
            if actions.error is not None:
                response.error = f"Generation Error: {actions.error}"
            return response
        except Exception as e:
            logger.error(str(e))
            return saga_server.ActionsResponse(actions=None, error=str(e), reference=req.reference)


