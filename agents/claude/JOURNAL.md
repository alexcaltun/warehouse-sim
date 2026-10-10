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

## T-004 — Evitarea coliziunilor: planificare prioritizata cu rezervari — 2026-10-10
**Fisiere atinse:**
- `sim/planner/prioritized.py` (nou)
- `sim/core/engine.py` (modificat)
- `tests/test_collisions.py` (nou)
- `agents/claude/JOURNAL.md` (acest jurnal)
- NU am atins `sim/core/types.py` (vezi "M-a blocat").

**Ce am implementat:**
Un planner nou care cauta drumul in spatiu si timp: stie unde vor fi ceilalti roboti la
fiecare tick si asteapta sau ocoleste ca sa nu intre peste ei si sa nu faca schimb de pozitii.
Fara rezervari se comporta exact ca A*. In engine, cu `use_reservations=True`, robotii isi
planifica drumul pe rand, dupa id, si fiecare isi trece imediat drumul in tabela, ca urmatorii
sa-l ocoleasca. Robotii care stau pe loc isi rezerva celula curenta. Cu `use_reservations=False`
(implicit) engine-ul se comporta exact ca inainte; testele din `test_engine.py` trec neschimbate.

**Decizii si de ce:**
- Pe tinta, robotul ramane parcat dupa sosire. Planner-ul accepta sosirea doar dupa ultima
  rezervare a altui robot pe celula-tinta, altfel parcarea de 20 de tick-uri s-ar suprapune
  peste drumul altcuiva. Spec-ul nu cerea explicit asta, dar fara ea apar coliziuni.
- Pe langa cheile drumului de la t+1 incolo, rezerv si `(pozitia curenta, t)`. Fara ea, un
  robot care planifica dupa in acelasi tick n-ar putea detecta schimbul de pozitii.
- Robotii care urmeaza sa planifice in tick-ul curent rezerva doar `(pozitie, t)`, nu 20 de
  tick-uri. Am incercat varianta conservatoare (rezerva si ei celula pe 20 de tick-uri):
  in coridorul de test robotii se blocau reciproc, fiecare asteptand ca celalalt sa plece.
- Evacuare: daca un robot care sta pe loc (liber, blocat sau la tinta) are nevoie de o celula
  pe care alt robot si-a planificat-o mai tarziu, robotul care sta castiga (nu poate disparea),
  iar celalalt isi pierde drumul si replanifica in acelasi tick. Fara asta coliziunile reapar
  cand rezervarea de 20 de tick-uri e reimprospatata. Bucla se termina: un robot esueaza cel
  mult o data pe tick, iar robotii fara drum nu sunt evacuati niciodata.
- Engine-ul tine o lista de chei per robot, ca stergerea rezervarilor sa nu parcurga toata
  tabela la fiecare replanificare.
- `base` e folosit doar cand rezervarile sunt `None`/goale. In engine tabela nu e niciodata
  goala (contine macar pozitia robotului), deci acolo ruleaza mereu A* spatiu-timp. Drumul
  are aceeasi lungime ca la A*, dar la egalitate poate alege alta varianta.
- Ordinea de departajare in heap e `(f, h, timp, pozitie)`, cum cere spec-ul. Ordinea
  actiunilor: vecinii din `grid.neighbors`, apoi asteptarea.
- Board vs spec: `agents/board.yaml` da pentru T-004 doar `prioritized.py` si
  `test_collisions.py`, dar spec-ul permite explicit si `engine.py`. Am urmat spec-ul (mai
  specific, iar partea B e imposibila fara engine). Board-ul pare neactualizat: si T-001
  apare inca "wip".
- Merge: la pornire worktree-ul era intr-un `git rebase` al lui `agent/claude` peste `main`,
  oprit pe conflict in acest jurnal. `main` continea deja toate fisierele mele, identice.
  Am pastrat versiunea din `main` si am terminat rebase-ul; commit-urile redundante au fost
  sarite. Branch-ul local a divergit fata de `origin/agent/claude`.

