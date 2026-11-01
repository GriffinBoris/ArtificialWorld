import json
from copy import deepcopy

from pydantic_ai.messages import (
	ModelMessagesTypeAdapter,
	ModelRequest,
	ModelResponse,
	RetryPromptPart,
	ToolCallPart,
	ToolReturnPart,
	UserPromptPart,
)

MAX_RECENT_TURNS = 6
MAX_HISTORY_CHARACTERS = 60000
MAX_SUMMARY_ENTRIES = 24
MAX_SUMMARY_CHARACTERS = 6000


def bounded_summary(entries):
	entries = entries[-MAX_SUMMARY_ENTRIES:]

	while sum(len(entry) for entry in entries) > MAX_SUMMARY_CHARACTERS:
		entries.pop(0)

	return entries


def bootstrap_conversation(decisions):
	entries = []
	last_plan = ''

	for decision in reversed(decisions):
		for heard in decision.observation.get('messages', []):
			entries.append(f'At tick {heard["tick"]}, heard {heard["speaker_id"]}: {heard["text"][:350]}')

		for entry in decision.trace:
			entries.append(f'At tick {decision.tick}, {entry["tool"]}: {json.dumps(entry["arguments"])[:350]}')

			if 'result' in entry:
				entries.append(f'{entry["tool"]} returned: {json.dumps(entry["result"])[:350]}')

			if entry['tool'] == 'share_plan' and 'error' not in entry:
				last_plan = entry['arguments']['text']

	return {'turns': [], 'summary': bounded_summary(entries), 'last_shared_plan': last_plan}


def public_messages(messages):
	public = []

	for message in messages:
		parts = []

		if isinstance(message, ModelResponse):
			parts = [
				ToolCallPart(part.tool_name, part.args, tool_call_id=part.tool_call_id)
				for part in message.parts
				if isinstance(part, ToolCallPart)
			]
		else:
			for part in message.parts:
				if isinstance(part, UserPromptPart) and isinstance(part.content, str):
					parts.append(UserPromptPart(part.content))
				elif isinstance(part, ToolReturnPart):
					parts.append(ToolReturnPart(part.tool_name, part.content, tool_call_id=part.tool_call_id))
				elif isinstance(part, RetryPromptPart):
					parts.append(
						RetryPromptPart(part.content, tool_name=part.tool_name, tool_call_id=part.tool_call_id)
					)

		if parts:
			public.append(
				ModelResponse(parts=parts) if isinstance(message, ModelResponse) else ModelRequest(parts=parts)
			)

	return ModelMessagesTypeAdapter.dump_python(public, mode='json')


def conversation_history(conversation):
	messages = ModelMessagesTypeAdapter.validate_python(
		[message for turn in conversation.get('turns', []) for message in turn]
	)
	known_calls = set()
	complete = []

	for message in messages:
		if isinstance(message, ModelResponse):
			known_calls.update(part.tool_call_id for part in message.parts if isinstance(part, ToolCallPart))
		else:
			message.parts = [
				part
				for part in message.parts
				if not isinstance(part, (ToolReturnPart, RetryPromptPart))
				or not part.tool_call_id
				or part.tool_call_id in known_calls
			]

		if message.parts:
			complete.append(message)

	return complete


def summarize_turn(messages):
	entries = []

	for message in ModelMessagesTypeAdapter.validate_python(messages):
		for part in message.parts:
			if isinstance(part, ToolCallPart):
				entries.append(f'{part.tool_name}: {json.dumps(part.args, ensure_ascii=False)[:350]}')
			elif isinstance(part, ToolReturnPart):
				entries.append(f'{part.tool_name} returned: {json.dumps(part.content, ensure_ascii=False)[:350]}')
			elif isinstance(part, UserPromptPart) and isinstance(part.content, str):
				try:
					observation = json.loads(part.content)
				except json.JSONDecodeError:
					continue

				for heard in observation.get('messages', []):
					entries.append(f'At tick {heard["tick"]}, heard {heard["speaker_id"]}: {heard["text"][:350]}')

	return entries


def retain_conversation(previous, messages, trace, decision_id):
	conversation = deepcopy(previous)
	turns = conversation.setdefault('turns', [])
	summary = conversation.setdefault('summary', [])
	turns.append(messages)
	conversation['pending_decision_id'] = str(decision_id)

	for entry in trace:
		if entry['tool'] == 'share_plan' and 'error' not in entry:
			conversation['last_shared_plan'] = entry['arguments']['text']

	while len(turns) > 1 and (len(turns) > MAX_RECENT_TURNS or len(json.dumps(turns)) > MAX_HISTORY_CHARACTERS):
		summary.extend(summarize_turn(turns.pop(0)))

	if len(json.dumps(turns)) > MAX_HISTORY_CHARACTERS:
		summary.extend(summarize_turn(turns.pop()))
		pending = next(entry for entry in trace if 'tool_call_id' in entry)
		turns.append(
			public_messages(
				[
					ModelRequest(parts=[UserPromptPart('Earlier world action:')]),
					ModelResponse(
						parts=[
							ToolCallPart(pending['tool'], pending['arguments'], tool_call_id=pending['tool_call_id'])
						]
					),
				]
			)
		)

	conversation['summary'] = bounded_summary(summary)

	return conversation
