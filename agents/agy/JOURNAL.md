# Jurnal agy

## T-002 — A* pe grid cu obstacole statice — 2026-10-10
**Fisiere atinse:** `sim/planner/astar.py`, `tests/test_astar.py`
**Ce am implementat:** Algoritmul A* a fost implementat complet respectând interfața `Planner`. Acesta parcurge grid-ul pentru a găsi traseul cel mai scurt între punctele de plecare și destinație evitând obstacolele statice (cum ar fi `SHELF`). Găsește un drum valid, excluzând startul și incluzând destinația, și se oprește anticipat doar când atinge destinația (sau returnează o listă vidă dacă calea nu există).
**Decizii si de ce:**
- Coada de priorități folosește un format de elemente `(f, h, pos)`: Am ales această structură deoarece Python execută tie-breaking automat la nivel de tuplu, obținând astfel direct determinismul solicitat, evitând logici auxiliare manuale de ordine a inserării.
- Utilizarea `dict` pentru scoruri și `set` pentru vizite: În loc de o reprezentare internă matricială care necesita spațiu și inițializări excedentare, am ales structurile predefinite; o măsurătoare a demonstrat că rezolvarea pe 100x100 cu obstacole durează aproximativ 1 ms (ceea ce respectă confortabil pragul de < 50 ms).
- Selectarea coordonatelor de test: Din moment ce țintele amplasate direct pe `SHELF` nu generează vecini viabili (algoritmul ar eșua intenționat și corect pe ele), am fixat destinațiile explicite pe coloane deschise (`FREE`) în grid-ul `make_warehouse`.
**Teste scrise:**
- `test_astar_empty_grid_5x5`: Verifică traseul normal și lungimea corectă pe un grid fără obstacole.
- `test_astar_start_equals_goal`: Confirmă returnarea unei liste vide atunci când punctul de start este identic cu destinația.
- `test_astar_wall_with_breach`: Validează faptul că algoritmul găsește singura breșă disponibilă printr-un obstacol vertical lung.
- `test_astar_goal_surrounded`: Demonstrează returnarea drumului inexistent (listă vidă) atunci când ținta este înconjurată complet de rafturi.
- `test_astar_path_properties`: Garantează că fiecare punct din traseu este pasabil (ne-blocat) și cu distanță Manhattan de 1 față de pasul adiacent.
- `test_astar_vs_manhattan`: Certifică faptul că pe `make_warehouse` lungimea drumului ce ocolește rafturi este mai mare decât simpla distanță Manhattan directă.
- `test_astar_determinism`: Asigură constanța rezultatului, adică două apeluri consecutive identice generează liste perfect egale.
**Rezultat pytest:** 7 passed in 0.05s
**Limitari cunoscute:** Planner-ul implementat analizează eficient mediul static, dar nu previne coliziunile între roboți și nu folosește în niciun fel tabela de rezervări (`reservations`). O verificare independentă pe 300 de perechi aleatoare într-un depozit 40x40 a confirmat că drumurile sunt optime, dar pentru un singur robot la un moment dat.
**Ramas nefacut:** Suportul real pentru parametrul `reservations` în cadrul calculelor, care momentan este doar declarat în semnătură. Integrarea pentru evitarea de coliziuni (prioritized planning) se va face în T-004.
**M-a blocat:** Eroarea de sintaxă "unsupported operand type(s) for |" la testarea pe Python 3.9, care era provocată tocmai de lipsa directivei `from __future__ import annotations` (necesară la validarea de type hints noi sub 3.10) ca primă linie în fișierul `astar.py`.

## T-003 — Alocatori: Hungarian si FIFO — 2026-10-10
**Fisiere atinse:** `sim/allocator/hungarian.py`, `sim/allocator/fifo.py`, `tests/test_allocator.py`
**Ce am implementat:** Am implementat doi alocatori alternativi conform protocolului Allocator: HungarianAllocator si FifoAllocator. HungarianAllocator utilizeaza algoritmul Kuhn-Munkres pentru a minimiza global suma distantelor Manhattan dintre roboti si punctele de preluare ale task-urilor, gestionand matrici dreptunghiulare prin completare cu valori mari. FifoAllocator aloca prioritar cele mai vechi task-uri (dupa released_at) catre cel mai apropiat robot disponibil pentru a preveni infometarea.
**Decizii si de ce:**
- Kuhn-Munkres pur stdlib: am implementat algoritmul maghiar clasic cu potentiale in O(n^3) folosind exclusiv tipuri intregi pentru a elimina erorile de precizie in virgula mobila si fara dependinte externe.
- Matrice dreptunghiulara completata cu 10^9: am utilizat o constanta mare pentru a forta cuplarea cu prioritate a robotilor si task-urilor reale, eliminand cuplajele artificiale la final.
- Sortare determinista: atat in Hungarian cat si in FIFO, entitatile sunt sortate explicit dupa id (respectiv released_at si id), garantand reproductibilitatea fara iteratii peste set-uri.
**Teste scrise:**
- `test_empty_inputs`: verifica returnarea unui dictionar gol cand lista de roboti sau de task-uri este vida (pentru toti alocatorii).
- `test_no_duplicate_assignments`: asigura ca niciun robot si niciun task nu este alocat de mai multe ori in acelasi pas (pentru toti alocatorii).
- `test_rectangular_counts`: valideaza obtinerea a exact 3 perechi atat pentru 3 roboti cu 5 task-uri cat si pentru 5 roboti cu 3 task-uri (pentru toti alocatorii).
- `test_hungarian_beats_greedy`: testul central (2 roboti, 2 task-uri) demonstrand ca Hungarian obtine suma distantelor minima (9), strict mai mica decat algoritmul greedy NearestAllocator (11).
- `test_hungarian_determinism`: confirma ca doua apeluri succesive identice pe aceleasi date returneaza exact acelasi dictionar de asignari.
- `test_fifo_prioritizes_oldest_task`: verifica ca task-ul cu cel mai mic released_at (1) este asignat primului robot liber, ignorand task-uri mai apropiate dar mai noi.
- `test_simulation_warehouse`: ruleaza o simulare completa pe make_warehouse(20,20) cu AStarPlanner si 10 roboti / 30 task-uri pentru fiecare alocator, verificand ca toate cele 30 de task-uri sunt finalizate.
**Rezultat pytest:** 30 passed in 0.15s
**Limitari cunoscute:** HungarianAllocator optimizeaza suma distantelor la tick-ul curent in mod miop la pasul de asignare, fara a anticipa task-urile viitoare si fara a tine cont de traseele cu ocolisuri sau coliziuni de pe grid.
**Ramas nefacut:** Integrarea prioritizarii bazate pe rezervari spatio-temporale pentru evitarea coliziunilor intre roboti (T-004).
**M-a blocat:** nimic