**Teste scrise:**
- `test_planner_without_reservations_matches_astar` — cu `None` si `{}` drumul e identic cu AStarPlanner pe depozit.
- `test_planner_without_base_finds_shortest_path` — fara base si fara rezervari gaseste drumul minim.
- `test_planner_waits_for_reserved_cell` — celula rezervata la t+1: robotul asteapta un tick (pozitie repetata).
- `test_planner_rejects_swap` — schimbul de pozitii cu acelasi robot e respins.
- `test_planner_follow_is_not_swap` — intrarea intr-o celula imediat dupa ce altul a plecat e permisa.
- `test_planner_gives_up_beyond_horizon` — tinta ocupata dincolo de orizont: lista vida.
- `test_planner_uses_absolute_time` — rezervarile se citesc relativ la `t` primit, nu de la 0.
- `test_engine_default_passes_no_reservations` — implicit planner-ul primeste mereu `None` si tabela ramane goala.
- `test_corridor_crossing_without_collision` — coridor de latime 1 cu nisa: 0 coliziuni, ambele task-uri livrate.
- `test_corridor_crossing_collides_without_reservations` — acelasi coridor fara rezervari: coliziuni >= 1.
- `test_corridor_makespan_cost_of_safety` — in coridor, makespan cu rezervari (9) >= fara (6).
- `test_warehouse_reservations_no_collisions` — depozit 20x20, 10 roboti, 30 task-uri, cu rezervari: 0 coliziuni.
- `test_warehouse_without_reservations_collides` — acelasi scenariu fara rezervari: 30/30 livrate, coliziuni > 0.
- `test_reservations_deterministic` — doua rulari cu rezervari dau `Metrics` egale.
- `test_warehouse_reservations_delivers_all` — XFAIL strict: tasks_done == 30 cu rezervari (vezi limitari).
- `test_warehouse_makespan_cost_of_safety` — XFAIL strict: comparatia de makespan pe depozit cere 30/30 in ambele rulari.
- `test_max_wait_at_least_avg_wait` — XFAIL strict (AttributeError): `Metrics.max_wait` nu exista.

**Rezultat pytest:**
`29 passed, 3 xfailed in 4.22s`

**Limitari cunoscute:**
- Cerinta din Definition of done "tasks_done == 30 cu use_reservations=True" NU e atinsa.
  Masurat pe 10 seed-uri (layout ca in demo, horizon 50, NearestAllocator):

  | | livrate | coliziuni | deadlock |
  |---|---|---|---|
  | A* fara rezervari | 30/30 la toate | 123-179 | 0 |
  | prioritized cu rezervari | 2-23 din 30 | 0 la toate | 1 la toate |

  Cauza: spec-ul cere ca robotii fara drum sa-si rezerve celula curenta si nu exista niciun
  mecanism care sa-i mute. Un robot liber ramane pe statia unde a livrat. Daca alt robot are
  de livrat exact acolo, nu ajunge niciodata. In `make_warehouse` toate culoarele (coloana
  statiilor, cele doua randuri-inel, culoarele dintre rafturi) au latime 1, deci un robot
  parcat inchide si drumul. Confirmat si pe un grid deschis 10x10: deadlock cu robotii liberi
  stand pe statiile-tinta ale celor care cara marfa.
- Comparatia de makespan pe depozit nu e valida cat timp rularea cu rezervari se opreste in
  deadlock (ex. seed 0: makespan 79 cu rezervari vs 147 fara, doar pentru ca a livrat 4 task-uri).
- Un plan esuat exploreaza tot orizontul (pana la ~170 de tick-uri x celule). Pe 20x20 o
  rulare cu deadlock dureaza 1-3 s; la 50 de roboti in T-005 poate deveni lent.
- Prioritatea e fixa (dupa id), deci robotii cu id mare asteapta sistematic mai mult.

**Ramas nefacut:**
- Partea C (`max_wait` in `Metrics`): blocata, vezi mai jos. Dupa ce se adauga campul in
  types.py, in `Simulation.metrics()` din engine.py trebuie adaugat, dupa `avg_wait=...`:
  `max_wait=max(waits, default=0),`
  si apoi scos marcajul xfail de pe `test_max_wait_at_least_avg_wait`.
- Un mecanism de eliberare pentru robotii liberi. Propuneri, de ales de Alex:
  1. robotul liber, cand e "in calea" unui plan esuat, primeste un drum scurt de evitare
     catre cea mai apropiata celula nerezervata;
  2. dupa livrare, robotul liber pleaca de pe statie spre o zona de parcare dedicata
     (necesita celule de parcare in `make_warehouse`, adica schimbare in world.py);
  3. un layout cu culoare de latime 2 sau o zona tampon langa statii, ca experimentul sa
     nu masoare in principal blocajele geometriei.
  Varianta 1 e cea mai locala (doar engine.py). Fiecare schimba rezultatele din lucrare,
  de aceea n-am ales eu.
- Dupa mecanism: scos xfail de pe `test_warehouse_reservations_delivers_all` si
  `test_warehouse_makespan_cost_of_safety`.
- Actualizarea `agents/board.yaml` (touches pentru T-004, statusuri) si `docs/ROADMAP.md`.

