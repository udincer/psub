import argparse
import subprocess
import sys
from glob import glob

from psub import Psub


def check_status_select():
    pass


def _job_select_terminal_menu(psub_history_recent_first):
    from simple_term_menu import TerminalMenu

    one_line_reps = [p.str_single_line().replace('|', r'\|')
                     for p in psub_history_recent_first]

    one_line_reps_with_data_component = \
        [f"{menu_item}|{i}"
         for i, menu_item in enumerate(one_line_reps)]

    def psub_preview(i) -> str:
        p = psub_history_recent_first[int(i)]
        return str(p)

    terminal_menu = TerminalMenu(one_line_reps_with_data_component,
                                 title="Psub job history:",
                                 preview_command=psub_preview,
                                 preview_size=0.75,
                                 )

    return terminal_menu


def _log_select_terminal_menu(pp: Psub):
    from simple_term_menu import TerminalMenu

    log_fns = sorted(glob(f"{pp.log_dir}/*"))

    def log_preview(log_fn) -> str:
        with open(log_fn) as f:
            log = f.read()
        return log

    terminal_menu_logs = TerminalMenu(log_fns,
                                      title=f"Job logs for {pp.name}:",
                                      preview_command=log_preview,
                                      preview_size=0.75,
                                      )

    return terminal_menu_logs


def logging_workflow():
    psub_history_recent_first = sorted(Psub.get_history(),
                                       key=lambda x: x.submit_time,
                                       reverse=True)

    terminal_menu = _job_select_terminal_menu(psub_history_recent_first)
    run_choice = terminal_menu.show()

    while run_choice is not None:
        pp = psub_history_recent_first[run_choice]
        terminal_menu_logs = _log_select_terminal_menu(pp)

        log_fns = sorted(glob(f"{pp.log_dir}/*"))
        log_choice = terminal_menu_logs.show()

        while log_choice is not None:
            _ = subprocess.run(['less', f"{log_fns[log_choice]}"])
            log_choice = terminal_menu_logs.show()

        run_choice = terminal_menu.show()


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
        "-y",
        "--yes",
        action="store_true",
        default=False,
        help="Do not ask for confirmation before submitting jobs.",
    )

    parser.add_argument(
        '-L',
        '--logs',
        action="store_true",
        default=False,
        help="Do not ask for confirmation before submitting jobs.",
    )

    parser.add_argument("command", nargs=argparse.REMAINDER,
                        help="Command template string")

    if len(sys.argv) < 2:
        parser.print_help(sys.stderr)
        raise SystemExit()

    # check if subcommand is 'logs'
    if sys.argv[1] == 'logs':
        logging_workflow()
        return

    if sys.argv[1] == 'status':
        check_status_select()
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


if __name__ == '__main__':
    main()
