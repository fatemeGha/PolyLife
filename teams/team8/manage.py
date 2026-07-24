#!/usr/bin/env python
"""Django command-line utility for the standalone Team 8 service."""

import os
import sys
from pathlib import Path


def main():
    # Keep this app importable as ``teams.team8`` both from the monorepo and
    # when manage.py is invoked directly inside this folder.
    repository_root = Path(__file__).resolve().parents[2]
    if str(repository_root) not in sys.path:
        sys.path.insert(0, str(repository_root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
