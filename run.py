#!/usr/bin/env python3
"""Barber Bot — точка запуску.

    python3 run.py           запустити бота
    python3 run.py check     перевірити налаштування
    python3 run.py chat      поговорити з AI у терміналі
    python3 run.py eval      перевірити AI на тестових діалогах
    python3 run.py dialogs   вивантажити листування з клієнтами
    python3 run.py test      запустити автотести
"""

import sys

if sys.version_info < (3, 11):
    print(f"Потрібен Python 3.11 або новіший, а зараз {sys.version.split()[0]}.")
    print("Встановіть свіжий Python з https://www.python.org/downloads/ і запускайте командою python3.")
    sys.exit(1)

from barberbot.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
