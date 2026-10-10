# T-002: A* pe grid cu obstacole statice

## decizii luate
- Am implementat `AStarPlanner` respectând protocolul `Planner` din `sim/core/types.py`.
- Pentru determinism, am stocat elementele în coada de priorități (`heapq`) sub forma `(f, h, current)`. Întrucât `current` este un `tuple[int, int]`, Python face tie-breaking element cu element, asigurând exact ordinea dorită.
- Am utilizat `g_score: dict[Pos, int]` și `expanded: set[Pos]` pentru viteză. Testat pe 100x100 cu `make_warehouse`, rulează în ~1-2 ms, mult sub limita de 50ms.
- La implementarea testelor pentru grid-ul 30x30, am ales explicit ținte (goals) care sunt pe o coloană liberă (`FREE`), deoarece țintele de tip `SHELF` nu generează vecini pasabili și drumul este imposibil de atins (ceea ce e comportamentul corect).

## ce ai lasat nefacut
- Parametrul `reservations` este primit în semnătură dar ignorat total, exact cum a fost specificat, pregătind terenul pentru `T-004`.

## ce te-a blocat
- Am întâmpinat o problemă locală deoarece comanda `python` folosea Python 3.9, în timp ce specificația cerea 3.11+. Am rezolvat lansând testele cu `py -m pytest` (care a invocat Python 3.12).
- Pachetul `pytest` lipsea în mediul curent, așa că l-am instalat din `requirements.txt` înainte să rulez validările.
