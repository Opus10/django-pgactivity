import datetime as dt
import os
import textwrap

from django.core.management.base import BaseCommand

from pgactivity import config, models


class SubCommands(BaseCommand):  # pragma: no cover
    """
    Subcommand class vendored in from
    https://github.com/andrewp-as-is/django-subcommands.py
    because of installation issues
    """

    argv = []
    subcommands = {}

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="subcommand", title="subcommands", description="")
        subparsers.required = True

        for command_name, command_class in self.subcommands.items():
            command = command_class()

            subparser = subparsers.add_parser(command_name, help=command_class.help)
            command.add_arguments(subparser)
            prog_name = subcommand = ""
            if self.argv:
                prog_name = self.argv[0]
                subcommand = self.argv[1]

            command_parser = command.create_parser(prog_name, subcommand)
            subparser._actions = command_parser._actions

    def run_from_argv(self, argv):
        self.argv = argv
        return super().run_from_argv(argv)

    def handle(self, *args, **options):
        command_name = options["subcommand"]
        self.subcommands.get(command_name)
        command_class = self.subcommands[command_name]

        if self.argv:
            args = [self.argv[0]] + self.argv[2:]
            return command_class().run_from_argv(args)
        else:
            return command_class().execute(*args, **options)


class CancelCommand(BaseCommand):
    help = "Cancel activity."

    def add_arguments(self, parser):
        parser.add_argument("pids", nargs="+", type=str)

    def handle(self, *args, **options):
        cancelled = models.PGActivity.objects.pid(*options["pids"]).cancel()
        pluralize = "y" if len(cancelled) == 1 else "ies"
        self.stdout.write(f"Cancelled {len(cancelled)} quer{pluralize}")


class TerminateCommand(BaseCommand):
    help = "Terminate activity."

    def add_arguments(self, parser):
        parser.add_argument("pids", nargs="+", type=str)

    def handle(self, *args, **options):
        terminated = models.PGActivity.objects.pid(*options["pids"]).terminate()
        pluralize = "y" if len(terminated) == 1 else "ies"
        self.stdout.write(f"Terminated {len(terminated)} quer{pluralize}")


def get_terminal_width():
    try:
        return os.get_terminal_size().columns
    except OSError:  # This only happens during testing
        return 80


class LsCommand(BaseCommand):
    help = "List activity."

    def add_arguments(self, parser):
        parser.add_argument("pids", nargs="*", type=str)
        parser.add_argument("-d", "--database", help="The database")
        parser.add_argument(
            "-f",
            "--filters",
            action="append",
            help="Filters for the query",
        )
        parser.add_argument("-l", "--limit", help="Limit results")
        parser.add_argument("-e", "--expanded", action="store_true", help="List an expanded view")
        parser.add_argument("-c", "--config", help="Use a config from settings.PGACTIVITY_CONFIGS")

    def handle(self, *args, **options):
        overrides = {key: val for key, val in options.items() if val}
        activity = models.PGActivity.objects.order_by("-duration").config(
            options["config"], **overrides
        )

        cfg = config.get(options["config"], **options)

        term_w = get_terminal_width()

        for a in activity:
            duration = a.duration
            if duration:  # pragma: no branch
                duration -= dt.timedelta(microseconds=duration.microseconds)

            if cfg.get("expanded"):
                self.stdout.write("-" * term_w)
                self.stdout.write(f"pid: {a.id}")
                self.stdout.write(f"duration: {duration}")
                self.stdout.write(f"state: {a.state}")
                self.stdout.write(f"context: {a.context}")
                query = textwrap.dedent(a.query).strip()
                self.stdout.write(f"query: {query}")
            else:
                line = (
                    f"{a.id} | {duration} | {a.state} | {a.context} |"
                    f" {' '.join(a.query.split())}"
                )
                self.stdout.write(f"{line[:term_w]}")


class Command(SubCommands):
    help = "Core django-pgactivity subcommands."

    subcommands = {
        "cancel": CancelCommand,
        "terminate": TerminateCommand,
        "ls": LsCommand,
    }
