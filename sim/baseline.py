"""Baseline-uri naive. Punctul de referinta fata de care masuram orice algoritm."""
from __future__ import annotations

from sim.core.types import Pos


class ManhattanPlanner:
    """Merge pe randuri apoi pe coloane. Ignora complet obstacolele si coliziunile."""

    name = "manhattan-naive"

    def plan(self, grid, start, goal, reservations=None, t=0) -> list[Pos]:
        path: list[Pos] = []
        r, c = start
        while r != goal[0]:
            r += 1 if goal[0] > r else -1
            path.append((r, c))
        while c != goal[1]:
            c += 1 if goal[1] > c else -1
            path.append((r, c))
        return path


class NearestAllocator:
    """Fiecare robot liber ia cel mai apropiat task, in ordinea id-ului."""

    name = "greedy-nearest"

    def assign(self, robots, tasks, grid, t) -> dict[str, str]:
        out: dict[str, str] = {}
        luate: set[str] = set()
        for rob in sorted(robots, key=lambda x: x.id):
            disp = [tk for tk in tasks if tk.id not in luate]
            if not disp:
                break
            best = min(
                disp,
                key=lambda tk: (
                    abs(tk.pickup[0] - rob.pos[0]) + abs(tk.pickup[1] - rob.pos[1]),
                    tk.id,
                ),
            )
            out[rob.id] = best.id
            luate.add(best.id)
        return out
