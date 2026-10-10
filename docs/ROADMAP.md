# ROADMAP — starea proiectului

Managerul (orice conversatie AI) citeste acest fisier primul.
Alex il actualizeaza dupa fiecare merge pe main.

## Tema
Comparatie sistematica a strategiilor de alocare a task-urilor si planificare
a drumurilor intr-un depozit multi-robot. Masor: throughput, makespan, timp
de asteptare, coliziuni, deadlock-uri, la densitate variabila de roboti (5-50).

## Agenti
- claude  -> VS Code, wt/claude, branch agent/claude -> engine, integrare, experimente
- agy     -> Antigravity IDE, wt/agy, branch agent/agy -> algoritmi izolati

## Stare
- [x] Fundatie: types.py, world.py, baseline.py
- [x] T-001 engine (claude)
- [x] T-002 A* (agy)
- [ ] T-003 alocatori Hungarian + FIFO (agy) — in lucru
- [ ] T-004 evitare coliziuni (claude) — in lucru
- [ ] T-005 sweep + grafice — blocat de T-003, T-004

## Rezultate masurate pana acum
20x20, 10 roboti, 30 task-uri, seed 3, NearestAllocator:
- manhattan-naive: 0/30 livrate, deadlock dupa 84 ticks
- astar: 30/30 livrate, 162 ticks, throughput 0.185, 176 coliziuni
A* verificat independent contra BFS pe 300 de perechi: drumuri optime, 0.6 ms pe 100x100.
ATENTIE: cifrele sunt o limita superioara - robotii inca trec unii prin altii pana la T-004.

## Decizii luate
- 2026-10-10: statiile excluse din pickup_points — altfel task-urile aveau
  pickup si dropoff ambele pe coloana 0, drumuri triviale care nu testeaza nimic.
