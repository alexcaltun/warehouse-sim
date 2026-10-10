from __future__ import annotations

import pytest

from sim.allocator.fifo import FifoAllocator
from sim.allocator.hungarian import HungarianAllocator
from sim.baseline import NearestAllocator
from sim.core.engine import Simulation
from sim.core.types import CellType, Grid, Robot, Task
from sim.core.world import make_warehouse, random_tasks, stations
from sim.planner.astar import AStarPlanner

ALLOCATOR_CLASSES = [NearestAllocator, HungarianAllocator, FifoAllocator]


def make_test_grid(rows: int = 15, cols: int = 15) -> Grid:
    cells = tuple(tuple(CellType.FREE for _ in range(cols)) for _ in range(rows))
    return Grid(rows=rows, cols=cols, cells=cells)


@pytest.mark.parametrize("allocator_cls", ALLOCATOR_CLASSES)
def test_empty_inputs(allocator_cls) -> None:
    grid = make_test_grid()
    allocator = allocator_cls()
    robots = [Robot(id="r0", pos=(0, 0))]
    tasks = [Task(id="t0", pickup=(1, 1), dropoff=(2, 2), released_at=0)]

    assert allocator.assign([], tasks, grid, 0) == {}
    assert allocator.assign(robots, [], grid, 0) == {}
    assert allocator.assign([], [], grid, 0) == {}


@pytest.mark.parametrize("allocator_cls", ALLOCATOR_CLASSES)
def test_no_duplicate_assignments(allocator_cls) -> None:
    grid = make_test_grid()
    allocator = allocator_cls()
    robots = [Robot(id=f"r{i}", pos=(i, 0)) for i in range(5)]
    tasks = [
        Task(id=f"t{j}", pickup=(j, j), dropoff=(0, 0), released_at=0)
        for j in range(5)
    ]

    res = allocator.assign(robots, tasks, grid, 0)
    assigned_robots = list(res.keys())
    assigned_tasks = list(res.values())

    assert len(assigned_robots) == len(set(assigned_robots))
    assert len(assigned_tasks) == len(set(assigned_tasks))


@pytest.mark.parametrize("allocator_cls", ALLOCATOR_CLASSES)
def test_rectangular_counts(allocator_cls) -> None:
    grid = make_test_grid()
    allocator = allocator_cls()

    # 3 robots and 5 tasks => exactly 3 pairs
    r3 = [Robot(id=f"r{i}", pos=(i, 0)) for i in range(3)]
    t5 = [
        Task(id=f"t{j}", pickup=(j, 1), dropoff=(0, 0), released_at=0)
        for j in range(5)
    ]
    res_3_5 = allocator.assign(r3, t5, grid, 0)
    assert len(res_3_5) == 3

    # 5 robots and 3 tasks => exactly 3 pairs
    r5 = [Robot(id=f"r{i}", pos=(i, 0)) for i in range(5)]
    t3 = [
        Task(id=f"t{j}", pickup=(j, 1), dropoff=(0, 0), released_at=0)
        for j in range(3)
    ]
    res_5_3 = allocator.assign(r5, t3, grid, 0)
    assert len(res_5_3) == 3


def test_hungarian_beats_greedy() -> None:
    """Testul central: 2 roboti si 2 task-uri unde alegerea lacoma este strict

    mai proasta decat cea gasita de Hungarian (suma distantelor minima).
    """
    grid = make_test_grid(rows=1, cols=12)

    # r0 la (0, 2), r1 la (0, 10)
    # t0 la (0, 3), t1 la (0, 0)
    robots = [
        Robot(id="r0", pos=(0, 2)),
        Robot(id="r1", pos=(0, 10)),
    ]
    tasks = [
        Task(id="t0", pickup=(0, 3), dropoff=(0, 0), released_at=0),
        Task(id="t1", pickup=(0, 0), dropoff=(0, 0), released_at=0),
    ]

    # Distante Manhattan:
    # r0 -> t0: |2 - 3| = 1
    # r0 -> t1: |2 - 0| = 2
    # r1 -> t0: |10 - 3| = 7
    # r1 -> t1: |10 - 0| = 10
    #
    # NearestAllocator (greedy):
    # r0 ia cel mai apropiat task disponibil -> t0 (dist 1)
    # r1 este fortat sa ia t1 (dist 10)
    # Suma greedy = 1 + 10 = 11
    #
    # Hungarian (optim global):
    # r0 -> t1 (dist 2)
    # r1 -> t0 (dist 7)
    # Suma Hungarian = 2 + 7 = 9 (9 < 11)

    nearest = NearestAllocator()
    res_nearest = nearest.assign(robots, tasks, grid, 0)
    assert res_nearest == {"r0": "t0", "r1": "t1"}

    hungarian = HungarianAllocator()
    res_hungarian = hungarian.assign(robots, tasks, grid, 0)
    assert res_hungarian == {"r0": "t1", "r1": "t0"}

    def total_dist(mapping: dict[str, str]) -> int:
        rob_by_id = {r.id: r for r in robots}
        tsk_by_id = {tk.id: tk for tk in tasks}
        return sum(
            abs(rob_by_id[r_id].pos[0] - tsk_by_id[t_id].pickup[0])
            + abs(rob_by_id[r_id].pos[1] - tsk_by_id[t_id].pickup[1])
            for r_id, t_id in mapping.items()
        )

    sum_greedy = total_dist(res_nearest)
    sum_hungarian = total_dist(res_hungarian)

    assert sum_greedy == 11
    assert sum_hungarian == 9
    assert sum_hungarian < sum_greedy


def test_hungarian_determinism() -> None:
    grid = make_test_grid(20, 20)
    hungarian = HungarianAllocator()
    robots = [Robot(id=f"r{i}", pos=(i, 2)) for i in range(6)]
    tasks = [
        Task(id=f"t{i}", pickup=(2, i), dropoff=(0, 0), released_at=0)
        for i in range(6)
    ]

    res1 = hungarian.assign(robots, tasks, grid, 0)
    res2 = hungarian.assign(robots, tasks, grid, 0)
    assert res1 == res2


def test_fifo_prioritizes_oldest_task() -> None:
    """Cu 3 task-uri (released_at 5, 1, 3) si un robot, se aloca cel cu released_at 1."""
    grid = make_test_grid()
    fifo = FifoAllocator()

    # Robotul este cel mai aproape de t0 (dist 1), dar t1 este cel mai vechi
    robot = Robot(id="r0", pos=(0, 0))
    tasks = [
        Task(id="t0", pickup=(0, 1), dropoff=(0, 0), released_at=5),
        Task(id="t1", pickup=(0, 8), dropoff=(0, 0), released_at=1),
        Task(id="t2", pickup=(0, 4), dropoff=(0, 0), released_at=3),
    ]

    res = fifo.assign([robot], tasks, grid, 10)
    assert res == {"r0": "t1"}


@pytest.mark.parametrize("allocator_cls", ALLOCATOR_CLASSES)
def test_simulation_warehouse(allocator_cls) -> None:
    """make_warehouse(20, 20) cu AStarPlanner si 10 roboti / 30 task-uri => tasks_done == 30."""
    grid = make_warehouse(20, 20)
    robots = [Robot(id=f"r{i:02d}", pos=p) for i, p in enumerate(stations(grid)[:10])]
    tasks = random_tasks(grid, 30, horizon=100, seed=42)

    sim = Simulation(
        grid, robots, tasks, AStarPlanner(), allocator_cls(), max_ticks=5_000
    )
    metrics = sim.run()

    assert metrics.tasks_done == 30
    assert metrics.tasks_total == 30
