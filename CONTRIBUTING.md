# Samenwerken aan Sabi

## Werkwijze
1. **Werk nooit direct op `main`.** Maak een branch: `git switch -c feature/korte-naam` (of `fix/…`, `docs/…`).
2. **Kleine commits** met een duidelijke boodschap in de gebiedende wijs: *"Voeg FAQ over vervoer toe"*.
3. **Draai de tests** vóór je pusht: `uv run pytest`.
4. **Open een Pull Request** naar `main` en vraag minstens één groepsgenoot om een review.
5. Mergen mag pas als de **Tests**-check groen is.

## Afspraken
- Code, functies en variabelen in het **Engels**; teksten voor de klant in het **Nederlands**, in `src/texts.py`.
- Nieuwe functionaliteit krijgt een test. Hoort het bij een requirement, zet het FR-nummer dan in de testnaam.
- Elk feit dat Sabi noemt komt uit `data/` en heeft een bronlink naar orangesuriname.com.
- Geen persoonsgegevens in code, data, issues of commits.
- Pas labels in `data/test_wishes.csv` nooit met de hand aan; gebruik `scripts/build_test_wishes.py`.

## Nieuwe afhankelijkheid nodig?
```bash
uv add pakketnaam          # of: uv add --dev pakketnaam
```
Commit daarna `pyproject.toml` én `uv.lock`.
