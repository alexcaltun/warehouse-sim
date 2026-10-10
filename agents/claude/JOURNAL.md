# Jurnal claude

## 2026-10-10 — T-001 engine de simulare

Fisiere: `sim/core/engine.py`, `tests/test_engine.py`. `pytest -q` -> 8 passed, zero warnings
(verificat si cu `-W error`). Nu am atins types.py, world.py, baseline.py.

### Mediu
- Python implicit pe masina e 3.9 si nu avea pytest. Am creat `.venv/` (gitignored) cu
  Python 3.12 si am instalat doar `pytest`, care e deja in `requirements.txt`.
  Rulare: `.venv/Scripts/python -m pytest -q`.

### Decizii luate (unde spec-ul lasa loc de interpretare)
1. **Mutari imposibile fizic.** Daca urmatorul pas din `path` e SHELF/WALL sau nu e
   adiacent, robotul ramane pe loc si `path` se goleste (replanifica la tick-ul urmator).
   Fara asta, ManhattanPlanner trece prin pereti si testul de deadlock nu are sens.
   Pasul pe aceeasi celula (asteptare) e permis — util pentru T-004.
2. **Robot deja pe tinta** (path gol, pos == tinta): nu se apeleaza planner-ul, altfel
   lista vida ar fi interpretata gresit ca "nu exista drum".
3. **Plan esuat cu marfa in brate:** task-ul NU se dezasigneaza (altfel alt robot l-ar
   prelua a doua oara si picked_at s-ar suprascrie). Robotul ramane pe loc si reincearca.
   Pentru task-uri nepreluate se aplica regula din spec (dezasignare la final de tick).
4. **Deadlock:** contorul de 50 de tick-uri avanseaza doar cand exista task-uri
   eliberate si necompletate. Altfel, roboti care asteapta un task cu `released_at`
   mare ar fi declarati in deadlock fals. Exista test pentru asta.
5. **Coliziuni:** contorizate per pereche per tick, literal ca in spec. Doi roboti
   care stau pe aceeasi celula N tick-uri dau N coliziuni.
   Schimbul de pozitii cere ca ambii sa se fi miscat.
6. **Metrici:**
   - `ticks` = numarul de tick-uri executate.
   - `makespan` = max(completed_at) (acelasi ceas ca released_at), 0 daca nimic livrat.
   - `avg_wait` = medie(picked_at - released_at) pe task-urile preluate.
   - `avg_service` = medie(completed_at - picked_at) pe task-urile livrate.
   Types.py nu are `assigned_at`, deci impartirea wait/service se face la preluare.
7. **Iesirea din allocator e validata:** robot necunoscut/ocupat, task inexistent in
   `pending` sau deja asignat -> intrarea e ignorata. Aplicata in ordinea robot_id.
8. Engine-ul **modifica obiectele Robot/Task primite** (nu face copii), ca apelantul sa
   poata inspecta starea dupa run. Pentru rulari repetate trebuie construite obiecte noi
   (asa face testul de determinism). De retinut pentru T-005.
9. Am adaugat metoda publica `metrics()` (folosita de `run()`), utila daca cineva
   foloseste `step()` direct.

### Observatii
- Pe `make_warehouse(20, 20)` cu 10 roboti si 30 task-uri, baseline-ul
  ManhattanPlanner + NearestAllocator livreaza 0 task-uri si intra in deadlock la ~100
  tick-uri: drumurile lui trec prin rafturi, iar engine-ul refuza pasii. E comportamentul
  asteptat pentru un baseline care ignora obstacolele; A* (T-002) ar trebui sa schimbe asta.

### Nefacut / blocaje
- Nimic blocant. `reservations` se trimite ca `None` planner-ului; integrarea cu
  reservation table e treaba T-004.
- Fisierul de jurnal nu e in `touches` pentru T-001, dar AGENTS.md cere explicit sa-l scriu.
