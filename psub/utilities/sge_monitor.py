import os
import time
import sys
import subprocess
from datetime import datetime
from collections import defaultdict
import shutil
import xml.etree.cElementTree as ET

""" Monitor jobs on SGE

Updates status every minute
"""

USER = os.environ['USER']


class AnsiCommands:
    """https://stackoverflow.com/questions/287871/"""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    START_LINE = "\033[F"
    UP_LINE = "\033[A"
    SWITCH_ALT_SCREEN = '\033[?1049h'
    SWITCH_NORMAL_SCREEN = '\033[?1049l'


class Job:

    def __repr__(self):
        return str(self.__dict__)

    def one_line_rep(self, line_max=79, color=True) -> str:
        if line_max < 80:
            line_max = 79

        job_number = self.JB_job_number
        job_name = self.JB_name
        job_state = getattr(self, 'state', 'unknown')

        job_start_time = getattr(self, 'JAT_start_time', None)
        job_submission_time = getattr(self, 'JB_submission_time', None)

        job_time = next(
            (t for t in [job_start_time, job_submission_time] if t is not None), '')
        timediff = datetime.now() - datetime.fromisoformat(job_time)
        job_time = str(timediff).split('.')[0]

        job_queue = self.queue_name if self.queue_name is not None else "-"
        job_slots = self.slots

        tasks = getattr(self, 'tasks', '')

        job_name_ = ""
        s_ = f"{job_number}: {job_state} ➜ {job_name_} | {job_time} | {job_queue} {tasks} n{job_slots}"

        job_name_len = line_max - len(s_)

        job_name_ = job_name[:job_name_len - 3] + '...' if len(
            job_name) > job_name_len else job_name

        s_2 = f"{job_number}: {job_state} ➜ {job_name_} | {job_time} | {job_queue} {tasks} n{job_slots}"
        slack = line_max - len(s_2) + len(job_name_)

        if color:
            col_ = AnsiCommands.OKGREEN if job_state == 'r' else AnsiCommands.OKBLUE
            col_end = AnsiCommands.ENDC
        else:
            col_ = ''
            col_end = ''

        return f"{job_number}: {col_}{job_state} ➜ {job_name_:<{slack}}{col_end} | {job_time} | {job_queue} {tasks} n{job_slots}"


def etree_to_dict(t):
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib:
        d[t.tag].update(('@' + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d


def get_job_list(dd):
    job_list = []

    try:
        l1 = dd['job_info']['queue_info']['job_list']
    except Exception:
        l1 = []

    try:
        l2 = dd['job_info']['job_info']['job_list']
    except Exception:
        l2 = []

    for ll in [l1, l2]:
        if not isinstance(ll, list):
            ll = [ll]

        job_list += ll

    jobs = []
    for job_d in job_list:
        j = Job()
        j.__dict__.update(job_d)
        jobs.append(j)

    return jobs


def get_job_lines():
    cp = subprocess.run(f'qstat -u {USER} -xml', capture_output=True, shell=True)
    xml_ = cp.stdout.decode()

    e = ET.XML(xml_)

    dd = etree_to_dict(e)
    job_list = get_job_list(dd)

    line_width, term_height = shutil.get_terminal_size((80, 20))

    lines = [j.one_line_rep(line_width) for j in job_list]
    return lines


def main():
    try:
        sys.stdout.write(AnsiCommands.SWITCH_ALT_SCREEN)
        while True:
            line_width, term_height = shutil.get_terminal_size((80, 20))
            lines = get_job_lines()
            num_blank_lines = term_height - len(lines) - 1
            lines += [''] * num_blank_lines

            for line in lines:
                print(line)

            GO_UP = f"\u001b[{term_height - 1}A"
            GO_LEFT = u"\u001b[1000D"

            sys.stdout.write(GO_LEFT)
            sys.stdout.write(GO_UP)

            time.sleep(1)

    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.flush()
        sys.stdout.write(AnsiCommands.SWITCH_NORMAL_SCREEN)


if __name__ == '__main__':
    main()
