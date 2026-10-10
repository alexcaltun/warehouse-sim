"""Bucla de simulare cu pasi discreti. Nu contine algoritmi: planner-ul si
allocator-ul vin din afara, prin constructor."""
from __future__ import annotations

from sim.core.types import Allocator, Grid, Metrics, Planner, Pos, Robot, Task, Time

DEADLOCK_TICKS = 50
PARK_HORIZON = 20

Key = tuple[Pos, Time]


class Simulation:
    def __init__(
        self,
        grid: Grid,
        robots: list[Robot],
        tasks: list[Task],
        planner: Planner,
        allocator: Allocator,
        max_ticks: int = 10_000,
        use_reservations: bool = False,
    ) -> None:
        self.grid = grid
        self.robots: list[Robot] = sorted(robots, key=lambda r: r.id)
        self.tasks: list[Task] = sorted(tasks, key=lambda tk: tk.id)
        self.planner = planner
        self.allocator = allocator
        self.max_ticks = max_ticks
        self.use_reservations = use_reservations

        self.t: Time = 0
        self.pending: list[Task] = []
        self.collisions = 0
        self.deadlocks = 0
        self.reservations: dict[Key, str] = {}
        self._owned: dict[str, list[Key]] = {rob.id: [] for rob in self.robots}
        self._robot_by_id: dict[str, Robot] = {rob.id: rob for rob in self.robots}
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
        if self.use_reservations:
            failed = self._plan_with_reservations(t)
        else:
            for rob in self.robots:
                if rob.task_id is None or rob.path:
                    continue
                goal = self._goal(rob)
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

    def _goal(self, rob: Robot) -> Pos:
        task = self._task_by_id[rob.task_id or ""]
        return task.pickup if rob.carrying is None else task.dropoff

    def _needs_plan(self, rob: Robot) -> bool:
        return rob.task_id is not None and not rob.path and rob.pos != self._goal(rob)

    def _plan_with_reservations(self, t: Time) -> list[Robot]:
        self.reservations = {k: v for k, v in self.reservations.items() if k[1] >= t}
        for rid in sorted(self._owned):
            self._owned[rid] = [k for k in self._owned[rid] if k[1] >= t]

        queue: list[str] = []
        # Robotii care urmeaza sa planifice ocupa doar celula curenta, la momentul t,
        # ca vecinii sa le vada pozitia pentru verificarea schimbului de pozitii.
        for rob in self.robots:
            if self._needs_plan(rob):
                self._release(rob.id)
                self._reserve(rob.id, (rob.pos, t))
                queue.append(rob.id)
        for rob in self.robots:
            if not rob.path and rob.id not in queue:
                self._hold(rob, t, queue)

        failed: list[Robot] = []
        while queue:
            queue.sort()
            rob = self._robot_by_id[queue.pop(0)]
            if not self._needs_plan(rob):
                continue
            self._release(rob.id)
            self._reserve(rob.id, (rob.pos, t))
            path = self.planner.plan(self.grid, rob.pos, self._goal(rob), self.reservations, t)
            if path:
                rob.path = list(path)
                for i, cell in enumerate(rob.path):
                    self._reserve(rob.id, (cell, t + 1 + i))
                end = t + len(rob.path)
                for tau in range(end + 1, end + PARK_HORIZON + 1):
                    self._reserve(rob.id, (rob.path[-1], tau))
            else:
                failed.append(rob)
                self._hold(rob, t, queue)
        return failed

    def _hold(self, rob: Robot, t: Time, queue: list[str]) -> None:
        """Robot fara drum: rezerva celula curenta pe t..t+PARK_HORIZON. Un robot
        care si-a planificat trecerea prin celula asta pierde drumul si replanifica."""
        self._release(rob.id)
        for tau in range(t, t + PARK_HORIZON + 1):
            key = (rob.pos, tau)
            owner = self.reservations.get(key)
            if owner is not None and owner != rob.id:
                other = self._robot_by_id[owner]
                if not other.path:
                    continue  # doi roboti deja suprapusi; coliziunea s-a numarat
                self._evict(other, t, queue)
            self._reserve(rob.id, key)

    def _evict(self, rob: Robot, t: Time, queue: list[str]) -> None:
        rob.path = []
        self._release(rob.id)
        if self._needs_plan(rob):
            self._reserve(rob.id, (rob.pos, t))
            if rob.id not in queue:
                queue.append(rob.id)
        else:
            self._hold(rob, t, queue)

    def _reserve(self, rid: str, key: Key) -> None:
        if self.reservations.get(key, rid) != rid:
            return
        self.reservations[key] = rid
        self._owned[rid].append(key)

    def _release(self, rid: str) -> None:
        for key in self._owned[rid]:
            if self.reservations.get(key) == rid:
                del self.reservations[key]
        self._owned[rid] = []

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
