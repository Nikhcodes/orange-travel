# Ontwikkelaarshandleiding – Orange Travel

Voor iedereen in de groep die aan de code werkt. Je leest hier hoe je het project installeert, start en test, en hoe je data, foto's en het model aanpast.

---

## 1. Eenmalig installeren

### 1.1 Benodigdheden
- **Python 3.11 of nieuwer.** Het project is getest met 3.13; 3.14 werkt ook.
- **uv**, de pakketbeheerder die de opdracht vraagt (`pyproject.toml` + `uv.lock`).
- **VS Code** met de Python-extensie.

uv installeren:

| Systeem | Commando |
|---|---|
| Fedora | `sudo dnf install uv` |
| Ubuntu / overig Linux / macOS | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Windows (PowerShell) | `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` |

Controleer de installatie met `uv --version`.

### 1.2 Project klaarzetten

```bash
cd ~/Projects/orange-travel
uv sync
```

`uv sync` maakt de map `.venv` aan en installeert precies de versies uit `uv.lock`, inclusief pytest. Iedereen in de groep heeft daarna dezelfde omgeving.

### 1.3 VS Code
Open de map `orange-travel` (*File → Open Folder*). Druk op `Ctrl+Shift+P`, kies *Python: Select Interpreter* en dan `.venv`.

---

## 2. Dagelijks gebruik

| Wat | Commando |
|---|---|
| App starten | `uv run streamlit run app.py` |
| Alle tests | `uv run pytest` |
| Snelle tests (zonder tuning, ± 5 s) | `uv run pytest -k "not tuning and not never_above"` |
| Datasets controleren | `uv run python -m scripts.validate_datasets` |
| Gewichten opnieuw tunen | `uv run python -m scripts.tune_weights` |

Met `uv run` hoef je de virtuele omgeving niet eerst te activeren.

- Klantpagina: <http://localhost:8501>
- Beheervenster: <http://localhost:8501/beheer>

Stoppen doe je met `Ctrl+C` in de terminal.

### Zonder uv (alternatief met pip)

```fish
python3 -m venv .venv
source .venv/bin/activate.fish      # fish-shell
# source .venv/bin/activate         # bash/zsh
pip install -r requirements.txt
streamlit run app.py
```

> **Veelgemaakte fout:** zie je `streamlit: command not found`, of meldt pip iets over `~/.local/bin`, dan was je venv niet actief. Controleer het met `which python`: dat moet eindigen op `.venv/bin/python`.

---

## 3. Het beheervenster (`/beheer`)

Het wachtwoord staat standaard op `oranje2026`. Kies een eigen wachtwoord:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# open secrets.toml en pas admin_password aan
```

`secrets.toml` wordt niet gedeeld (staat in `.gitignore`).

### 3.1 Tabblad *Testen*
1. Kies **Ingebouwde testwensen** en dan *Testset*. Dat zijn de officiële cijfers voor het verslag.
2. Of kies **Tekst plakken** / **Bestand uploaden** en plak je eigen lijst. Elke indeling werkt: komma, puntkomma of tab, met Nederlandse of Engelse kolomnamen, en `$1.500` wordt als 1500 gelezen. Voorbeeld:

   ```
   budget;dagen;soort;gezelschap;verwacht
   1500;7;strand;stel;Solenta Eiland
   300;4;natuur;gezin;geen
   ```

   `geen`, `-` of een lege cel in *verwacht* betekent: er hoort géén advies uit te komen.
3. Je krijgt de succescriteria, de twee confusion matrices, precision/recall/F1, een score per type wens en een tabel met ✓/✗ per wens. Onderaan kun je de resultaten downloaden als CSV.

### 3.2 Tabblad *Bestemmingen*
- **Wijzigen:** klik in een cel, pas de waarde aan en klik op **Opslaan**.
- **Toevoegen:** typ in de lege rij onderaan. Laat `id` leeg, dan wordt het automatisch ingevuld.
- **Verwijderen:** selecteer de rij aan de linkerkant en druk op `Delete`.
- Bij elke opslag wordt eerst gecontroleerd (unieke namen, geldige soort, positieve prijs …) en wordt een **back-up** gemaakt in `data/backups/`.
- **Foto's:** kies een bestemming, upload een png/jpg/webp en klik op *Foto gebruiken*. Zonder foto toont de app een eigen illustratie. Gebruik alleen foto's die jullie zelf hebben gemaakt of mogen gebruiken, en geen foto van een echte plek bij een verzonnen bestemming.

> **Let op:** wijzig je prijzen of bestemmingen, dan kunnen de verwachte uitkomsten van de testwensen veranderen. De app waarschuwt dan en biedt aan om de testwensen opnieuw op te bouwen met de rubriek. Doe dit vóór je nieuwe cijfers rapporteert.

### 3.3 Tabblad *Onderzoek*
Klik op **Experimenten uitvoeren** (± 30 seconden). Je ziet dan de ablatie (onderzoeksvraag 1), Model A vs. B vs. het eindmodel (onderzoeksvraag 2), de 10 beste gewichten uit de tuning en een uitleg-voorbeeld (onderzoeksvraag 3).

---

## 4. Hoe de code in elkaar zit

```
klant ──► src/ui/client.py ──► src/recommendation_engine.py ──► src/preprocessing.py
                │                         │                            │
                │                 NearestNeighbors              get_dummies + StandardScaler
                │                 + budget/soort-filter          + gewichten (config.py)
                ▼
          src/i18n.py (NL / Sranan)   src/text_parser.py (vrije tekst)

