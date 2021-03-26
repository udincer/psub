#!/usr/bin/env python3

"""Submit array jobs to a SGE cluster without all the suffering."""

import sys
import os
import subprocess
import argparse
import re
import itertools
import textwrap
from datetime import datetime


class Psub:

    PSUB_MAIN = """
TASKS_FILE=$1
N_TASKS=$(cat $TASKS_FILE | wc -l)
NUM_IN_BATCH=${{2:-1}}
echo Submitting $N_TASKS tasks to the queue from $TASKS_FILE, with $NUM_IN_BATCH lines in each batch
qsub <<CMD
#!/bin/bash
#$ -cwd
#$ -j y
#$ -S /bin/bash
#$ -V
#$ -l {l_str}
## -pe shared 1
#$ -N $(basename $TASKS_FILE)_$(date +%s)_$RANDOM
#$ -o {logdir}/job.\$TASK_ID.${{HOSTNAME}}.log
#$ -m bae
#$ -t 1-${{N_TASKS}}:${{NUM_IN_BATCH}}
{tmpdir}/run_task.sh ${{TASKS_FILE}} ${{NUM_IN_BATCH}}
sleep $((11-SECONDS)) 2> /dev/null
CMD
"""

    RUN_TASK = """
TASKS_FILE=$1
NUM_IN_BATCH=$2
for ((i=0; i<${NUM_IN_BATCH}; i++)); do
    LINE_NUM=$((SGE_TASK_ID+i))
    CMD=$(awk "NR==$LINE_NUM" $TASKS_FILE)
    eval $CMD
done"""

    def __init__(self, name=None, tmpdir=None):

        if name is None:
            now_str = datetime.now().strftime("%Y%m%dT%H%M")
            name = f"job.{now_str}"

        self.command_l = []
        self.name = name

        if tmpdir is None:
            tmpdir = f"tmp/psub/{self.name}"

        if not os.path.isabs(tmpdir):
            cwd = os.getcwd()
            tmpdir = os.path.join(cwd, tmpdir)

        self.tmpdir = tmpdir
        self.logdir = f"{self.tmpdir}/logs"
        self.cmd_fn = f"{self.tmpdir}/{self.name}.sh"

        self.jobs_per_batch = 1

        # default resources
        self.resource_dict = {
            "l_arch": "intel*",
            "l_mem": "4G",
            "l_time": "7:59:00",
            "l_highp": "highp",
        }

        self.set_resources()

    def __repr__(self):
        repr_str = []

        repr_str.append(f"Psub: {self.name}")
        repr_str.append(f"Resources to request: {self.l_str}")

        num_commands = len(self.command_l)

        if self.jobs_per_batch == 1:
            repr_str.append(f"{num_commands} commands will be submitted:")
        else:
            repr_str.append(
                f"{num_commands} commands will be submitted, "
                f"{self.jobs_per_batch} jobs per batch:")

        if len(self.command_l) > 10:
            command_l_disp = self.command_l[:5]
            command_l_disp += ["..."]
            command_l_disp += self.command_l[-5:]
        else:
            command_l_disp = self.command_l

        for cmd in command_l_disp:
            repr_str.append(cmd)

        return "\n".join(repr_str)

    def set_resources(self, l_arch=None, l_mem=None, l_time=None, l_highp=None):

        if l_arch is not None:
            self.resource_dict["l_arch"] = l_arch

        if l_mem is not None:
            self.resource_dict["l_mem"] = l_mem

        if l_time is not None:
            self.resource_dict["l_time"] = l_time

        if l_highp is not None:
            self.resource_dict["l_highp"] = l_highp

        l_str = "arch={l_arch},h_data={l_mem},h_rt={l_time}".format(
            **self.resource_dict
        )
        if self.resource_dict["l_highp"]:
            l_str += ",highp"

        self.l_str = l_str

    def add(self, cmd):
        if isinstance(cmd, str):
            self.command_l.append(cmd)
        elif isinstance(cmd, list):
            self.command_l.extend(cmd)
        else:
            raise TypeError("Commands should be str or list of str")

    def submit(self, dryrun=False, skip_confirm=False):
        os.makedirs(self.logdir, exist_ok=True)

        with open(self.cmd_fn, "w") as f:
            for cmd in self.command_l:
                print(cmd, file=f)

        psub_main_params = {
            "l_str": self.l_str,
            "logdir": self.logdir,
            "tmpdir": self.tmpdir,
        }

        psub_main_fn = f"{self.tmpdir}/psub_main.sh"
        with open(psub_main_fn, "w") as f:
            print(Psub.PSUB_MAIN.format(**psub_main_params), file=f)

        run_task_fn = f"{self.tmpdir}/run_task.sh"
        with open(run_task_fn, "w") as f:
            print(Psub.RUN_TASK, file=f)

        # make the scripts executable
        os.chmod(psub_main_fn, 0o755)
        os.chmod(run_task_fn, 0o755)

        subprocess_cmd = f". {self.tmpdir}/psub_main.sh {self.cmd_fn} {self.jobs_per_batch}"

        print(str(self))

        if dryrun:
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


