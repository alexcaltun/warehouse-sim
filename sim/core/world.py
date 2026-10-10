"""Generare layout de depozit si task-uri aleatoare."""
from __future__ import annotations

import random

from sim.core.types import CellType, Grid, Pos, Task


def make_warehouse(rows: int = 30, cols: int = 30, block: int = 2, aisle: int = 1) -> Grid:
    """Rafturi in blocuri verticale separate de culoare. Coloana 0 = statii.
    Randurile de sus si de jos raman libere ca inel de circulatie."""
    cells: list[tuple[CellType, ...]] = []
    for r in range(rows):
        row: list[CellType] = []
        for c in range(cols):
            if c == 0:
                row.append(CellType.STATION)
            elif r in (0, rows - 1):
                row.append(CellType.FREE)
            elif (c - 1) % (block + aisle) < block:
                row.append(CellType.SHELF)
            else:
                row.append(CellType.FREE)
        cells.append(tuple(row))
    return Grid(rows=rows, cols=cols, cells=tuple(cells))


def free_cells(grid: Grid) -> list[Pos]:
    return [
        (r, c)
        for r in range(grid.rows)
        for c in range(grid.cols)
        if grid.passable((r, c))
    ]


def pickup_points(grid: Grid) -> list[Pos]:
    """Celule penetrabile adiacente unui raft - de acolo se preia marfa."""
    out: list[Pos] = []
    for p in free_cells(grid):
        r, c = p
        if grid.at(p) is CellType.STATION:
            continue  # statiile sunt destinatii, nu puncte de preluare
        for q in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if grid.in_bounds(q) and grid.at(q) is CellType.SHELF:
                out.append(p)
                break
    return out


def stations(grid: Grid) -> list[Pos]:
    return [(r, 0) for r in range(grid.rows) if grid.passable((r, 0))]


def random_tasks(grid: Grid, n: int, horizon: int, seed: int = 0) -> list[Task]:
    rng = random.Random(seed)
    picks, drops = pickup_points(grid), stations(grid)
    return [
        Task(
            id=f"task-{i:04d}",
            pickup=rng.choice(picks),
            dropoff=rng.choice(drops),
            released_at=rng.randint(0, horizon),
        )
        for i in range(n)
    ]
