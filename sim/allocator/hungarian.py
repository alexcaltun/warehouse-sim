from __future__ import annotations

from sim.core.types import Grid, Robot, Task, Time


def _hungarian_min_cost(cost: list[list[int]]) -> list[int]:
    """Kuhn-Munkres (Hungarian algorithm) in O(n^3) for minimum cost assignment.
    cost is an n x n square matrix.
    Returns matching where matching[row] = col.
    """
    n = len(cost)
    inf = 10**18
    u = [0] * (n + 1)
    v = [0] * (n + 1)
    p = [0] * (n + 1)
    way = [0] * (n + 1)

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [inf] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = inf
            j1 = 0
            for j in range(1, n + 1):
                if not used[j]:
                    cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j
            for j in range(0, n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break

    ans = [-1] * n
    for j in range(1, n + 1):
        if p[j] != 0:
            ans[p[j] - 1] = j - 1
    return ans


class HungarianAllocator:
    name = "hungarian"

    def assign(
        self, robots: list[Robot], tasks: list[Task], grid: Grid, t: Time
    ) -> dict[str, str]:
        free_robs = sorted(
            [r for r in robots if r.task_id is None], key=lambda r: r.id
        )
        free_tsks = sorted(
            [tk for tk in tasks if tk.assigned_to is None and tk.completed_at is None],
            key=lambda tk: tk.id,
        )

        r_count = len(free_robs)
        c_count = len(free_tsks)
        if r_count == 0 or c_count == 0:
            return {}

        k = max(r_count, c_count)
        big_cost = 1_000_000_000

        # Create a square k x k cost matrix padded with a large constant
        cost = [[big_cost] * k for _ in range(k)]
        for i in range(r_count):
            rob_pos = free_robs[i].pos
            for j in range(c_count):
                pickup = free_tsks[j].pickup
                dist = abs(rob_pos[0] - pickup[0]) + abs(rob_pos[1] - pickup[1])
                cost[i][j] = dist

        matching = _hungarian_min_cost(cost)

        out: dict[str, str] = {}
        for i in range(r_count):
            j = matching[i]
            if j < c_count:
                out[free_robs[i].id] = free_tsks[j].id

        return out
