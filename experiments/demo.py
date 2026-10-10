"""Demo rapid: baseline vs A* pe acelasi depozit si aceleasi task-uri."""
from sim.core.world import make_warehouse, random_tasks, free_cells
from sim.core.engine import Simulation
from sim.baseline import ManhattanPlanner, NearestAllocator
from sim.planner.astar import AStarPlanner
from sim.core.types import Robot

N_ROBOTI = 10
N_TASKURI = 30

grid = make_warehouse(20, 20)
celule = free_cells(grid)

print(f"\nDepozit 20x20, {N_ROBOTI} roboti, {N_TASKURI} task-uri\n")
print(f"{'planner':<18} {'livrate':>9} {'ticks':>7} {'throughput':>11} {'asteptare':>10} {'coliziuni':>10} {'deadlock':>9}")
print("-" * 80)

for planner in (ManhattanPlanner(), AStarPlanner()):
    roboti = [Robot(id=f"r{i:02d}", pos=celule[i * 7 % len(celule)]) for i in range(N_ROBOTI)]
    taskuri = random_tasks(grid, N_TASKURI, horizon=50, seed=3)
    m = Simulation(grid, roboti, taskuri, planner, NearestAllocator(), max_ticks=3000).run()
    print(
        f"{planner.name:<18} {m.tasks_done:>4}/{m.tasks_total:<4} {m.ticks:>7} "
        f"{m.throughput:>11.3f} {m.avg_wait:>10.1f} {m.collisions:>10} {m.deadlocks:>9}"
    )
print()