**M-a blocat:**
- `sim/core/types.py`: spec-ul permite adaugarea `max_wait`, dar `.claude/settings.json` are
  `deny: Edit(./sim/core/types.py)`, iar AGENTS.md interzice modificarea. N-am ocolit regula.
  Propunere exacta pentru types.py, in `Metrics`, dupa `avg_wait: float = 0.0`:
  `max_wait: Time = 0`
  Oprit aici pentru partea C pana decide Alex.
- Contradictie in spec: Definition of done cere 30/30 si 0 coliziuni, dar regula "robotii
  fara drum isi rezerva celula curenta", aplicata pe un layout cu culoare de latime 1, duce
  sistematic la deadlock. Am implementat regula literal si am marcat testele afectate xfail
  strict, in loc sa caut un seed norocos care sa treaca.

## T-006 — Eliberarea robotilor parcati (evacuare locala) — 2026-10-11
**Fisiere atinse:**
- `sim/core/engine.py` (modificat)
- `sim/core/types.py` (doar `Metrics.evacuations: int = 0`)
- `tests/test_collisions.py` (scos xfail, acceptanta parametrizata pe seed-urile 1, 3, 7)
- `tests/test_evacuation.py` (nou)
- `agents/claude/JOURNAL.md` (acest jurnal)
- `max_wait` era deja completat de Alex in `6900c9f`; n-a mai fost nimic de facut acolo.

**Ce am implementat:**
Cand un robot cu task nu gaseste drum pentru ca robotii liberi parcati ii taie accesul, engine-ul
calculeaza drumul pe care l-ar avea fara ei, iar robotii liberi de pe acel drum se dau la o parte
spre cea mai apropiata celula libera care nu incurca pe nimeni. Robotul cu task replanifica in
acelasi tick. Ca mecanismul sa functioneze, un robot oprit isi rezerva acum celula pe tot
orizontul planner-ului (nu doar 20 de tick-uri), iar un robot fara marfa al carui plan esueaza
renunta imediat la task. Evacuarile sunt numarate in `Metrics.evacuations`.

**Decizii si de ce:**
- Declansare: planul esueaza SI tinta e inaccesibila cand robotii parcati sunt considerati
  ziduri, dar accesibila fara robotii liberi. Blocantii sunt robotii liberi de pe drumul
  "relaxat" (planificat ignorand rezervarile lor). Daca tinta e accesibila si planul tot esueaza,
  cauza e traficul sau orizontul, iar evacuarea nu ajuta.
- Celula de evacuare: cea mai apropiata prin BFS care ocoleste robotii opriti; nerezervata de
  nimeni in viitor; nu e pickup/dropoff al unui task neterminat; nu e pe drumul robotului care
  cere trecere si nici celula lui ("se da la o parte" = iese de pe traseu). Se incearca maximum
  8 candidati (`MAX_EVAC_TRIES`), ca un esec sa nu coste prea mult.
- Cat timp se cauta evacuarea, robotul cu task isi tine celula; daca nu s-a mutat nimeni,
  rezervarile temporare se sterg.
- Abatere importanta fata de T-004: orizontul de parcare pentru robotii opriti si pentru capatul
  drumului nu mai e 20, ci `max_wait_steps + 4 * (rows + cols)` (168 pe 20x20), adica tot
  orizontul planner-ului. Cu 20, un robot gasea drumuri care asteptau 21+ tick-uri dupa un robot
  oprit; rezervarea acestuia se reimprospata, drumul era invalidat la fiecare tick, planul nu
  esua niciodata (deci evacuarea nu pornea), iar drumurile-fantoma blocau tintele altora.
  Masurat (cu evacuarea activa): cu 20 se livrau 6-27/30 si deadlock pe toate seed-urile 0-9;
  cu orizontul lung, 9/10 seed-uri complete.
  Formula citeste `max_wait_steps` din planner prin `getattr`, deci depinde de formula de orizont
  din PrioritizedPlanner.
- Robotul fara marfa al carui plan esueaza renunta la task imediat, nu la finalul tick-ului.
  Altfel NearestAllocator ii reda un task la fiecare tick, inainte de planificare, si robotul
  nu e niciodata "liber" (task_id None) cand s-ar putea evacua (observat pe seed 8).
  Efectul asupra metricilor e acelasi: task-ul revine oricum in coada la tick-ul urmator.
- Test rapid `_reachable` inainte de planner: BFS in care celula unui robot parcat e zid din
  momentul in care il ocupa. E o conditie necesara, deci nu schimba rezultatul planner-ului; doar
  sare peste cautari spatiu-timp care oricum ar esua. Timp pe rulare: de la 16-41 s la 1,3-4 s.
