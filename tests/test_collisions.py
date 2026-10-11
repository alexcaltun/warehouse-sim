from __future__ import annotations

from functools import cache

import pytest

from sim.baseline import NearestAllocator
from sim.core.engine import Simulation
from sim.core.types import CellType, Grid, Metrics, Pos, Robot, Task, Time
from sim.core.world import free_cells, make_warehouse, random_tasks
from sim.planner.astar import AStarPlanner
from sim.planner.prioritized import PrioritizedPlanner

Res = dict[tuple[Pos, Time], str]


def grid_from_free(rows: int, cols: int, free: list[Pos]) -> Grid:
    cells = tuple(
        tuple(CellType.FREE if (r, c) in free else CellType.WALL for c in range(cols))
        for r in range(rows)
    )
    return Grid(rows=rows, cols=cols, cells=cells)


def open_grid(rows: int, cols: int) -> Grid:
    return grid_from_free(rows, cols, [(r, c) for r in range(rows) for c in range(cols)])


def line(cols: int) -> Grid:
    return open_grid(1, cols)


def corridor() -> Grid:
    """Coridor de latime 1 pe randul 1, cu o singura nisa in (0, 4)."""
    return grid_from_free(3, 7, [(1, c) for c in range(7)] + [(0, 4)])


def run_corridor(use_reservations: bool) -> Metrics:
    robots = [Robot(id="r0", pos=(1, 0)), Robot(id="r1", pos=(1, 6))]
    tasks = [
        Task(id="t0", pickup=(1, 0), dropoff=(1, 6), released_at=0),
        Task(id="t1", pickup=(1, 6), dropoff=(1, 0), released_at=0),
    ]
    planner = PrioritizedPlanner(base=AStarPlanner())
    sim = Simulation(
        corridor(), robots, tasks, planner, NearestAllocator(), use_reservations=use_reservations
    )
    return sim.run()


ACCEPTANCE_SEEDS = [1, 3, 7]


def run_warehouse(use_reservations: bool, seed: int = 3) -> Metrics:
    grid = make_warehouse(20, 20)
    cells = free_cells(grid)
    robots = [Robot(id=f"r{i:02d}", pos=cells[i * 7 % len(cells)]) for i in range(10)]
    tasks = random_tasks(grid, 30, horizon=50, seed=seed)
    planner = PrioritizedPlanner(base=AStarPlanner()) if use_reservations else AStarPlanner()
    sim = Simulation(
        grid, robots, tasks, planner, NearestAllocator(),
        max_ticks=3_000, use_reservations=use_reservations,
    )
    return sim.run()


@cache
def warehouse_metrics(use_reservations: bool, seed: int = 3) -> Metrics:
    return run_warehouse(use_reservations, seed)


def respects(path: list[Pos], res: Res, t: Time) -> bool:
    return all((cell, t + 1 + i) not in res for i, cell in enumerate(path))


# --- PrioritizedPlanner ---------------------------------------------------


