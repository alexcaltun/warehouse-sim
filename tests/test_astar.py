import pytest
from sim.core.types import Grid, CellType, Pos
from sim.core.world import make_warehouse
from sim.planner.astar import AStarPlanner, manhattan_distance

def make_empty_grid(r: int, c: int) -> Grid:
    cells = tuple(tuple([CellType.FREE] * c) for _ in range(r))
    return Grid(rows=r, cols=c, cells=cells)

def test_astar_empty_grid_5x5():
    grid = make_empty_grid(5, 5)
    planner = AStarPlanner()
    start = (0, 0)
    goal = (4, 4)
    path = planner.plan(grid, start, goal)
    
    assert len(path) == 8
    assert path[-1] == (4, 4)
    assert (0, 0) not in path

def test_astar_start_equals_goal():
    grid = make_empty_grid(5, 5)
    planner = AStarPlanner()
    assert planner.plan(grid, (2, 2), (2, 2)) == []

def test_astar_wall_with_breach():
    # 5x5 grid cu un perete vertical pe coloana 2, breasa la randul 3
    cells = []
    for r in range(5):
        row = []
        for c in range(5):
            if c == 2 and r != 3:
                row.append(CellType.SHELF)
            else:
                row.append(CellType.FREE)
        cells.append(tuple(row))
    grid = Grid(rows=5, cols=5, cells=tuple(cells))
    
    planner = AStarPlanner()
    path = planner.plan(grid, (0, 0), (0, 4))
    
    assert len(path) > 0
    assert path[-1] == (0, 4)
    assert (3, 2) in path # Must pass through the breach

def test_astar_goal_surrounded():
    cells = []
    for r in range(5):
        row = []
        for c in range(5):
            # Goal is at (2, 2), surrounded by SHELF
            if abs(r - 2) <= 1 and abs(c - 2) <= 1 and (r, c) != (2, 2):
                row.append(CellType.SHELF)
            else:
                row.append(CellType.FREE)
        cells.append(tuple(row))
    grid = Grid(rows=5, cols=5, cells=tuple(cells))
    
    planner = AStarPlanner()
    path = planner.plan(grid, (0, 0), (2, 2))
    assert path == []

def test_astar_path_properties():
    grid = make_warehouse(30, 30)
    planner = AStarPlanner()
    start = (1, 0)
    goal = (28, 27)
    
    path = planner.plan(grid, start, goal)
    assert len(path) > 0
    assert path[-1] == goal
    assert start not in path
    
    curr = start
    for p in path:
        assert grid.passable(p)
        assert manhattan_distance(curr, p) == 1
        curr = p

def test_astar_vs_manhattan():
    grid = make_warehouse(30, 30)
    planner = AStarPlanner()
    
    start = (15, 0)
    goal = (15, 21)
    
    path = planner.plan(grid, start, goal)
    assert len(path) > 0
    
    manhattan_len = manhattan_distance(start, goal)
    assert len(path) > manhattan_len

def test_astar_determinism():
    grid = make_warehouse(30, 30)
    planner = AStarPlanner()
    start = (2, 0)
    goal = (25, 25)
    
    path1 = planner.plan(grid, start, goal)
    path2 = planner.plan(grid, start, goal)
    assert path1 == path2
