import json
import logging

import cattrs
import fable_saga
from fable_saga import server as saga_server

logger = logging.getLogger(__name__)

class PrintActionsAndPickFirst:
    """ Server for SAGA. """
    def __init__(self, llm: saga_server.BaseLanguageModel = None):
        super().__init__()
        self.agent = fable_saga.SagaAgent(llm)

    async def generate_actions(self, req: saga_server.ActionsRequest) -> saga_server.ActionsResponse:
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
            assert isinstance(req, saga_server.ActionsRequest), f"Invalid request type: {type(req)}"

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


