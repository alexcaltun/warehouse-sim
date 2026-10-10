from __future__ import annotations

from sim.baseline import ManhattanPlanner, NearestAllocator
from sim.core.engine import Simulation
from sim.core.types import CellType, Grid, Pos, Robot, Task
from sim.core.world import make_warehouse, random_tasks, stations


def open_grid(rows: int, cols: int, walls: list[Pos] | None = None) -> Grid:
    blocked = walls or []
    cells = tuple(
        tuple(CellType.WALL if (r, c) in blocked else CellType.FREE for c in range(cols))
        for r in range(rows)
    )
    return Grid(rows=rows, cols=cols, cells=cells)


def make_sim(grid: Grid, robots: list[Robot], tasks: list[Task], **kw: int) -> Simulation:
    return Simulation(grid, robots, tasks, ManhattanPlanner(), NearestAllocator(), **kw)


def warehouse_sim(seed: int = 1) -> Simulation:
    grid = make_warehouse(20, 20)
    robots = [Robot(id=f"r{i:02d}", pos=p) for i, p in enumerate(stations(grid)[:10])]
    tasks = random_tasks(grid, 30, horizon=100, seed=seed)
    return make_sim(grid, robots, tasks, max_ticks=2_000)


def test_single_robot_single_task() -> None:
    robots = [Robot(id="r0", pos=(0, 0))]
    tasks = [Task(id="t0", pickup=(2, 3), dropoff=(4, 0), released_at=0)]
    m = make_sim(open_grid(5, 5), robots, tasks).run()
    assert m.tasks_done == 1
    assert m.tasks_total == 1
    assert m.makespan > 0
    assert m.collisions == 0
    assert m.deadlocks == 0
    assert tasks[0].picked_at == 4
    assert tasks[0].completed_at == 9
    assert m.avg_wait == 4.0
    assert m.avg_service == 5.0
    assert m.throughput == m.tasks_done / m.ticks
    assert robots[0].task_id is None and robots[0].carrying is None


def test_zero_tasks() -> None:
    m = make_sim(open_grid(5, 5), [Robot(id="r0", pos=(0, 0))], []).run()
    assert m.tasks_done == 0
    assert m.ticks == 0
    assert m.deadlocks == 0


def test_head_on_meet_in_same_cell() -> None:
    robots = [Robot(id="r0", pos=(2, 0)), Robot(id="r1", pos=(2, 4))]
    tasks = [
        Task(id="t0", pickup=(2, 0), dropoff=(2, 4), released_at=0),
        Task(id="t1", pickup=(2, 4), dropoff=(2, 0), released_at=0),
    ]
    m = make_sim(open_grid(5, 5), robots, tasks).run()
    assert m.collisions >= 1
    assert m.tasks_done == 2


def test_head_on_swap() -> None:
    robots = [Robot(id="r0", pos=(2, 0)), Robot(id="r1", pos=(2, 3))]
    tasks = [
        Task(id="t0", pickup=(2, 0), dropoff=(2, 3), released_at=0),
        Task(id="t1", pickup=(2, 3), dropoff=(2, 0), released_at=0),
    ]
    m = make_sim(open_grid(5, 5), robots, tasks).run()
    assert m.collisions >= 1


def test_double_run_identical() -> None:
    assert warehouse_sim(seed=7).run() == warehouse_sim(seed=7).run()


def test_robot_walled_in_deadlocks() -> None:
    walls = [(1, 2), (3, 2), (2, 1), (2, 3)]
    robots = [Robot(id="r0", pos=(2, 2))]
    tasks = [Task(id="t0", pickup=(0, 0), dropoff=(4, 4), released_at=0)]
    m = make_sim(open_grid(5, 5, walls), robots, tasks).run()
    assert m.deadlocks == 1
    assert m.tasks_done == 0
    assert robots[0].pos == (2, 2)
    assert m.ticks < 10_000


def test_waiting_for_release_is_not_deadlock() -> None:
    robots = [Robot(id="r0", pos=(0, 0))]
    tasks = [Task(id="t0", pickup=(0, 1), dropoff=(0, 2), released_at=200)]
    m = make_sim(open_grid(5, 5), robots, tasks).run()
    assert m.deadlocks == 0
    assert m.tasks_done == 1


def test_warehouse_runs() -> None:
    m = warehouse_sim().run()
    assert m.tasks_total == 30
    assert 0 <= m.tasks_done <= 30
    assert m.ticks > 0
