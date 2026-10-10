from __future__ import annotations
import heapq
from sim.core.types import Grid, Pos, Time

def manhattan_distance(a: Pos, b: Pos) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

class AStarPlanner:
    name = "astar"

    def plan(
        self,
        grid: Grid,
        start: Pos,
        goal: Pos,
        reservations: dict[tuple[Pos, Time], str] | None = None,
        t: Time = 0,
    ) -> list[Pos]:
        if start == goal:
            return []
            
        h_start = manhattan_distance(start, goal)
        # Heap elements are: (f_score, h_score, pos)
        open_set: list[tuple[int, int, Pos]] = []
        heapq.heappush(open_set, (h_start, h_start, start))
        
        came_from: dict[Pos, Pos] = {}
        g_score: dict[Pos, int] = {start: 0}
        expanded: set[Pos] = set()
        
        while open_set:
            f, h, current = heapq.heappop(open_set)
            
            if current in expanded:
                continue
            expanded.add(current)
            
            if current == goal:
                path = []
                curr = goal
                while curr != start:
                    path.append(curr)
                    curr = came_from[curr]
                path.reverse()
                return path
                
            curr_g = g_score[current]
            
            for neighbor in grid.neighbors(current):
                tentative_g = curr_g + 1
                if tentative_g < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    h_neighbor = manhattan_distance(neighbor, goal)
                    f_neighbor = tentative_g + h_neighbor
                    heapq.heappush(open_set, (f_neighbor, h_neighbor, neighbor))
                    
        return []
