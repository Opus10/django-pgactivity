import datetime as dt
import os
import re
import sys
import textwrap

from django.core.management.base import BaseCommand
from django.db.models import F

from pgactivity import config, models


def get_terminal_width():  # pragma: no cover
    try:
        return os.get_terminal_size().columns
    except OSError:  # This only happens during testing
        return 80


def _format(val, expanded):
    if isinstance(val, dt.timedelta):
        if val:  # pragma: no branch
            val -= dt.timedelta(microseconds=val.microseconds)
    elif isinstance(val, str):
        if not expanded:
            val = " ".join(val.split())
        else:
            val = textwrap.dedent(val).strip()

    return str(val)


def _handle_user_input(*, cfg, num_queries, stdout):
    is_cancel = cfg.get("cancel")

    if not num_queries:
        stdout.write(f"No queries to {'cancel' if is_cancel else 'terminate'}.")
        return False

    if not cfg.get("yes"):
        pluralize = "y" if num_queries == 1 else "ies"
        resp = input(
            (
                f"{'Cancel' if is_cancel else 'Terminate'} "
                f"{num_queries} quer{pluralize}? (y/[n]) "
            )
        )
        if not re.match("^(y)(es)?$", resp, re.IGNORECASE):
            stdout.write("Aborting!")
            return False

    return True


class Command(BaseCommand):
    help = "Show and manage activity."

    def add_arguments(self, parser):
        parser.add_argument("pids", nargs="*", type=str)
        parser.add_argument("-d", "--database", help="The database")
        parser.add_argument(
            "-f",
            "--filter",
            action="append",
            dest="filters",
            help="Filters for the underlying queryset",
        )
        parser.add_argument(
            "-a",
            "--attribute",
            action="append",
            dest="attributes",
            help="Attributes to show",
        )
        parser.add_argument("-l", "--limit", help="Limit results")
        parser.add_argument("-e", "--expanded", action="store_true", help="Show an expanded view")
        parser.add_argument("-c", "--config", help="Use a config from settings.PGACTIVITY_CONFIGS")
        parser.add_argument("-y", "--yes", action="store_true", help="Don't prompt for input")

        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--cancel",
            action="store_true",
            help="Cancel activity",
        )
        group.add_argument(
            "--terminate",
            action="store_true",
            help="Terminate activity",
        )

    def handle(self, *args, **options):
        cfg = config.get(options["config"], **options)
        is_cancel = cfg.get("cancel")
        is_terminate = cfg.get("terminate")
        activity = (models.PGActivity.objects.config(options["config"], **options)).values(
            *cfg["attributes"]
        )

        term_w = get_terminal_width()
        expanded = cfg.get("expanded", False)

        if is_cancel or is_terminate:
            activity = activity.distinct("id")
            num_queries = len(activity)

            if not _handle_user_input(cfg=cfg, num_queries=num_queries, stdout=self.stdout):
                sys.exit(1)

            method_name = "cancel" if is_cancel else "terminate"
            num_success = len(getattr(activity, method_name)())
            pluralize = "y" if num_success == 1 else "ies"
            self.stdout.write(
                (f"{'Canceled' if is_cancel else 'Terminated'} " f"{num_success} quer{pluralize}")
            )
        else:
            activity = activity.order_by(F("duration").desc(nulls_last=True))

            if not cfg.get("pids") and cfg.get("limit"):
                activity = activity[: cfg["limit"]]

            for query in activity:
                if cfg.get("expanded"):
                    self.stdout.write("\033[1m" + "─" * term_w + "\033[0m")
                    for a in cfg["attributes"]:
                        self.stdout.write(f"\033[1m{a}\033[0m: {_format(query[a], expanded)}")
                else:
                    line = " | ".join(_format(query[a], expanded) for a in cfg["attributes"])
                    line = line[:term_w]
                    self.stdout.write(line)
