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
**Limitari cunoscute:** Planner-ul implementat analizează eficient mediul static, dar nu previne coliziunile între roboți și nu folosește în niciun fel tabela de rezervări (`reservations`). O verificare independentă pe 300 de perechi aleatoare într-un depozit 40x40 a confirmat că drumurile sunt optime, dar sunt valabile doar pentru un singur robot la un moment dat.
**Ramas nefacut:** Suportul real pentru parametrul `reservations` în cadrul calculelor, care momentan este doar declarat în semnătură. Suportul necesar integrării de prevenire a coliziunilor dinamice ar trebui adăugat și implementat într-un task viitor (probabil T-004).
**M-a blocat:** Comanda nativă `python` apela versiunea 3.9 pe mașina locală, astfel încât, pentru a respecta specificația Python 3.11+, am fost nevoit să utilizez direct `py -m pytest` ce instanțiază versiunea 3.12, după ce am instalat pachetul `pytest` inițial inexistent.
