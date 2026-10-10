"""Contracte fixe. Nimic de aici nu se modifica fara decizie explicita."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

Pos = tuple[int, int]   # (rand, coloana)
Time = int              # tick discret


class CellType(Enum):
    FREE = 0
    SHELF = 1      # raft: impenetrabil
    STATION = 2    # statie de livrare: penetrabil
    WALL = 4


@dataclass(frozen=True)
class Grid:
    rows: int
    cols: int
    cells: tuple[tuple[CellType, ...], ...]

    def at(self, p: Pos) -> CellType:
        return self.cells[p[0]][p[1]]

    def in_bounds(self, p: Pos) -> bool:
        return 0 <= p[0] < self.rows and 0 <= p[1] < self.cols

    def passable(self, p: Pos) -> bool:
        return self.in_bounds(p) and self.at(p) not in (CellType.SHELF, CellType.WALL)

    def neighbors(self, p: Pos) -> list[Pos]:
        """Vecini in 4 directii, doar cei penetrabili. Ordine fixa = determinism."""
        r, c = p
        cand = [(r - 1, c), (r, c - 1), (r, c + 1), (r + 1, c)]
        return [q for q in cand if self.passable(q)]


@dataclass
class Task:
    id: str
    pickup: Pos
    dropoff: Pos
    released_at: Time
    assigned_to: str | None = None
    picked_at: Time | None = None
    completed_at: Time | None = None


@dataclass
class Robot:
    id: str
    pos: Pos
    path: list[Pos] = field(default_factory=list)   # pasi ramasi, EXCLUDE pozitia curenta
    carrying: str | None = None
    task_id: str | None = None


class Planner(Protocol):
    """Calculeaza drumul unui robot. Rezultatul EXCLUDE pozitia de start."""

    name: str

    def plan(
        self,
        grid: Grid,
        start: Pos,
        goal: Pos,
        reservations: dict[tuple[Pos, Time], str] | None = None,
        t: Time = 0,
    ) -> list[Pos]:
        """Lista vida = nu exista drum."""
        ...


class Allocator(Protocol):
    """Decide care robot ia care task."""

    name: str

    def assign(
        self, robots: list[Robot], tasks: list[Task], grid: Grid, t: Time
    ) -> dict[str, str]:
        """{robot_id: task_id}. Doar roboti liberi si task-uri neasignate."""
        ...


@dataclass
class Metrics:
    ticks: Time = 0
    tasks_total: int = 0
    tasks_done: int = 0
    makespan: Time = 0
    throughput: float = 0.0
    avg_wait: float = 0.0
    max_wait: Time = 0
    avg_service: float = 0.0
    collisions: int = 0
    deadlocks: int = 0

    def as_row(self) -> dict[str, float]:
        return {k: float(v) for k, v in self.__dict__.items()}
