import argparse
import subprocess
import sys
from glob import glob
import shutil

from simple_term_menu import TerminalMenu

from psub import Psub, __version__


class AnsiColors:
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


def check_status_workflow():
    psub_history_recent_first = sorted(
        Psub.get_history(), key=lambda x: x.submit_time, reverse=True
    )
    terminal_menu = _job_select_terminal_menu(psub_history_recent_first, with_status=True)
    run_choice = terminal_menu.show()

    while run_choice is not None:
        pp = psub_history_recent_first[run_choice]
        terminal_menu_logs = _log_select_terminal_menu_with_status(pp)

        log_fns = sorted(glob(f"{pp.log_dir}/*"))
        log_choice = terminal_menu_logs.show()

        while log_choice is not None:
            if shutil.which('bat'):  # check if bat (cat alternative) is installed
                _ = subprocess.run(["bat", "--paging=always", "--wrap=never", f"{log_fns[log_choice]}"])
            else:  # fallback to less
                _ = subprocess.run(["less", f"{log_fns[log_choice]}"])
            log_choice = terminal_menu_logs.show()

        run_choice = terminal_menu.show()


def _job_select_terminal_menu(psub_history_recent_first, with_status=False, num_with_status=10):
    one_line_reps = [p.str_single_line() for p in psub_history_recent_first]

    if with_status:
        statuses = []
        reps_with_status = []
        for j, p in enumerate(psub_history_recent_first):
            if j < num_with_status:
                status_ = p.status
                statuses.append(status_)

                rep = one_line_reps[j]
                reps_with_status.append(f"{rep} -> {status_}")
            else:
                statuses.append("...")
                rep = one_line_reps[j]
                reps_with_status.append(f"{rep} -> ...")

        one_line_reps_ = reps_with_status

        def psub_preview_with_status(i) -> str:
            p = psub_history_recent_first[int(i)]
            status_ = statuses[int(i)]

            ansi_color_code_d = {
                "Finished": AnsiColors.OKGREEN,
                "Errors": AnsiColors.FAIL,
                "Not yet started": AnsiColors.OKBLUE,
                "Running": AnsiColors.OKCYAN,
                "...": AnsiColors.OKBLUE,
            }

            color_code = [
                col for k, col in ansi_color_code_d.items() if status_.startswith(k)
            ][0]

            status_c = f"{color_code}{status_}{AnsiColors.ENDC}"
            s_ = f"{status_c} \n" f"{str(p)}"
            return s_

        psub_preview_ = psub_preview_with_status

    else:
        one_line_reps_ = one_line_reps

        def psub_preview(i) -> str:
            p = psub_history_recent_first[int(i)]
            s_ = f"{str(p)}"
            return s_

        psub_preview_ = psub_preview

    one_line_reps_with_data_component = [
        menu_item.replace("|", r"\|") + "|" + str(i)
        for i, menu_item in enumerate(one_line_reps_)
    ]

    terminal_menu = TerminalMenu(
        one_line_reps_with_data_component,
        title="Psub job history:",
        preview_command=psub_preview_,
        preview_size=0.75,
        status_bar="q -> go back, / -> search",
    )

    return terminal_menu


def _log_select_terminal_menu(pp: Psub):
    log_fns = sorted(glob(f"{pp.log_dir}/*"))

    def log_preview(log_fn) -> str:
        log_l = []
        with open(log_fn) as f:
            for line in f:
                log_l.append(line)
        if len(log_l) > 30:
            log_str = ''.join(log_l[:15] + ['...\n'] + log_l[-15:])
        else:
            log_str = ''.join(log_l)
        return log_str

    terminal_menu_logs = TerminalMenu(
        log_fns,
        title=f"Job logs for {pp.name}:",
        preview_command=log_preview,
        preview_size=0.75,
        status_bar="q -> go back, / -> search",
    )

    return terminal_menu_logs

