import json
import math
import re

MAX_PROGRAM_BYTES = 16000
MAX_STORAGE_BYTES = 4096
MAX_PROGRAM_DEPTH = 16
MAX_INSTRUCTIONS = 256
MAX_MESSAGES = 10
MAX_KEY_LENGTH = 64
BINARY_ARGUMENT_COUNT = 2
MAX_MESSAGE_LENGTH = 1000
MAX_NUMBER = 1e12


class ProgramError(ValueError):
	pass


def validate_program(source):
	if len(source.encode()) > MAX_PROGRAM_BYTES:
		raise ProgramError('Program exceeds the source size limit.')

	try:
		program = json.loads(source)
	except (ValueError, RecursionError) as error:
		raise ProgramError('Programs must be bounded JSON instructions.') from error

	if not isinstance(program, list):
		raise ProgramError('A program must be a list of instructions.')

	def visit(value, depth=0):
		if depth > MAX_PROGRAM_DEPTH:
			raise ProgramError('Program nesting is too deep.')

		if isinstance(value, dict):
			for key, child in value.items():
				if not re.fullmatch(r'[a-z][a-z_]*', key):
					raise ProgramError('Instruction keys must be plain identifiers.')

				visit(child, depth + 1)
		elif isinstance(value, list):
			for child in value:
				visit(child, depth + 1)
		elif isinstance(value, (float, int)):
			if abs(value) > MAX_NUMBER or not math.isfinite(value):
				raise ProgramError('A numeric literal is outside the supported range.')
		elif value is not None and not isinstance(value, (str, bool)):
			raise ProgramError('Unsupported program value.')

	visit(program)

	return program


class SimulationProgramVM:
	def __init__(self, records, sensors, fuel=MAX_INSTRUCTIONS):
		self.records = json.loads(json.dumps(records))
		self.sensors = sensors
		self.fuel = min(fuel, MAX_INSTRUCTIONS)
		self.used = 0
		self.messages = []

	def _spend(self):
		self.used += 1

		if self.used > self.fuel:
			raise ProgramError('Program exhausted its instruction budget.')

	def expression(self, value):
		self._spend()

		if isinstance(value, (str, bool, int, float)) or value is None:
			return value

		if not isinstance(value, dict):
			raise ProgramError('Expressions must be literals or supported operations.')

		if set(value) == {'record'}:
			return self.records.get(self._key(self.expression(value['record'])), 0)

		if set(value) == {'sensor'}:
			if value['sensor'] not in self.sensors:
				raise ProgramError('That sensor is not available to this device.')

			return self.sensors[value['sensor']]

		if set(value) != {'op', 'args'} or not isinstance(value['args'], list):
			raise ProgramError('Unsupported expression.')

		args = [self.expression(argument) for argument in value['args']]
		op = value['op']

		if op == 'concat':
			result = ''.join(str(argument) for argument in args)
		elif op == 'length' and len(args) == 1 and isinstance(args[0], (str, list, dict)):
			result = len(args[0])
		elif op == 'field' and len(args) == BINARY_ARGUMENT_COUNT and isinstance(args[0], dict):
			result = args[0].get(self._key(args[1]))
		elif op == 'item' and len(args) == BINARY_ARGUMENT_COUNT and isinstance(args[0], list) and type(args[1]) is int:
			result = args[0][args[1]] if 0 <= args[1] < len(args[0]) else None
		elif op in ('eq', 'lt', 'gt') and len(args) == BINARY_ARGUMENT_COUNT:
			if op == 'eq':
				return args[0] == args[1]

			self._numbers(args)

			return args[0] < args[1] if op == 'lt' else args[0] > args[1]
		elif op in ('add', 'sub', 'mul', 'div') and len(args) == BINARY_ARGUMENT_COUNT:
			self._numbers(args)

			if op == 'add':
				result = args[0] + args[1]
			elif op == 'sub':
				result = args[0] - args[1]
			elif op == 'mul':
				result = args[0] * args[1]
			else:
				if args[1] == 0:
					raise ProgramError('Division by zero.')

				result = args[0] / args[1]
		else:
			raise ProgramError('This operation is not part of the simulation language.')

		if isinstance(result, (float, int)) and (abs(result) > MAX_NUMBER or not math.isfinite(result)):
			raise ProgramError('Arithmetic exceeded the numeric limit.')

		if isinstance(result, str) and len(result.encode()) > MAX_STORAGE_BYTES:
			raise ProgramError('String exceeded the storage limit.')

		return result

	def _numbers(self, values):
		if not all(type(value) in (int, float) for value in values):
			raise ProgramError('This operation requires numeric arguments.')

	def _key(self, value):
		if not isinstance(value, str) or not value or len(value) > MAX_KEY_LENGTH:
			raise ProgramError('Record keys must be short nonempty strings.')

		return value

	def run(self, instructions):
		if not isinstance(instructions, list):
			raise ProgramError('Expected a list of instructions.')

		for instruction in instructions:
			self._spend()

			if not isinstance(instruction, dict):
				raise ProgramError('Invalid instruction.')

			keys = set(instruction)

			if keys == {'put', 'value'}:
				key = self._key(self.expression(instruction['put']))
				self.records[key] = self.expression(instruction['value'])

				if len(json.dumps(self.records).encode()) > MAX_STORAGE_BYTES:
					raise ProgramError('Device storage is full.')
			elif keys == {'send'}:
				message = self.expression(instruction['send'])

				if (
					not isinstance(message, str)
					or len(message) > MAX_MESSAGE_LENGTH
					or len(self.messages) >= MAX_MESSAGES
				):
					raise ProgramError('Device message limit exceeded.')

				self.messages.append(message)
			elif keys == {'if', 'then', 'else'}:
				self.run(instruction['then'] if self.expression(instruction['if']) else instruction['else'])
			elif keys == {'repeat', 'do'}:
				count = instruction['repeat']

				if type(count) is not int or not 0 <= count <= MAX_INSTRUCTIONS:
					raise ProgramError('Loop count exceeds the instruction budget.')

				for _ in range(count):
					self.run(instruction['do'])
			else:
				raise ProgramError('Instruction is not part of the simulation language.')

		return {'records': self.records, 'messages': self.messages, 'instructions_used': self.used}
