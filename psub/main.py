import argparse
import itertools
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Union, Tuple, Iterator
import re

from psub import submission_scripts

PATH_HOME = Path.home()
PATH_PSUB = f"{PATH_HOME}/.psub"


class Psub:
    def __init__(
            self,
            name: str = None,
            l_arch: str = "intel*",
            l_mem: str = "4G",
            l_time: str = "7:59:59",
            l_highp: bool = True,
            num_cores: int = 1,
            batch_size: int = 1,
    ):
        if name is None:
            now_str = datetime.now().strftime("%Y_%m_%dT%H%M")
            name = f"job.{now_str}"
        self.name = name

        self.log_dir = f"{PATH_PSUB}/logs/{self.name}"
        self.tmp_dir = f"{PATH_PSUB}/tmp/{self.name}"

        self.commands_list_fn = f"{self.tmp_dir}/commands.sh"
        self.submission_script_fn = f"{self.tmp_dir}/submission_script.sh"
        self.task_runner_fn = f"{self.tmp_dir}/run_task.sh"

        self.l_arch = l_arch if l_arch is not None else "intel*"
        self.l_mem = l_mem if l_mem is not None else "4G"
        self.l_time = l_time if l_time is not None else "7:59:59"
        self.l_highp = l_highp if l_highp is not None else True
        self.num_cores = num_cores if num_cores is not None else 1

        self.batch_size = batch_size if batch_size is not None else 1

        self.history_fn = f"{PATH_PSUB}/psub_history.json"
        self.history_number_of_records_limit = 100

        self.submit_time = None

        self.commands: List[str] = []

    def __str__(self):
        repr_str = [
            f"Psub: {self.name}",
            f"Resources to request: {self._build_resource_string()}",
            f"{len(self.commands)} commands will be submitted:",
        ]

        if self.batch_size > 1:
            repr_str.append(f"Jobs per batch: {self.batch_size}")

        if len(self.commands) > 10:
            commands_to_display = self.commands[:5]
            commands_to_display += ["..."]
            commands_to_display += self.commands[-5:]
        else:
            commands_to_display = self.commands

        for cmd in commands_to_display:
            repr_str.append(cmd)

        return "\n".join(repr_str)

    def add(self, commands: Union[List[str], str]):
        if isinstance(commands, str):
            commands = [commands]
        self.commands += commands

    def add_parameter_combinations(self, command_template: str,
                                   *parameters: List[str]):

        num_fields = len(re.findall(r"{}", command_template))
        assert num_fields == len(parameters), (
            f"Mismatch between number of fields in template and number "
            f"of parameters: {num_fields}, {len(parameters)} "
        )

        parameter_combinations: Iterator[Tuple] = itertools.product(*parameters)
        self.commands += [command_template.format(*c) for c in parameter_combinations]

    def submit(self, dry_run: bool = False, skip_confirm: bool = False):
        assert self.commands, "Command list empty"

        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.tmp_dir, exist_ok=True)

        with open(self.commands_list_fn, "w") as f:
            for cmd_ in self.commands:
                print(cmd_, file=f)

        psub_main_params = {
            "l_str": self._build_resource_string(),
            "logdir": self.log_dir,
            "tmpdir": self.tmp_dir,
        }

        with open(self.submission_script_fn, "w") as f:
            print(submission_scripts.PSUB_MAIN.format(**psub_main_params), file=f)

        with open(self.task_runner_fn, "w") as f:
            print(submission_scripts.RUN_TASK, file=f)

        # make the scripts executable
        os.chmod(self.submission_script_fn, 0o755)
        os.chmod(self.task_runner_fn, 0o755)

        self.submit_time = datetime.now().isoformat(timespec="seconds")

        subprocess_cmd = (
            f". {self.submission_script_fn} {self.commands_list_fn} {self.batch_size}"
        )

        print(str(self))

        if dry_run:
            return

        if not skip_confirm:
            print("\nSubmit to cluster? [Y/n]")
            response = input()
        else:
            response = "y"

        if response in {"", "y", "Y"}:
            comp_process = subprocess.run(
                subprocess_cmd,
                shell=True,
                universal_newlines=True,
                stdout=subprocess.PIPE,
            )
            print(comp_process.stdout)

            self._register_to_history()

    def _register_to_history(self):
        # todo
        pass

    def _build_resource_string(self) -> str:
        l_str = []
        l_str += [f"arch={self.l_arch}"] if self.l_arch is not None else []
        l_str += [f"h_data={self.l_mem}"]
        l_str += [f"h_rt={self.l_time}"]
        l_str += ["highp"] if self.l_highp else []

        return ",".join(l_str)

    @classmethod
    def parse_psub_command_string_to_command_list(cls, line_: str) -> List[str]:
        command_string_l = line_.split(":::")
        command_template = command_string_l[0].strip()

        parameters: List[List[str]] = []
        for argument in command_string_l[1:]:
            if argument[0] == ":":  # arguments given in file
                argument_fn = argument[1:].strip()
                with open(argument_fn) as f:
                    fn_args = [line.strip() for line in f]
                parameters.append(fn_args)
            else:  # arguments given as string
                str_args = argument.strip().split()
                parameters.append(str_args)

        num_fields = len(re.findall(r"{}", command_template))
        assert num_fields == len(parameters), (
            f"Mismatch between number of fields in template and number "
            f"of parameters: {num_fields}, {len(parameters)} "
        )

        parameter_combinations: Iterator[Tuple] = itertools.product(*parameters)
        return [command_template.format(*c) for c in parameter_combinations]