def test_planner_without_reservations_matches_astar() -> None:
    grid = make_warehouse(20, 20)
    base = AStarPlanner()
    planner = PrioritizedPlanner(base=base)
    cells = free_cells(grid)
    n = len(cells)
    for start, goal in [(cells[0], cells[-1]), (cells[10], cells[n // 2]), (cells[n // 3], cells[3])]:
        expected = base.plan(grid, start, goal)
        assert planner.plan(grid, start, goal, None) == expected
        assert planner.plan(grid, start, goal, {}) == expected


def test_planner_without_base_finds_shortest_path() -> None:
    path = PrioritizedPlanner().plan(open_grid(5, 5), (0, 0), (4, 3))
    assert len(path) == 7
    assert path[-1] == (4, 3)
    assert (0, 0) not in path


def test_planner_waits_for_reserved_cell() -> None:
    res: Res = {((0, 1), 1): "x"}
    path = PrioritizedPlanner().plan(line(4), (0, 0), (0, 3), res, 0)
    assert path == [(0, 0), (0, 1), (0, 2), (0, 3)]
    assert respects(path, res, 0)


def test_planner_rejects_swap() -> None:
    # x merge din (0,1) in (0,0) exact cand noi am vrea din (0,0) in (0,1).
    res: Res = {((0, 1), 0): "x", ((0, 0), 1): "x"}
    assert PrioritizedPlanner().plan(line(3), (0, 0), (0, 2), res, 0) == []


def test_planner_follow_is_not_swap() -> None:
    # x pleaca din (0,1) spre (0,2); intrarea noastra in (0,1) dupa el e permisa.
    res: Res = {((0, 1), 0): "x", ((0, 2), 1): "x", ((0, 3), 2): "x"}
    path = PrioritizedPlanner().plan(line(5), (0, 0), (0, 4), res, 0)
    assert path[:2] == [(0, 1), (0, 2)]
    assert respects(path, res, 0)


def test_planner_gives_up_beyond_horizon() -> None:
    res: Res = {((0, 2), tau): "x" for tau in range(100)}
    assert PrioritizedPlanner(max_wait_steps=8).plan(line(3), (0, 0), (0, 2), res, 0) == []


def test_planner_uses_absolute_time() -> None:
    res: Res = {((0, 1), 11): "x"}
    path = PrioritizedPlanner().plan(line(3), (0, 0), (0, 2), res, 10)
    assert path[0] == (0, 0)
    assert respects(path, res, 10)


# --- Engine cu rezervari ----------------------------------------------------


def test_engine_default_passes_no_reservations() -> None:
    seen: list[object] = []

    class Spy(AStarPlanner):
        def plan(self, grid, start, goal, reservations=None, t=0):  # type: ignore[override]
            seen.append(reservations)
            return super().plan(grid, start, goal, reservations, t)

    robots = [Robot(id="r0", pos=(0, 0))]
    tasks = [Task(id="t0", pickup=(2, 2), dropoff=(4, 0), released_at=0)]
    sim = Simulation(open_grid(5, 5), robots, tasks, Spy(), NearestAllocator())
    assert sim.run().tasks_done == 1
    assert seen and all(r is None for r in seen)
    assert sim.reservations == {}


def test_corridor_crossing_without_collision() -> None:
    m = run_corridor(use_reservations=True)
    assert m.collisions == 0
    assert m.tasks_done == 2
    assert m.deadlocks == 0


def test_corridor_crossing_collides_without_reservations() -> None:
    assert run_corridor(use_reservations=False).collisions >= 1


def test_corridor_makespan_cost_of_safety() -> None:
    with_res = run_corridor(use_reservations=True)
    without = run_corridor(use_reservations=False)
    assert with_res.tasks_done == without.tasks_done == 2
    assert with_res.makespan >= without.makespan


@pytest.mark.parametrize("seed", ACCEPTANCE_SEEDS)
def test_warehouse_reservations_no_collisions(seed: int) -> None:
    assert warehouse_metrics(True, seed).collisions == 0


@pytest.mark.parametrize("seed", ACCEPTANCE_SEEDS)
def test_warehouse_without_reservations_collides(seed: int) -> None:
    m = warehouse_metrics(False, seed)
    assert m.tasks_done == 30
    assert m.collisions > 0


def test_reservations_deterministic() -> None:
    assert run_warehouse(True) == warehouse_metrics(True)


@pytest.mark.parametrize("seed", ACCEPTANCE_SEEDS)
def test_warehouse_reservations_delivers_all(seed: int) -> None:
    m = warehouse_metrics(True, seed)
    assert m.tasks_done == 30
    assert m.deadlocks == 0


@pytest.mark.parametrize("seed", ACCEPTANCE_SEEDS)
def test_warehouse_makespan_cost_of_safety(seed: int) -> None:
    with_res, without = warehouse_metrics(True, seed), warehouse_metrics(False, seed)
    assert with_res.tasks_done == without.tasks_done == 30
    assert with_res.makespan >= without.makespan


def test_max_wait_at_least_avg_wait() -> None:
    for m in (run_corridor(True), warehouse_metrics(True), warehouse_metrics(False)):
        assert m.max_wait >= m.avg_wait  # type: ignore[attr-defined]
