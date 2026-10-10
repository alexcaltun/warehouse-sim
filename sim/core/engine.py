"""Bucla de simulare cu pasi discreti. Nu contine algoritmi: planner-ul si
allocator-ul vin din afara, prin constructor."""
from __future__ import annotations

from sim.core.types import Allocator, Grid, Metrics, Planner, Pos, Robot, Task, Time

DEADLOCK_TICKS = 50
PARK_HORIZON = 20
MAX_EVAC_TRIES = 8

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
        # Un robot oprit isi rezerva celula pe tot orizontul de cautare al planner-ului
        # (max_wait_steps + 4 * distanta), altfel altii planifica "prin el, dupa ce pleaca".
        self.park_horizon = max(
            PARK_HORIZON,
            getattr(planner, "max_wait_steps", 0) + 4 * (grid.rows + grid.cols),
        )

        self.t: Time = 0
        self.pending: list[Task] = []
        self.collisions = 0
        self.deadlocks = 0
        self.evacuations = 0
        self.reservations: dict[Key, str] = {}
        self._evacuating: set[str] = set()
        self._evacuated_tick: set[str] = set()
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
            max_wait=max(waits, default=0),
            avg_service=sum(services) / len(services) if services else 0.0,
            collisions=self.collisions,
            deadlocks=self.deadlocks,
            evacuations=self.evacuations,
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

        self._evacuated_tick = set()
        # Un robot in evacuare care tocmai a primit task renunta la evacuare.
        for rob in self.robots:
            if rob.id in self._evacuating and (rob.task_id is not None or not rob.path):
                self._evacuating.discard(rob.id)
                rob.path = []

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
            goal = self._goal(rob)
            if self._reachable(rob, goal, ignore=[]):
                path = self.planner.plan(self.grid, rob.pos, goal, self.reservations, t)
                if path:
                    self._set_path(rob, path, t)
                    continue
            # Evacuarea ajuta doar cand robotii liberi parcati taie accesul; daca tinta
            # e accesibila si totusi nu exista plan, cauza e alta (trafic, orizont).
            elif self._make_way(rob, self._relaxed_route(rob, goal, t), t):
                # Celula-problema s-a eliberat: robotul replanifica in acelasi tick.
                self._release(rob.id)
                self._reserve(rob.id, (rob.pos, t))
                queue.append(rob.id)
                continue
            failed.append(rob)
            if rob.carrying is None and rob.task_id is not None:
                # Renunta la task imediat, ca sa poata fi evacuat in acest tick.
                self._task_by_id[rob.task_id].assigned_to = None
                rob.task_id = None
            self._hold(rob, t, queue)
        return failed

    def _set_path(self, rob: Robot, path: list[Pos], t: Time) -> None:
        rob.path = list(path)
        for i, cell in enumerate(rob.path):
            self._reserve(rob.id, (cell, t + 1 + i))
        end = t + len(rob.path)
        for tau in range(end + 1, end + self.park_horizon + 1):
            self._reserve(rob.id, (rob.path[-1], tau))

    def _reachable(self, rob: Robot, goal: Pos, ignore: list[str]) -> bool:
        """Test ieftin inaintea planner-ului. Un robot parcat (oprit, sau la capatul
        drumului) isi tine celula pe tot orizontul planner-ului, deci celula lui e zid
        din momentul in care o ocupa. Daca tinta nu se poate atinge nici macar ignorand
        restul rezervarilor, planner-ul ar esua oricum, dupa o cautare completa."""
        t = self.t
        walls: dict[Pos, Time] = {}
        for r in self.robots:
            if r is rob or r.id in ignore:
                continue
            if r.path:
                cell, since = r.path[-1], t + len(r.path)
            elif self.reservations.get((r.pos, t + 1)) == r.id:
                cell, since = r.pos, t
            else:
                continue
            walls[cell] = min(walls.get(cell, since), since)
        if goal in walls:
            return False
        dist = {rob.pos: 0}
        frontier = [rob.pos]
        i = 0
        while i < len(frontier):
            cur = frontier[i]
            i += 1
            for nxt in self.grid.neighbors(cur):
                d = dist[cur] + 1
                if nxt in dist or walls.get(nxt, t + d + 1) <= t + d:
                    continue
                if nxt == goal:
                    return True
                dist[nxt] = d
                frontier.append(nxt)
        return False

    def _parked_idle(self) -> list[Robot]:
        """Roboti liberi, opriti, care pot fi inca evacuati in tick-ul curent."""
        return [
            rob
            for rob in self.robots
            if rob.task_id is None and not rob.path and rob.id not in self._evacuated_tick
        ]

    def _relaxed_route(self, rob: Robot, goal: Pos, t: Time) -> list[Pos]:
        """Drumul pe care l-ar avea robotul daca robotii liberi parcati n-ar exista."""
        parked = [r.id for r in self._parked_idle()]
        if not parked or not self._reachable(rob, goal, ignore=parked):
            return []
        relaxed = {k: v for k, v in self.reservations.items() if v not in parked}
        return self.planner.plan(self.grid, rob.pos, goal, relaxed, t)

    def _make_way(self, rob: Robot, route: list[Pos], t: Time) -> bool:
        """Evacueaza robotii liberi parcati pe `route`. True daca s-a mutat macar unul."""
        on_route = {cell: i for i, cell in reversed(list(enumerate(route)))}
        blockers = sorted(
            (r for r in self._parked_idle() if r.pos in on_route),
            key=lambda r: (on_route[r.pos], r.id),
        )
        if not blockers:
            return False
        # Cat timp se cauta celule de evacuare, robotul cu task ramane pe loc.
        temp = [
            (rob.pos, tau)
            for tau in range(t + 1, t + self.park_horizon + 1)
            if (rob.pos, tau) not in self.reservations
        ]
        for key in temp:
            self._reserve(rob.id, key)
        keep_clear = [*route, rob.pos]
        moved = False
        for blocker in blockers:
            self._evacuated_tick.add(blocker.id)
            if self._evacuate(blocker, keep_clear, t):
                moved = True
        if not moved:
            for key in temp:
                del self.reservations[key]
            self._owned[rob.id] = [k for k in self._owned[rob.id] if k not in temp]
        return moved

    def _evacuate(self, rob: Robot, keep_clear: list[Pos], t: Time) -> bool:
        self._release(rob.id)
        self._reserve(rob.id, (rob.pos, t))
        excluded = set(keep_clear)
        for tk in self.tasks:
            if tk.completed_at is None:
                excluded.add(tk.pickup)
                excluded.add(tk.dropoff)
        excluded.update(cell for (cell, _), owner in self.reservations.items() if owner != rob.id)

        stopped = [r.pos for r in self.robots if r is not rob and not r.path]
        tries = 0
        for cell in self._cells_by_distance(rob.pos, stopped):
            if cell in excluded:
                continue
            path = self.planner.plan(self.grid, rob.pos, cell, self.reservations, t)
            if path:
                self._set_path(rob, path, t)
                self._evacuating.add(rob.id)
                self.evacuations += 1
                return True
            tries += 1
            if tries >= MAX_EVAC_TRIES:
                break
        self._release(rob.id)
        for tau in range(t, t + self.park_horizon + 1):
            self._reserve(rob.id, (rob.pos, tau))
        return False

    def _cells_by_distance(self, start: Pos, blocked: list[Pos]) -> list[Pos]:
        """BFS care ocoleste robotii opriti; ordinea vecinilor e fixa, deci si rezultatul."""
        order = [start]
        seen = {start, *blocked}
        i = 0
        while i < len(order):
            for nxt in self.grid.neighbors(order[i]):
                if nxt not in seen:
                    seen.add(nxt)
                    order.append(nxt)
            i += 1
        return order[1:]

    def _hold(self, rob: Robot, t: Time, queue: list[str]) -> None:
        """Robot fara drum: rezerva celula curenta pe t..t+park_horizon. Un robot
        care si-a planificat trecerea prin celula asta pierde drumul si replanifica."""
        self._release(rob.id)
        for tau in range(t, t + self.park_horizon + 1):
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
