"""Submit array jobs to a SGE cluster without all the suffering."""

import os
import subprocess
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

        repr_str.append(f"{num_commands} commands will be submitted:")

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

    def submit(self, dryrun=False):
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

        subprocess_cmd = f". {self.tmpdir}/psub_main.sh {self.cmd_fn}"

        if dryrun:
            print(str(self))
        else:
            comp_process = subprocess.run(
                subprocess_cmd,
                shell=True,
                universal_newlines=True,
                stdout=subprocess.PIPE,
            )
            print(comp_process.stdout)