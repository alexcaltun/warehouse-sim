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
- [ ] T-001 engine (claude) — in lucru
- [ ] T-002 A* (agy) — in lucru
- [ ] T-003, T-004, T-005 — blocate

## Decizii luate
- 2026-10-10: statiile excluse din pickup_points — altfel task-urile aveau
  pickup si dropoff ambele pe coloana 0, drumuri triviale care nu testeaza nimic.
