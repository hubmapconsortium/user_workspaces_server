#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # requires setting a different env var for DJANGO_SETTINGS_MODULE per environment
    # (e.g. DJANGO_SETTINGS_MODULE="user_workspaces_server_project.settings.local")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "user_workspaces_server_project.settings_default")
    argv = sys.argv
    cmd = argv[1] if len(argv) > 1 else ""
    os.environ["SUBCOMMAND"] = cmd
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