team ──► src/ui/admin.py ──► src/evaluation.py, src/experiments.py, src/test_file.py
```

| Bestand | Verantwoordelijkheid |
|---|---|
| `src/config.py` | Alle constanten. **`FINAL_WEIGHTS`** = de getunede gewichten. |
| `src/data_loader.py` | CSV inlezen, `validate_destinations()` controleert alles. |
| `src/preprocessing.py` | `FeaturePreprocessor`: fit op bestemmingen, transformeert klant identiek. |
| `src/recommendation_engine.py` | `RecommendationEngine.recommend()`: afstanden → filters → top 3 → uitleg. |
| `src/rubric.py` | De geschreven regel voor de *verwachte beste* bestemming (los van het model). |
| `src/evaluation.py` | Succescriteria, confusion matrices, precision/recall/F1. |
| `src/experiments.py` | Tuning (alleen ontwikkelset), ablatie, Model A/B. |
| `src/ui/client.py` | Het gesprek met Lora en de resultaatkaarten. |
| `src/ui/admin.py` | Het beheervenster. |
| `src/ui/theme.py` | Kleuren, CSS en animaties. |
| `src/illustrations.py` | Genereert per bestemming een eigen SVG-poster. |

### Code-afspraken
- Code, functies en variabelen in het **Engels**; teksten voor de gebruiker in `src/i18n.py`.
- Nieuwe tekst voor de klant? Voeg de sleutel toe aan **zowel** `"nl"` als `"srn"`.
- Type hints en een docstring bij elke belangrijke functie.
- Geen if/else-advies: het advies komt altijd uit `RecommendationEngine`.
- Draai `uv run pytest` vóór je code deelt.

---

## 5. De tests

| Testbestand | Wat het bewijst |
|---|---|
| `test_recommendation_engine.py` | Nooit boven budget (1.008 combinaties × 2 modellen), altijd juiste soort, nooit een verzonnen of gemiste bestemming, geen featuremismatch, scaler alleen op bestemmingen gefit. |
| `test_evaluation.py` | Labels volgen de rubriek; `FINAL_WEIGHTS` is echt het tuningresultaat; succescriteria op de testset; confusion matrices tellen kloppend op. |
| `test_input.py` | Vrije tekst en rommelige testbestanden worden correct begrepen. |

Faalt `test_final_weights_are_the_tuning_result`? Dan zijn de data veranderd. Draai `uv run python -m scripts.tune_weights`, neem de gekozen gewichten over in `config.FINAL_WEIGHTS` en meld de nieuwe cijfers.

---

## 6. Data opnieuw opbouwen

```bash
uv run python -m scripts.build_test_scenarios   # 60 nieuwe testwensen (vaste seed, rubriek-labels)
uv run python -m scripts.tune_weights           # gewichten opnieuw kiezen op de ontwikkelset
uv run pytest
```

**Regel:** pas nooit labels aan nadat je de modelresultaten hebt gezien. Wil je de rubriek veranderen, verander dan eerst `src/rubric.py` en bouw daarna alles opnieuw op. Leg in het verslag uit waarom.

---

## 7. Delen via Teams

Deel een zip **zonder** `.venv/`, `__pycache__/`, `.pytest_cache/`, `data/backups/` en `.streamlit/secrets.toml`. De ontvanger draait dan zelf `uv sync`.

```bash
cd ..
zip -r orange-travel.zip orange-travel -x "*/.venv/*" "*/__pycache__/*" "*/.pytest_cache/*" "*/data/backups/*" "*/secrets.toml"
```

---

## 8. Problemen oplossen

| Probleem | Oplossing |
|---|---|
| `streamlit: command not found` | Gebruik `uv run streamlit run app.py`, of activeer eerst `.venv`. |
| `ModuleNotFoundError: src` | Start vanuit de projectmap (waar `app.py` staat). |
| App toont "reisgegevens konden niet worden geladen" | De CSV is ongeldig; de melding noemt de rij. Herstel via `data/backups/`. |
| Wachtwoord vergeten | Zie `.streamlit/secrets.toml`, of verwijder dat bestand (dan geldt `oranje2026`). |
| Poort 8501 bezet | `uv run streamlit run app.py --server.port 8502` |
