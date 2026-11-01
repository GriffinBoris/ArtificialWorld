import asyncio
import json

from django.conf import settings
from pydantic_ai import Agent, DeferredToolRequests, DeferredToolResults, ModelRetry
from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.usage import UsageLimits
from worlds.agents.contracts import DecisionDraft, DecisionFailed, DriverReply
from worlds.agents.conversation import conversation_history, public_messages
from worlds.agents.providers import create_provider
from worlds.agents.tools import LocalTools
from worlds.simulation.actions import Action

INSTRUCTIONS = """You live in this world. Explore it, follow your curiosity, and keep pursuing whatever matters to you.
Use your memories and observations to continue your life. Act, speak, and remember through tools."""


def require_world_action(output):
	if isinstance(output, str):
		raise ModelRetry('Use a world action tool to act, or wait to let time pass.')

	return output


class PydanticDriver:
	def __init__(self, progress=None):
		self.provider = create_provider()
		self.progress = progress

	async def decide(self, context):
		progress = (lambda trace: self.progress(context, trace)) if self.progress is not None else None
		tools = LocalTools(context, progress=progress)
		model_class = OpenAIChatModel if settings.WORLD_AI_PROVIDER == 'opencode-go' else OpenAIResponsesModel
		model_settings = (
			{'extra_headers': {'User-Agent': 'ArtificialWorld/0.1', 'x-opencode-session': context.actor_id}}
			if settings.WORLD_AI_PROVIDER == 'opencode-go'
			else None
		)
		agent = Agent(
			model_class(context.model_name, provider=self.provider),
			model_settings=model_settings,
			output_type=[str, DeferredToolRequests],
			instructions=INSTRUCTIONS,
			tools=[
				tools.inspect,
				tools.recall,
				tools.remember,
				tools.read_document,
				tools.scratch,
				tools.share_plan,
				tools.walk,
				tools.speak,
				tools.wait,
				tools.rest,
				tools.grasp,
				tools.release,
				tools.place,
				tools.push,
				tools.strike,
				tools.shape,
				tools.connect,
				tools.detach,
				tools.gather,
				tools.fell,
				tools.take_seed,
				tools.plant,
				tools.uproot,
				tools.eat,
				tools.drink,
				tools.care,
				tools.write,
				tools.program,
				tools.consent,
				tools.name_self,
				tools.name_child,
			],
			retries=1,
		)

		agent.output_validator(require_world_action)
		history = conversation_history(context.conversation)
		deferred_results = None

		if previous := context.previous_tool:
			if not history:
				history = [
					ModelRequest(parts=[UserPromptPart('Previous world action:')]),
					ModelResponse(
						parts=[
							ToolCallPart(
								previous['tool'],
								previous['arguments'],
								tool_call_id=previous['tool_call_id'],
							)
						]
					),
				]
			deferred_results = DeferredToolResults(calls={previous['tool_call_id']: previous['result']})

		try:
			result = await agent.run(
				json.dumps(context.observation),
				message_history=history,
				deferred_tool_results=deferred_results,
				usage_limits=UsageLimits(
					request_limit=8, tool_calls_limit=12, input_tokens_limit=64000, output_tokens_limit=8000
				),
				timeout=120,
			)
		except Exception as error:
			raise DecisionFailed(type(error).__name__, tools.trace) from None

		(call,) = result.output.calls
		action = Action.model_validate(result.output.metadata[call.tool_call_id]['action'])
		await asyncio.to_thread(
			tools.record,
			{
				'tool': call.tool_name,
				'arguments': call.args_as_dict(),
				'tool_call_id': call.tool_call_id,
				'status': 'pending',
			},
		)

		return DriverReply(
			draft=DecisionDraft(action=action, memories=tools.memories),
			trace=tools.trace,
			messages=public_messages(result.new_messages()),
		)
