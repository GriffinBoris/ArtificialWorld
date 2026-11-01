import json

import pytest
from worlds.simulation.programs import ProgramError, SimulationProgramVM, validate_program


def test_program_can_keep_records_and_broadcast_without_host_io():
	source = json.dumps(
		[
			{'put': 'count', 'value': {'op': 'add', 'args': [{'record': 'count'}, 1]}},
			{'send': {'op': 'concat', 'args': ['Visitors: ', {'record': 'count'}]}},
		]
	)
	result = SimulationProgramVM({'count': 4}, {'tick': 0}).run(validate_program(source))
	assert result['records'] == {'count': 5}
	assert result['messages'] == ['Visitors: 5']


@pytest.mark.parametrize(
	'instruction',
	[
		{'import': 'os'},
		{'open': '/etc/passwd'},
		{'http': 'http://localhost:8000/admin/'},
		{'op': 'eval', 'args': ['1+1']},
		{'send': {'op': '__import__', 'args': ['os']}},
	],
)
def test_program_rejects_host_operations(instruction):
	with pytest.raises(ProgramError):
		SimulationProgramVM({}, {}).run(validate_program(json.dumps([instruction])))


def test_program_instruction_limit_stops_nested_loops():
	source = json.dumps([{'repeat': 200, 'do': [{'repeat': 200, 'do': [{'put': 'counter', 'value': 1}]}]}])
	with pytest.raises(ProgramError, match='budget'):
		SimulationProgramVM({}, {}).run(validate_program(source))


def test_program_storage_limit_cannot_modify_callers_records():
	records = {'original': 1}
	source = json.dumps([{'put': 'large', 'value': 'x' * 5000}])
	with pytest.raises(ProgramError, match='storage'):
		SimulationProgramVM(records, {}).run(validate_program(source))
	assert records == {'original': 1}


def test_program_cannot_read_ungranted_sensor():
	with pytest.raises(ProgramError, match='sensor'):
		SimulationProgramVM({}, {'tick': 1}).run([{'put': 'secret', 'value': {'sensor': 'server_environment'}}])
