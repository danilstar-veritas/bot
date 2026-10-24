"""Розрахунок вільного часу. Чисті функції без бази даних — легко тестувати."""

from __future__ import annotations

from datetime import datetime, timedelta

Interval = tuple[datetime, datetime]


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def free_starts(work: list[Interval], busy: list[Interval], duration_min: int, step_min: int,
                not_before: datetime) -> list[datetime]:
    """Можливі початки візиту тривалістю duration_min у робочих проміжках work.

    Початки йдуть із кроком step_min від початку кожного робочого проміжку;
    візит має повністю вміщатися в проміжок і не перетинатися з busy.
    """
    duration = timedelta(minutes=duration_min)
    step = timedelta(minutes=step_min)
    result: list[datetime] = []
    for start, end in work:
        t = start
        while t + duration <= end:
            if t >= not_before and not any(overlaps(t, t + duration, bs, be) for bs, be in busy):
                result.append(t)
            t += step
    return result
