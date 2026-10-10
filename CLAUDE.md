NOTA: acest fisier e duplicat ca CLAUDE.md si GEMINI.md. Daca il modifici, modifica-le pe toate trei.

# Reguli pentru agenti

## Interdictii absolute
- NU faci `git push`. NU faci `git checkout` sau `git switch`. NU atingi branch-ul main.
- NU modifici `sim/core/types.py`. Contractele sunt fixe.
  Daca ai nevoie de alta interfata: scrii propunerea in `agents/<tine>/JOURNAL.md` si TE OPRESTI.
- NU modifici fisiere in afara listei `touches` din `agents/board.yaml` pentru task-ul tau.
- NU instalezi dependinte noi fara sa le ceri in JOURNAL.md.

## Cum lucrezi
1. Citesti `docs/specs/<TASK>.md` integral.
2. Implementezi DOAR task-ul cerut. Fara imbunatatiri necerute.
3. Scrii teste in `tests/`. Rulezi `pytest -q`. Nu te opresti pana nu trece.
4. Commit-uri mici. Mesaj: `<TASK>: ce ai facut`.
5. La final ADAUGI la finalul `agents/<tine>/JOURNAL.md` o intrare noua, FARA sa
   stergi intrarile anterioare. Formatul e obligatoriu, exact acest sablon:

   ## <TASK-ID> — <titlu> — <data YYYY-MM-DD>
   **Fisiere atinse:** lista exacta
   **Ce am implementat:** 3-6 randuri, in cuvinte simple, nu cod
   **Decizii si de ce:** fiecare alegere unde existau mai multe variante, cu motivul
   **Teste scrise:** numele fiecarui test si ce verifica, un rand fiecare
   **Rezultat pytest:** output-ul exact al `pytest -q` (ultima linie)
   **Limitari cunoscute:** ce NU acopera implementarea
   **Ramas nefacut:** ce ar trebui facut intr-un task viitor
   **M-a blocat:** ce a fost neclar in spec, sau "nimic"

   Daca fisierul e gol, incepi cu titlul `# Jurnal <tine>` si apoi prima intrare.

## Stil
- Python 3.11+, type hints obligatorii, fara librarii externe in `sim/` (doar stdlib).
- Determinism: fara iterare pe set-uri in logica de decizie. Sorteaza explicit.
- Comentarii doar unde codul nu se explica singur.
