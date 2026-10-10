"""A* in spatiu-timp peste o tabela de rezervari (planificare prioritizata)."""
from __future__ import annotations

import heapq

from sim.core.types import Grid, Planner, Pos, Time

State = tuple[Pos, Time]


def _manhattan(a: Pos, b: Pos) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class PrioritizedPlanner:
    name = "prioritized"

    def __init__(self, base: Planner | None = None, max_wait_steps: int = 8) -> None:
        self.base = base
        self.max_wait_steps = max_wait_steps

    def plan(
        self,
        grid: Grid,
        start: Pos,
        goal: Pos,
        reservations: dict[tuple[Pos, Time], str] | None = None,
        t: Time = 0,
    ) -> list[Pos]:
        if start == goal:
            return []
        if not reservations and self.base is not None:
            return self.base.plan(grid, start, goal, None, t)
        return self._space_time_astar(grid, start, goal, reservations or {}, t)

    def _space_time_astar(
        self,
        grid: Grid,
        start: Pos,
        goal: Pos,
        res: dict[tuple[Pos, Time], str],
        t: Time,
    ) -> list[Pos]:
        horizon = t + self.max_wait_steps + _manhattan(start, goal) * 4
        # Robotul ramane parcat pe tinta dupa sosire, deci tinta trebuie sa nu mai
        # fie rezervata de altcineva dupa momentul sosirii.
        goal_last = max((tau for (p, tau) in res if p == goal), default=t - 1)

        h0 = _manhattan(start, goal)
        open_heap: list[tuple[int, int, Time, Pos]] = [(h0, h0, t, start)]
        parent: dict[State, State] = {}
        closed: set[State] = set()

        while open_heap:
            _, _, tau, pos = heapq.heappop(open_heap)
            state = (pos, tau)
            if state in closed:
                continue
            closed.add(state)

            if pos == goal and tau > goal_last:
                return self._reconstruct(parent, state, (start, t))

            nxt_tau = tau + 1
            for nxt in [*grid.neighbors(pos), pos]:
                h = _manhattan(nxt, goal)
                if nxt_tau + h > horizon:
                    continue
                child = (nxt, nxt_tau)
                if child in closed or (nxt, nxt_tau) in res:
                    continue
                if nxt != pos:
                    # Schimb de pozitii cu un alt robot pe aceeasi muchie.
                    other = res.get((nxt, tau))
                    if other is not None and res.get((pos, nxt_tau)) == other:
                        continue
                if child not in parent:
                    parent[child] = state
                    g = nxt_tau - t
                    heapq.heappush(open_heap, (g + h, h, nxt_tau, nxt))
        return []

    @staticmethod
    def _reconstruct(parent: dict[State, State], end: State, root: State) -> list[Pos]:
        path: list[Pos] = []
        cur = end
        while cur != root:
            path.append(cur[0])
            cur = parent[cur]
        path.reverse()
        return path
