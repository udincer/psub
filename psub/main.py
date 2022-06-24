import itertools
import os
import subprocess
from collections import Counter
from datetime import datetime
from glob import glob
from pathlib import Path
from typing import List, Union, Tuple, Iterator, Dict
import re
import json
import logging
import copy

from psub import submission_scripts
from psub import sqlite_utils

logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

PATH_PSUB = os.environ.get("PSUB_PATH", f"{Path.home()}/.psub")
TMP_DIR = f"{os.environ.get('SCRATCH', PATH_PSUB)}/psub_tmp"
HISTORY_DIR = f"{PATH_PSUB}/history"

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
        psub_path: str = None
    ):
        if name is None:
            name = "job"
        now_str = datetime.now().strftime("%Y_%m_%dT%H%M")
        self.name = f"{name}.{now_str}"

        PATH_PSUB = os.environ.get("PSUB_PATH", f"{Path.home()}/.psub") if psub_path is None else psub_path
        TMP_DIR = f"{os.environ.get('SCRATCH', PATH_PSUB)}/psub_tmp"

        self.log_dir = f"{PATH_PSUB}/logs/{self.name}"
        self.tmp_dir = f"{TMP_DIR}/{self.name}"
        self.history_dir = f"{PATH_PSUB}/history"

        self.commands_list_fn = f"{self.tmp_dir}/{self.name}.commands.sh"
        self.submission_script_fn = f"{self.tmp_dir}/submission_script.sh"
        self.task_runner_fn = f"{self.tmp_dir}/run_task.sh"

        self.sqlite_write_fn = f"{self.tmp_dir}/sqlite_write.py"
        self.status_update_sh_fn = f"{self.tmp_dir}/status_update.sh"

        self.l_arch = l_arch
        self.l_mem = l_mem if l_mem is not None else "4G"
        self.l_time = l_time if l_time is not None else "7:59:59"
        self.l_highp = l_highp if l_highp is not None else True
        self.num_cores = num_cores if num_cores is not None else 1

        self.batch_size = batch_size if batch_size is not None else 1

        self.submit_time = None

        self.commands: List[str] = []
        

    def __str__(self):
        repr_str = [
            f"Psub: {self.name}",
            f"Resources to request: {self._build_resource_string()}",
            f"Cores per job: {self.num_cores}",
            "",
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

    def __repr__(self):
        return str(self)

    def str_single_line(self):
        max_line_len = 79
        sample_command = self.commands[0]
        single_line_str = f"Psub[{len(self.commands)}]: {self.name} | {sample_command}"
        if len(single_line_str) > max_line_len:
            return single_line_str[: max_line_len - 3] + "..."
        else:
            return single_line_str

    def add(self, commands: Union[List[str], str]):
        if isinstance(commands, str):
            commands = [commands]
        self.commands += commands

    def add_parameter_combinations(self, command_template: str, *parameters: List[str]):

        num_fields = len(re.findall(r"{}", command_template))
        assert num_fields == len(parameters), (
            f"Mismatch between number of fields in template and number "
            f"of parameters: {num_fields}, {len(parameters)} "
        )

        parameter_combinations: Iterator[Tuple] = itertools.product(*parameters)
        self.commands += [command_template.format(*c) for c in parameter_combinations]

    def submit(self, dry_run: bool = False, skip_confirm: bool = False, ssh_host=None):
        assert self.commands, "Command list empty"

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
            self._prepare_submit_files()
            if ssh_host:
                try:
                    self._submit_through_ssh(ssh_host, subprocess_cmd)
                    self._register_to_history()
                except Exception as e:
                    print(e)
            else:
                self._prepare_submit_files()
                comp_process = subprocess.run(
                    subprocess_cmd,
                    shell=True,
                    universal_newlines=True,
                    stdout=subprocess.PIPE,
                )
                print(comp_process.stdout)
                self._register_to_history()

    @classmethod
    def _submit_through_ssh(cls, ssh_host, subprocess_cmd, conda_env_name='tev'):
        from fabric import Connection

        c = Connection(
            ssh_host,
            connect_kwargs={"key_filename": [str(Path.home() / ".ssh/id_rsa")]},
        )
        cmd_ = f"""hostname &&
source activate {conda_env_name} &&
which python &&
cd {os.getcwd()} &&
{subprocess_cmd}
"""

        return c.run(cmd_)

    def _prepare_submit_files(self):
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.history_dir, exist_ok=True)
        os.makedirs(self.tmp_dir, exist_ok=True)
        os.makedirs(f"{self.tmp_dir}/exit_status", exist_ok=True)

        with open(self.commands_list_fn, "w") as f:
            for cmd_ in self.commands:
                print(cmd_, file=f)

        psub_main_params = {
            "l_str": self._build_resource_string(),
            "num_cores": self.num_cores,
            "logdir": self.log_dir,
            "tmpdir": self.tmp_dir,
            "pre_task_runner_script": "",
            "post_task_runner_script": "",
        }

        with open(self.submission_script_fn, "w") as f:
            print(submission_scripts.PSUB_MAIN.format(**psub_main_params), file=f)

        with open(self.task_runner_fn, "w") as f:
            print(submission_scripts.RUN_TASK, file=f)

        with open(self.sqlite_write_fn, "w") as f:
            print(submission_scripts.PY_SQLITE_WRITE, file=f)

        with open(self.status_update_sh_fn, "w") as f:
            print(
                submission_scripts.STATUS_UPDATE_SH.format(**psub_main_params), file=f
            )

        # make the scripts executable
        os.chmod(self.submission_script_fn, 0o755)
        os.chmod(self.task_runner_fn, 0o755)
        os.chmod(self.sqlite_write_fn, 0o755)
        os.chmod(self.status_update_sh_fn, 0o755)

    def _get_exit_codes(self):
        exit_status_d = {}
        try:
            exit_status_sqlite_fn = f"{self.tmp_dir}/exit_status/exit_status.sqlite"
            status_d = sqlite_utils.get_dict_from_sqlite(exit_status_sqlite_fn)
            exit_status_d = {int(k): v["exit_code"] for k, v in status_d.items()}
        except Exception as e:
            logging.debug(f"Error retrieving exit status: {exit_status_sqlite_fn}")
            logging.debug(e)
        return exit_status_d

    @property
    def exit_codes(self) -> Dict[str, Union[int, str]]:
        """Possible values:
        0: Success
        Nonzero number: Finished with error
        not_yet_started: Not yet started
        started: Started but not yet finished

        :return: Commands to exit codes
        """

        def interpret_code(v):
            try:
                if int(v) != 0:
                    return "Terminated with nonzero status"
                else:
                    return "Success"
            except ValueError:
                if v == "not_yet_started":
                    return "Not yet started"
                elif v == "started":
                    return "Started"

        exit_status_d = self._get_exit_codes()
        exit_d = {
            c: exit_status_d.get(i + 1, "not_yet_started")
            # line numbers start at 1
            for i, c in enumerate(self.commands)
        }

        return {c: interpret_code(v) for c, v in exit_d.items()}

    @property
    def success(self) -> bool:
        return all(v == "Success" for v in self.exit_codes.values())

    @property
    def status(self) -> str:  # TODO this seems to take a long time
        exit_vals = self.exit_codes.values()
        c = Counter(exit_vals)
        success_rate = c["Success"] / len(exit_vals)
        error_rate = c["Terminated with nonzero status"] / len(exit_vals)
        if all(v == "Success" for v in exit_vals):
            return "Finished"
        elif "Terminated with nonzero status" in exit_vals:
            return f"Errors [{error_rate:.0%}]"
        elif all(v == "Not yet started" for v in exit_vals):
            return "Not yet started"
        else:
            return f"Running [{success_rate:.0%}]"

    def rerun_failed(self, dry_run=False, skip_confirm=True):
        commands_l = [k for k, v in self.exit_codes.items() if v != "Success"]
        p = self.copy()
        p.commands = commands_l
        p.submit(dry_run=dry_run, skip_confirm=skip_confirm)

    def _register_to_history(self):
        assert self.submit_time is not None
        with open(f"{self.history_dir}/{self.submit_time}.{self.name}.json", "w") as f:
            print(self.dumps(), file=f)

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

    def dumps(self):
        return json.dumps(self.__dict__, indent=2)

    @classmethod
    def loads(cls, json_str):
        p = cls()
        d = json.loads(json_str)
        p.__dict__.update(d)
        return p

    @classmethod
    def load(cls, json_fn):
        with open(json_fn) as f:
            json_str = f.read()
        return cls.loads(json_str)

    @classmethod
    def get_history(cls) -> List["Psub"]:
        json_fns = sorted(glob(f"{HISTORY_DIR}/*.json"))
        psub_list = []
        for fn in json_fns:
            try:
                p_ = cls.load(fn)
                if p_.check_valid():
                    psub_list.append(p_)
            except json.JSONDecodeError:
                print(f"Trouble loading {fn}")
        return sorted(psub_list, key=lambda x: x.submit_time, reverse=True)

    def check_valid(self):
        return self.submit_time is not None

    def copy(self):
        return copy.deepcopy(self)
