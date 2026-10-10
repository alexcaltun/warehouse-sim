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
5. La final scrii in `agents/<tine>/JOURNAL.md`: decizii luate, ce ai lasat nefacut, ce te-a blocat.

## Stil
- Python 3.11+, type hints obligatorii, fara librarii externe in `sim/` (doar stdlib).
- Determinism: fara iterare pe set-uri in logica de decizie. Sorteaza explicit.
- Comentarii doar unde codul nu se explica singur.
