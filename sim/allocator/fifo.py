from __future__ import annotations

from sim.core.types import Grid, Robot, Task, Time


class FifoAllocator:
    name = "fifo"

    def assign(
        self, robots: list[Robot], tasks: list[Task], grid: Grid, t: Time
    ) -> dict[str, str]:
        free_robs = [r for r in robots if r.task_id is None]
        free_tsks = [
            tk for tk in tasks if tk.assigned_to is None and tk.completed_at is None
        ]

        if not free_robs or not free_tsks:
            return {}

        sorted_tsks = sorted(free_tsks, key=lambda tk: (tk.released_at, tk.id))
        avail_robs = list(free_robs)
        out: dict[str, str] = {}

        for tk in sorted_tsks:
            if not avail_robs:
                break
            pickup = tk.pickup
            best_rob = min(
                avail_robs,
                key=lambda r: (
                    abs(r.pos[0] - pickup[0]) + abs(r.pos[1] - pickup[1]),
                    r.id,
                ),
            )
            out[best_rob.id] = tk.id
            avail_robs.remove(best_rob)

        return out