- Un robot in evacuare care primeste task renunta la evacuare si planifica spre task.
- `evacuations` numara robotii mutati efectiv, nu incercarile.
- Board: T-006 nu exista in `agents/board.yaml`; am urmat lista de fisiere din spec.

**Teste scrise:**
- `test_parked_robot_steps_aside_in_corridor` — coridor de latime 1 cu nisa: robotul liber intra in nisa, celalalt livreaza, 0 coliziuni.
- `test_parked_robot_without_reservations_never_moves` — acelasi coridor fara rezervari: 0 evacuari, robotul liber nu se misca, coliziuni >= 1.
- `test_parked_robot_leaves_dropoff_before_arrival` — robot liber pe dropoff-ul unui task activ: pleaca inainte de livrare, 0 coliziuni.
- `test_full_grid_without_evacuation_cell_terminates` — grid 1x3 plin: fara exceptii, 0 evacuari, se opreste prin detectia de deadlock.
- `test_evacuation_is_deterministic` — doua rulari pe depozit (seed 1) dau `Metrics` egale, cu evacuari > 0.
- `test_no_evacuations_without_reservations` — fara rezervari: 0 evacuari, 30/30, tabela de rezervari goala.
- `test_warehouse_reservations_delivers_all[1,3,7]` (fost xfail) — tasks_done == 30 si deadlocks == 0.
- `test_warehouse_reservations_no_collisions[1,3,7]` — collisions == 0.
- `test_warehouse_makespan_cost_of_safety[1,3,7]` (fost xfail) — ambele rulari 30/30, makespan cu rezervari >= fara.
- `test_warehouse_without_reservations_collides[1,3,7]` — fara rezervari: 30/30 si coliziuni > 0.

**Rezultat pytest:**
`61 passed in 12.66s`

**Limitari cunoscute:**
- Acceptanta (10 roboti, 30 task-uri, depozit 20x20):

  | seed | fara rezervari: livrate / makespan / coliziuni | cu rezervari: livrate / makespan / coliziuni / deadlock / evacuari |
  |---|---|---|
  | 1 | 30 / 160 / 168 | 30 / 258 / 0 / 0 / 21 |
  | 3 | 30 / 161 / 176 | 30 / 290 / 0 / 0 / 40 |
  | 7 | 30 / 163 / 175 | 30 / 339 / 0 / 0 / 45 |

  Costul sigurantei: makespan de 1,6-2,1 ori mai mare.
- Pe seed-urile 0-39 (acelasi scenariu): 35/40 reusesc complet; coliziuni 0 pe toate 40.
  Cele 5 esecuri, clasificate:
  - seed 0 si 10: orizontul planner-ului (`8 + 4 * distanta Manhattan`) e mai scurt decat drumul
    real. Exemplu: de la (9,3) la statia (9,0) Manhattan e 3, deci orizont 20, dar drumul ocolind
    rafturile are 21 de pasi. Robotul n-ar putea planifica nici singur in depozit. Problema e in
    `prioritized.py`, pe care T-006 nu il permite.
  - seed 16 si 37: robotul liber de pe tinta are iesiri doar pe traseul celui care cere trecere
    sau prin spatele altor roboti liberi. Ar trebui evacuare in lant.
  - seed 27: gridlock intre 6 roboti care cara marfa; mecanismul evacueaza doar roboti liberi.
- Rezultatele sunt sensibile la detalii de implementare: in timpul dezvoltarii seed 8 a trecut
  din 30/30 in 29/30 si inapoi. Cifra 35/40 descrie exact aceasta versiune.
- Prioritatea ramane fixa dupa id.
- Viteza masurata doar pe 20x20 cu 10 roboti (1,3-4 s pe rulare); la 50 de roboti (T-005) nu stiu.

**Ramas nefacut:**
- PrioritizedPlanner: orizont calculat din distanta reala (BFS pe grid static) in loc de
  Manhattan. Ar rezolva seed-urile 0 si 10.
- Evacuare in lant (un robot liber poate cere si el altor roboti liberi sa se mute).
- Solutie pentru gridlock intre roboti cu marfa (ex. prioritate dinamica, sau voie pentru un
  robot cu marfa sa se dea la o parte).
- `agents/board.yaml`: adaugat T-006 si actualizat statusurile.

**M-a blocat:**
Nimic blocant. Neclar in spec: (1) spec-ul spune ca singura cauza e robotul liber parcat; am gasit
inca doua cauze necesare (drumurile-fantoma din orizontul de 20 de tick-uri si momentul in care
allocator-ul redistribuie task-urile), rezolvate in engine. (2) "Celula nerezervata" si "celula-
problema" nu erau definite precis; interpretarile sunt la "Decizii".