def main():
    ARGPARSE_HELP_STRING = """ Todo
    """  # todo

    parser = argparse.ArgumentParser(
        prog="psub",
        description=ARGPARSE_HELP_STRING,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what jobs will be submitted without actually submitting them.",
    )

    parser.add_argument(
        "-n", "--jobname", help="Name of job that will appear in the queue"
    )

    parser.add_argument(
        "-b", "--jobs-per-batch", "--batch-size", help="Number of jobs per batch"
    )

    parser.add_argument(
        "-a",
        "--file",
        action="store_true",
        help=(
            "Submit jobs for file where each line is a command. "
            'Equivalent to "psub :::: file".'
        ),
    )

    parser.add_argument(
        "--l_arch", "--arch", help="Only request a target CPU architecture, e.g. intel*"
    )
    parser.add_argument("--l_mem", "--mem", help="Memory per core requested, e.g. 4G")
    parser.add_argument(
        "--l_time", "--time", help="Time requested, e.g. 12:00:00 for 12 hours."
    )

    parser.add_argument(
        "-j", "--cores", "--num_cores", help="Number of cores to request."
    )

    parser.add_argument(
        "--l_highp",
        action="store_true",
        default=True,
        help=(
            "Submit to highp queue. "
            "This will only use nodes that belong to your user group and "
            "allows for job durations up to 14 days."
        ),
    )

    parser.add_argument(
        "--tmpdir",
        "--tmp",
        help=(
            "Temporary directory for intermediate scripts generated by psub. "
            "This should be a directory that can be accessed by all nodes. "
            "This means /tmp and /dev/shm won't work."
        ),
    )

    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        default=False,
        help="Do not ask for confirmation before submitting jobs.",
    )

    parser.add_argument("command", nargs=argparse.REMAINDER,
                        help="Command template string")

    if len(sys.argv) < 2:
        parser.print_help(sys.stderr)
        raise SystemExit()

    args = parser.parse_args()

    command_str = " ".join(args.command)

    p = Psub(
        name=args.jobname,
        l_arch=args.l_arch,
        l_mem=args.l_mem,
        l_time=args.l_time,
        l_highp=args.l_highp,
        num_cores=args.cores,
    )

    p.add(Psub.parse_psub_command_string_to_command_list(command_str))

    p.submit(dry_run=args.dry_run, skip_confirm=args.yes)

if __name__ == '__main__':
    main()