def _log_select_terminal_menu_with_status(pp: Psub):
    log_fns = sorted(glob(f"{pp.log_dir}/*"))
    exit_codes_d = pp._get_exit_codes()

    log_fn_with_exit_code_d = {}
    log_fn_with_exit_code_d_no_error = {}
    log_fn_with_exit_code_d_with_error = {}

    for log_fn in log_fns:
        job_number = int(log_fn.split('/')[-1].split('.')[1])
        exit_code = exit_codes_d.get(int(job_number))
        log_fn_with_exit_code_d[job_number]  = f"{log_fn} ## {exit_code}"

        if exit_code == '0':
            log_fn_with_exit_code_d_no_error[job_number]  = f"{log_fn} ## {exit_code}"
        else:
            log_fn_with_exit_code_d_with_error[job_number]  = f"{log_fn} ## {exit_code}"

    l1 = [log_fn_with_exit_code_d_with_error[key] for key in sorted(log_fn_with_exit_code_d_with_error.keys())]
    l2 = [log_fn_with_exit_code_d_no_error[key] for key in sorted(log_fn_with_exit_code_d_no_error.keys())]
    
    log_fn_with_exit_code_l = l1 + l2

    def log_preview(log_fn_with_exit_code) -> str:
        log_fn, exit_code = log_fn_with_exit_code.split(' ## ')
        log_l = []
        with open(log_fn) as f:
            for line in f:
                log_l.append(line)
        if len(log_l) > 30:
            log_str = ''.join(log_l[:15] + ['...\n'] + log_l[-15:])
        else:
            log_str = ''.join(log_l)
        return log_str

    terminal_menu_logs = TerminalMenu(
        log_fn_with_exit_code_l,
        title=f"Job logs for {pp.name}:",
        preview_command=log_preview,
        preview_size=0.75,
        status_bar="q -> go back, / -> search",
    )

    return terminal_menu_logs


def logging_workflow():
    psub_history_recent_first = sorted(
        Psub.get_history(), key=lambda x: x.submit_time, reverse=True
    )

    terminal_menu = _job_select_terminal_menu(psub_history_recent_first)
    run_choice = terminal_menu.show()

    while run_choice is not None:
        pp = psub_history_recent_first[run_choice]
        terminal_menu_logs = _log_select_terminal_menu(pp)

        log_fns = sorted(glob(f"{pp.log_dir}/*"))
        log_choice = terminal_menu_logs.show()

        while log_choice is not None:
            if shutil.which('bat'):  # check if bat (cat alternative) is installed
                _ = subprocess.run(["bat", "--paging=always", "--wrap=never", f"{log_fns[log_choice]}"])
            else:  # fallback to less
                _ = subprocess.run(["less", f"{log_fns[log_choice]}"])
            log_choice = terminal_menu_logs.show()

        run_choice = terminal_menu.show()


def main():
    ARGPARSE_HELP_STRING = """
Submit and monitor jobs, organize logs on UCLA's Hoffman2 cluster.
            
Submitting jobs:
    psub \\
    --jobname my_job \\
    --mem 4G \\
    --time 12:00:00 \\
    "./my_script.py {} --parameter {} ::: arg1 arg2 ::: p1 p2 p3"
    This will run my_script.py as a job array with 6 jobs for each combination 
    of arg and p.
    Use ::: to expand a list of parameters and :::: to read from each line in a file.
    Inspired by GNU Parallel's interface.
    
Viewing logs:
    Use the `psub logs` subcommand.
    
Checking job statuses:
    Use the `psub status` subcommand.
"""

    ARGPARSE_HELP_STRING = f"psub {__version__}:" + ARGPARSE_HELP_STRING
    # todo add more detail to help string

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
        "-y",
        "--yes",
        action="store_true",
        default=False,
        help="Do not ask for confirmation before submitting jobs.",
    )

    parser.add_argument(
        "-L",
        "--logs",
        action="store_true",
        default=False,
        help="View logs from submitted jobs.",
    )

    parser.add_argument(
        "command", nargs=argparse.REMAINDER, help="Command template string"
    )

    if len(sys.argv) < 2:
        parser.print_help(sys.stderr)
        raise SystemExit()

    # check if subcommand is 'logs'
    if sys.argv[1] == "logs":
        logging_workflow()
        return

    if sys.argv[1] == "status":
        check_status_workflow()
        return

    args = parser.parse_args()

    if args.logs:
        logging_workflow()
        return

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


if __name__ == "__main__":
    main()
