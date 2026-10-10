# Jurnal claude

## T-001 — Engine de simulare cu pasi discreti — 2026-10-10
**Fisiere atinse:**
- `sim/core/engine.py` (nou)
- `tests/test_engine.py` (nou)
- `agents/claude/JOURNAL.md` (acest jurnal)

**Ce am implementat:**
Clasa `Simulation` care ruleaza depozitul tick cu tick, in ordinea stricta din spec:
intrarea task-urilor in coada, alocare, planificare, o celula de mers pentru fiecare robot,
numararea coliziunilor, preluare/livrare. Algoritmii nu sunt in engine: planner-ul si
allocator-ul vin din constructor. `run()` merge pana se livreaza tot, pana la `max_ticks`
sau pana la deadlock (50 de tick-uri fara nicio miscare) si intoarce `Metrics` completate.
Robotii si task-urile sunt parcurse mereu sortate dupa id, deci rezultatul e determinist.

**Decizii si de ce:**
- Pas imposibil (raft, perete sau salt peste o celula): robotul ramane pe loc si drumul se
  goleste, ca sa fie recalculat la tick-ul urmator. Altfel ManhattanPlanner ar trece prin
  pereti si testul de deadlock n-ar avea sens. Pasul pe loc (asteptare) e permis, pentru T-004.
- Robot deja pe tinta: nu se apeleaza planner-ul. Lista vida intoarsa ar fi fost confundata
  cu "nu exista drum" si task-ul s-ar fi dezasignat degeaba.
- Plan esuat cand robotul cara deja marfa: task-ul ramane la el si reincearca. Daca l-as fi
  dezasignat, alt robot l-ar fi putut prelua a doua oara si `picked_at` s-ar fi suprascris.
  Pentru task-urile nepreluate se aplica regula din spec (dezasignare la final de tick).
- Deadlock: contorul de 50 de tick-uri creste doar cat timp exista task-uri eliberate si
  nelivrate. Altfel robotii care asteapta un task cu `released_at` mare ar fi declarati
  in deadlock fals.
- Coliziuni: numarate pe pereche, la fiecare tick, literal ca in spec. Doi roboti care stau
  10 tick-uri pe aceeasi celula dau 10 coliziuni. La schimbul de pozitii ambii trebuie sa
  se fi miscat.
- Metrici: `ticks` = tick-uri executate; `makespan` = cel mai mare `completed_at` (0 daca
  nu s-a livrat nimic); `avg_wait` = medie(`picked_at - released_at`); `avg_service` =
  medie(`completed_at - picked_at`). `Task` nu are `assigned_at`, deci impart la preluare.
- Raspunsul allocator-ului e validat: perechile cu robot ocupat/necunoscut sau task care nu
  e in coada sunt ignorate, ca un allocator gresit sa nu strice starea.
- Engine-ul modifica direct obiectele `Robot`/`Task` primite, fara copii, ca apelantul sa
  poata inspecta starea dupa rulare.
- Am adaugat metoda publica `metrics()` (folosita de `run()`), utila cand se apeleaza
  `step()` direct.
- Mediu: Python implicit pe masina e 3.9 si nu avea pytest. Am creat `.venv/` (gitignored)
  cu Python 3.12 si am instalat doar `pytest`, deja listat in `requirements.txt`.

**Teste scrise:**
- `test_single_robot_single_task` — grid 5x5 liber, 1 robot, 1 task: livrat, makespan > 0, timpii si mediile exacte.
- `test_zero_tasks` — fara task-uri: `run()` se termina imediat, 0 tick-uri, fara exceptii.
- `test_head_on_meet_in_same_cell` — doi roboti frontal care ajung in aceeasi celula: collisions >= 1.
- `test_head_on_swap` — doi roboti vecini care isi schimba pozitiile: collisions >= 1.
- `test_double_run_identical` — doua rulari pe aceeasi configuratie de depozit dau `Metrics` egale.
- `test_robot_walled_in_deadlocks` — robot inconjurat de WALL cu task activ: deadlocks == 1, nu s-a miscat.
- `test_waiting_for_release_is_not_deadlock` — robot care asteapta un task eliberat la t=200: fara deadlock, task livrat.
- `test_warehouse_runs` — `make_warehouse(20, 20)`, 10 roboti, 30 task-uri: ruleaza fara exceptii.

**Rezultat pytest:**
`8 passed in 0.08s`

**Limitari cunoscute:**
- Coliziunile doar se numara, nu se rezolva; robotii pot sta suprapusi.
- Planner-ul primeste `reservations=None`; engine-ul nu tine reservation table.
- Cu baseline-ul (ManhattanPlanner + NearestAllocator), pe `make_warehouse(20, 20)` se
  livreaza 0 task-uri si rularea se termina in deadlock pe la tick-ul 100: drumurile trec
  prin rafturi si engine-ul refuza pasii. E de asteptat pentru un planner care ignora obstacolele.
- Pentru rulari repetate trebuie construite obiecte `Robot`/`Task` noi, altfel a doua rulare
  porneste din starea finala a primei.
- Coliziunile intre roboti parcati pe aceeasi celula se aduna la fiecare tick, ceea ce poate
  umfla cifra pentru baseline.

**Ramas nefacut:**
- T-004: reservation table transmis planner-ului si rezolvarea coliziunilor.
- T-005: sweep-ul trebuie sa construiasca robotii si task-urile din nou la fiecare rulare.
- Actualizarea statusului T-001 in `agents/board.yaml` si `docs/ROADMAP.md` (nu sunt in `touches`).

**M-a blocat:**
Nimic blocant. Neclar in spec: daca engine-ul trebuie sa opreasca mutarile prin obstacole,
cum se impart `avg_wait`/`avg_service`, ce se intampla cu un task deja preluat cand planul
esueaza si daca asteptarea task-urilor neeliberate conteaza la deadlock. Am ales variantele
de mai sus.
