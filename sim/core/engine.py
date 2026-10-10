"""Bucla de simulare cu pasi discreti. Nu contine algoritmi: planner-ul si
allocator-ul vin din afara, prin constructor."""
from __future__ import annotations

from sim.core.types import Allocator, Grid, Metrics, Planner, Pos, Robot, Task, Time

DEADLOCK_TICKS = 50


class Simulation:
    def __init__(
        self,
        grid: Grid,
        robots: list[Robot],
        tasks: list[Task],
        planner: Planner,
        allocator: Allocator,
        max_ticks: int = 10_000,
    ) -> None:
        self.grid = grid
        self.robots: list[Robot] = sorted(robots, key=lambda r: r.id)
        self.tasks: list[Task] = sorted(tasks, key=lambda tk: tk.id)
        self.planner = planner
        self.allocator = allocator
        self.max_ticks = max_ticks

        self.t: Time = 0
        self.pending: list[Task] = []
        self.collisions = 0
        self.deadlocks = 0
        self._task_by_id: dict[str, Task] = {tk.id: tk for tk in self.tasks}
        self._stall = 0
        self._stopped = False

    def step(self) -> None:
        t = self.t

        # 1. Task-uri eliberate si neasignate intra in coada.
        self.pending = [
            tk
            for tk in self.tasks
            if tk.released_at <= t and tk.assigned_to is None and tk.completed_at is None
        ]

        # 2. Alocare.
        self._allocate(t)

        # 3. Planificare pentru robotii cu task si fara drum.
        failed: list[Robot] = []
        for rob in self.robots:
            if rob.task_id is None or rob.path:
                continue
            task = self._task_by_id[rob.task_id]
            goal = task.pickup if rob.carrying is None else task.dropoff
            if rob.pos == goal:
                continue
            path = self.planner.plan(self.grid, rob.pos, goal, None, t)
            if path:
                rob.path = list(path)
            else:
                failed.append(rob)

        # 4. Fiecare robot avanseaza exact o celula.
        prev: dict[str, Pos] = {rob.id: rob.pos for rob in self.robots}
        for rob in self.robots:
            if not rob.path:
                continue
            nxt = rob.path.pop(0)
            if self._valid_move(rob.pos, nxt):
                rob.pos = nxt
            else:
                # Pas imposibil fizic (obstacol sau salt): robotul ramane pe loc
                # si replanifica la tick-ul urmator.
                rob.path = []

        # 5. Coliziuni: doar contorizate, nu rezolvate.
        self.collisions += self._count_collisions(prev)

        # 6. Preluare / livrare.
        for rob in self.robots:
            if rob.task_id is None:
                continue
            task = self._task_by_id[rob.task_id]
            if rob.carrying is None and rob.pos == task.pickup:
                rob.carrying = task.id
                task.picked_at = t
                rob.path = []
            elif rob.carrying == task.id and rob.pos == task.dropoff:
                rob.carrying = None
                task.completed_at = t
                rob.task_id = None
                rob.path = []

        # Dezasignare dupa plan esuat. Un task deja preluat ramane la robotul
        # care il cara, altfel marfa ar putea fi preluata a doua oara.
        for rob in failed:
            if rob.task_id is None or rob.carrying is not None:
                continue
            self._task_by_id[rob.task_id].assigned_to = None
            rob.task_id = None

        # Deadlock: nimeni nu s-a miscat desi exista munca eliberata.
        moved = any(rob.pos != prev[rob.id] for rob in self.robots)
        if moved or not self._has_released_work(t):
            self._stall = 0
        else:
            self._stall += 1
            if self._stall >= DEADLOCK_TICKS:
                self.deadlocks += 1
                self._stopped = True

        # 7.
        self.t += 1

    def run(self) -> Metrics:
        while not self._finished():
            self.step()
        return self.metrics()

    def metrics(self) -> Metrics:
        done = [tk for tk in self.tasks if tk.completed_at is not None]
        picked = [tk for tk in self.tasks if tk.picked_at is not None]
        waits = [tk.picked_at - tk.released_at for tk in picked if tk.picked_at is not None]
        services = [
            tk.completed_at - tk.picked_at
            for tk in done
            if tk.completed_at is not None and tk.picked_at is not None
        ]
        return Metrics(
            ticks=self.t,
            tasks_total=len(self.tasks),
            tasks_done=len(done),
            makespan=max((tk.completed_at for tk in done if tk.completed_at is not None), default=0),
            throughput=len(done) / max(self.t, 1),
            avg_wait=sum(waits) / len(waits) if waits else 0.0,
            avg_service=sum(services) / len(services) if services else 0.0,
            collisions=self.collisions,
            deadlocks=self.deadlocks,
        )

    def _finished(self) -> bool:
        if self._stopped or self.t >= self.max_ticks:
            return True
        return all(tk.completed_at is not None for tk in self.tasks)

    def _allocate(self, t: Time) -> None:
        free = [rob for rob in self.robots if rob.task_id is None]
        if not free or not self.pending:
            return
        result = self.allocator.assign(list(free), list(self.pending), self.grid, t)
        free_by_id = {rob.id: rob for rob in free}
        pending_ids = [tk.id for tk in self.pending]
        for robot_id, task_id in sorted(result.items()):
            rob = free_by_id.get(robot_id)
            if rob is None or rob.task_id is not None or task_id not in pending_ids:
                continue
            task = self._task_by_id[task_id]
            if task.assigned_to is not None:
                continue
            rob.task_id = task_id
            task.assigned_to = robot_id
        self.pending = [tk for tk in self.pending if tk.assigned_to is None]

    def _valid_move(self, src: Pos, dst: Pos) -> bool:
        dist = abs(src[0] - dst[0]) + abs(src[1] - dst[1])
        return dist <= 1 and self.grid.passable(dst)

    def _count_collisions(self, prev: dict[str, Pos]) -> int:
        count = 0
        n = len(self.robots)
        for i in range(n):
            a = self.robots[i]
            for j in range(i + 1, n):
                b = self.robots[j]
                same_cell = a.pos == b.pos
                swapped = (
                    a.pos != prev[a.id]
                    and a.pos == prev[b.id]
                    and b.pos == prev[a.id]
                )
                if same_cell or swapped:
                    count += 1
        return count

    def _has_released_work(self, t: Time) -> bool:
        return any(
            tk.released_at <= t and tk.completed_at is None for tk in self.tasks
        )
