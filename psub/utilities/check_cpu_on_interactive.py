import subprocess
from pathlib import Path
from datetime import datetime
import asyncio

from psub.utilities.sge_monitor import get_job_list_direct

try:
    path_dir = Path(__file__).parents[0].absolute()
    sge_check_cpu_util_fn = f"{path_dir}/sge_check_cpu_util.py"
except Exception:
    sge_check_cpu_util_fn = (
        "/u/home/d/dincer/work/psub/psub/utilities/sge_check_cpu_util.py"
    )


def get_job_time(job):
    job_start_time = getattr(job, "JAT_start_time", None)
    job_submission_time = getattr(job, "JB_submission_time", None)

    job_time = next(
        (t for t in [job_start_time, job_submission_time] if t is not None), ""
    )
    timediff = datetime.now() - datetime.fromisoformat(job_time)
    job_time = str(timediff).split(".")[0]
    return job_time


def background(f):
    def wrapped(*args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(None, f, *args, **kwargs)

    return wrapped


@background
def get_cpu_usage(job):
    node_name = job.queue_name.split("@")[-1]
    job.node_name = node_name

    cmd_ = f"ssh {node_name} -f 'python {sge_check_cpu_util_fn}'"
    cp = subprocess.run(cmd_, shell=True, capture_output=True)
    cpu_usage = cp.stdout.decode("utf-8").strip()

    job_time = get_job_time(job)

    print(f"{node_name}: {cpu_usage:>5}, {job_time}")
    return node_name, cpu_usage, job_time


cpu_usages_d = {}
job_list = get_job_list_direct()

interactive_jobs = [job for job in job_list if job.JB_name == "QRLOGIN"]
for job in interactive_jobs:
    cpu_usages_d[job.queue_name] = get_cpu_usage(job)
