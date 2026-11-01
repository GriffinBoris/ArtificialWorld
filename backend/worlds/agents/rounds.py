import asyncio

from worlds.agents.contracts import DecisionDraft, DecisionFailed, DecisionOutcome, DriverReply


async def collect_decisions(contexts, driver, slots):
	semaphore = asyncio.Semaphore(slots)

	async def collect(context):
		async with semaphore:
			try:
				reply = await asyncio.wait_for(driver.decide(context), timeout=150)
				draft = DecisionDraft.model_validate(reply.draft)

				return DecisionOutcome(
					context=context, reply=DriverReply(draft=draft, trace=reply.trace, messages=reply.messages)
				)
			except DecisionFailed as error:
				message = f'Agent decision failed ({error.error_type}).'

				if error.error_type == 'ModelAuthenticationError':
					message = 'Model provider rejected authentication. Check API key expiry and access to this model.'

				return DecisionOutcome(context=context, error=message, trace=error.trace)
			except Exception as error:
				return DecisionOutcome(context=context, error=f'Agent decision failed ({type(error).__name__}).')

	return await asyncio.gather(*(collect(context) for context in contexts))