def parse_command(command):

    command_l = command.split(":::")

    base_command = command_l[0]

    groups = []
    for ss in command_l[1:]:
        if ss[0] == ":":
            fn = ss[1:].strip()
            groups.append((fn, True))
        else:
            args = ss.strip().split()
            groups.append((args, False))

    groups_l = []
    for args_, is_fn in groups:
        args = []
        if is_fn:
            with open(args_) as f:
                for line in f:
                    args.append(line.strip())
        else:
            args = args_

        groups_l.append(args)

    num_fields_in_command = len(re.findall("\{\}", base_command))

    args = [current for current in itertools.product(*groups_l)]
    num_args = len(args[0])

    if num_fields_in_command > num_args:
        raise ValueError("Too many replacement strings {}.")

    base_command += "{} " * (num_args - num_fields_in_command)
    base_command = base_command.strip()

    return [base_command.format(*arg_) for arg_ in args]


if __name__ == "__main__":

    ARGPARSE_HELP_STRING = """Submit jobs to the SGE cluster without all the suffering. 
            
Usage example:
psub \\
--jobname my_job \\
--mem 4G \\
--time 12:00:00 \\
"./my_script.py {} --parameter {} ::: arg1 arg2 ::: p1 p2 p3"

This will run my_script.py as a job array with 6 jobs for each combination 
of arg and p.

Use ::: to expand a list of parameters and :::: to read from each line in a file.
Inspired by GNU Parallel's interface (which does it better).
"""

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
        "-b", "--jobs-per-batch", help="Number of jobs per batch"
    )

    # alternative to :::: syntax
    parser.add_argument(
        "-a",
        "--file",
        action="store_true",
        help=(
            'Submit jobs for file where each line is a command. '
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

    parser.add_argument("command", nargs="+", help="Command template string")

    if len(sys.argv) < 2:
        parser.print_help(sys.stderr)
        raise SystemExit()
    
    args = parser.parse_args()

    command = " ".join(args.command)

    p = Psub(name=args.jobname, tmpdir=args.tmpdir)

    if args.l_arch is not None:
        p.set_resources(l_arch=args.l_arch)

    if args.l_mem is not None:
        p.set_resources(l_mem=args.l_mem)

    if args.l_time is not None:
        p.set_resources(l_time=args.l_time)

    if args.l_highp is not None:
        p.set_resources(l_highp=args.l_highp)

    if args.jobs_per_batch is not None:
        p.jobs_per_batch = args.jobs_per_batch

    if args.file:
        command = f":::: {command}"

    commands = parse_command(command)

    p.add(commands)

    p.submit(dryrun=args.dry_run, skip_confirm=args.yes)