from __future__ import annotations

from sim.baseline import NearestAllocator
from sim.core.engine import Simulation
from sim.core.types import CellType, Grid, Pos, Robot, Task
from sim.core.world import free_cells, make_warehouse, random_tasks
from sim.planner.astar import AStarPlanner
from sim.planner.prioritized import PrioritizedPlanner


def grid_from_free(rows: int, cols: int, free: list[Pos]) -> Grid:
    cells = tuple(
        tuple(CellType.FREE if (r, c) in free else CellType.WALL for c in range(cols))
        for r in range(rows)
    )
    return Grid(rows=rows, cols=cols, cells=cells)


def open_grid(rows: int, cols: int) -> Grid:
    return grid_from_free(rows, cols, [(r, c) for r in range(rows) for c in range(cols)])


def make_sim(
    grid: Grid, robots: list[Robot], tasks: list[Task], use_reservations: bool = True
) -> Simulation:
    planner = PrioritizedPlanner(base=AStarPlanner())
    return Simulation(
        grid, robots, tasks, planner, NearestAllocator(),
        max_ticks=500, use_reservations=use_reservations,
    )


def corridor_with_parked_robot(use_reservations: bool) -> tuple[Simulation, Robot]:
    """Coridor de latime 1 pe randul 1, cu nisa in (0, 3). Robotul liber sta in (1, 3)."""
    grid = grid_from_free(3, 7, [(1, c) for c in range(7)] + [(0, 3)])
    parked = Robot(id="r1", pos=(1, 3))
    robots = [Robot(id="r0", pos=(1, 0)), parked]
    tasks = [Task(id="t0", pickup=(1, 0), dropoff=(1, 6), released_at=0)]
    return make_sim(grid, robots, tasks, use_reservations), parked


def run_trace(sim: Simulation) -> list[dict[str, Pos]]:
    trace = [{r.id: r.pos for r in sim.robots}]
    while not sim._finished():
        sim.step()
        trace.append({r.id: r.pos for r in sim.robots})
    return trace


def warehouse_sim(seed: int, use_reservations: bool = True) -> Simulation:
    grid = make_warehouse(20, 20)
    cells = free_cells(grid)
    robots = [Robot(id=f"r{i:02d}", pos=cells[i * 7 % len(cells)]) for i in range(10)]
    tasks = random_tasks(grid, 30, horizon=50, seed=seed)
    planner = PrioritizedPlanner(base=AStarPlanner()) if use_reservations else AStarPlanner()
    return Simulation(
        grid, robots, tasks, planner, NearestAllocator(),
        max_ticks=3_000, use_reservations=use_reservations,
    )


def test_parked_robot_steps_aside_in_corridor() -> None:
    sim, parked = corridor_with_parked_robot(use_reservations=True)
    trace = run_trace(sim)
    m = sim.metrics()
    assert m.tasks_done == 1
    assert m.collisions == 0
    assert m.evacuations >= 1
    assert parked.pos == (0, 3)
    assert all(step["r0"] != step["r1"] for step in trace)


def test_parked_robot_without_reservations_never_moves() -> None:
    sim, parked = corridor_with_parked_robot(use_reservations=False)
    m = sim.run()
    assert m.evacuations == 0
    assert m.collisions >= 1
    assert parked.pos == (1, 3)


def test_parked_robot_leaves_dropoff_before_arrival() -> None:
    parked = Robot(id="r1", pos=(2, 4))
    robots = [Robot(id="r0", pos=(2, 0)), parked]
    task = Task(id="t0", pickup=(2, 1), dropoff=(2, 4), released_at=0)
    sim = make_sim(open_grid(5, 5), robots, [task])
    trace = run_trace(sim)
    m = sim.metrics()
    assert m.tasks_done == 1
    assert m.collisions == 0
    assert m.evacuations >= 1
    assert task.completed_at is not None
    left_at = next(i for i, step in enumerate(trace) if step["r1"] != (2, 4))
    # trace[i] e starea dupa tick-ul i-1; livrarea are loc in tick-ul completed_at.
    assert left_at - 1 < task.completed_at


def test_full_grid_without_evacuation_cell_terminates() -> None:
    robots = [Robot(id="r0", pos=(0, 0)), Robot(id="r1", pos=(0, 1)), Robot(id="r2", pos=(0, 2))]
    tasks = [Task(id="t0", pickup=(0, 2), dropoff=(0, 0), released_at=0)]
    sim = make_sim(open_grid(1, 3), robots, tasks)
    m = sim.run()
    assert m.evacuations == 0
    assert m.collisions == 0
    assert m.tasks_done == 0
    assert m.deadlocks == 1
    assert m.ticks < 500


def test_evacuation_is_deterministic() -> None:
    first, second = warehouse_sim(seed=1).run(), warehouse_sim(seed=1).run()
    assert first.evacuations > 0
    assert first == second


def test_no_evacuations_without_reservations() -> None:
    sim = warehouse_sim(seed=3, use_reservations=False)
    m = sim.run()
    assert m.evacuations == 0
    assert m.tasks_done == 30
    assert sim.reservations == {}
