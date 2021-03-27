import pytest

from psub import Psub


@pytest.fixture()
def p():
    return Psub(name="test_job",
                l_arch='intel*',
                l_mem='1G',
                l_time='0:10:00',
                l_highp=True)


@pytest.fixture()
def expected_commands():
    return ['echo arg1 -k argA -q argX', 'echo arg1 -k argA -q argY',
            'echo arg1 -k argB -q argX', 'echo arg1 -k argB -q argY',
            'echo arg1 -k argC -q argX', 'echo arg1 -k argC -q argY',
            'echo arg2 -k argA -q argX', 'echo arg2 -k argA -q argY',
            'echo arg2 -k argB -q argX', 'echo arg2 -k argB -q argY',
            'echo arg2 -k argC -q argX', 'echo arg2 -k argC -q argY']


def test_add_parameter_combinations(p, expected_commands):
    command_template = "echo {} -k {} -q {}"
    p.add_parameter_combinations(
        command_template, ["arg1", "arg2"], ["argA", "argB", "argC"], ["argX", "argY"]
    )

    assert p.commands == expected_commands


def test__build_resource_string(p):
    assert p._build_resource_string() == "arch=intel*,h_data=1G,h_rt=0:10:00,highp"


def test_parse_psub_command_string_to_command_list(p, expected_commands):
    line_ = "echo {} -k {} -q {} ::: arg1 arg2 ::: argA argB argC ::: argX argY"
    assert expected_commands == p.parse_psub_command_string_to_command_list(line_)


def test_cli():
    import os
    os.system('psub echo {} -k {} -q {} ::: arg1 arg2 ::: argA argB argC ::: argX argY')
