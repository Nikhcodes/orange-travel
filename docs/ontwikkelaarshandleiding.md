# Ontwikkelaarshandleiding

Voor iedereen in het team. Hier lees je hoe je het project installeert, start en test, en hoe je data, tekst en het model aanpast.

---

## 1. Eenmalig installeren

| Wat | Hoe |
|---|---|
| Git | Fedora: `sudo dnf install git` · Windows: [git-scm.com](https://git-scm.com) |
| uv | Fedora: `sudo dnf install uv` · overig Linux/macOS: `curl -LsSf https://astral.sh/uv/install.sh \| sh` · Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| VS Code | Met de Python-extensie |

```bash
git clone https://github.com/Nikhcodes/orange-travel.git
cd orange-travel
uv sync
```

`uv sync` maakt `.venv/` aan en installeert precies de versies uit `uv.lock`. In VS Code kies je daarna via `Ctrl+Shift+P` → *Python: Select Interpreter* de `.venv`.

> **Gebruik altijd `uv run …`.** Dan hoef je niets te activeren en installeer je nooit per ongeluk iets buiten het project. Werk je toch met `pip`, activeer dan eerst de venv. In **fish** is dat `source .venv/bin/activate.fish`, niet `activate`.

---

## 2. Starten

Gebruik twee terminals:

| Wat | Commando | Adres |
|---|---|---|
| Chatbot + demo | `uv run uvicorn src.api:app --reload` | <http://localhost:8000/demo> |
| Bladwijzer-demo | (zelfde server) | <http://localhost:8000/demo/bladwijzer> |
| API-documentatie | (zelfde server) | <http://localhost:8000/api/docs> |
| Teamdashboard | `uv run streamlit run dashboard.py` | <http://localhost:8501> |

Het dashboard heeft een wachtwoord, standaard `oranje2026`. Kies een eigen wachtwoord:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # en pas admin_password aan
```

---

## 3. Testen

```bash
uv run pytest                                   # alles (± 1 minuut, inclusief tuning)
uv run pytest -k "not tuning and not fr12_advice and not invents"   # snel (± 3 s)
uv run pytest tests/test_dialogue.py -v         # alleen de gesprekstests, met namen
uv run python -m scripts.validate_data          # controleer alle data en labels
```

Bij elke push en pull request draait GitHub dezelfde tests (zie het tabblad *Actions*). Een rood kruis betekent: niet mergen.

| Testbestand | Wat het bewijst |
|---|---|
| `test_recommendation.py` | Nooit advies boven budget (648 wensen × 3 modellen), geen verzonnen tours, FR-08/09/11/12 |
| `test_evaluation.py` | Labels volgen de rubriek, gewichten = tuningresultaat, succescriteria op de testset |
| `test_nlu.py` | Kwaliteit van het intentmodel, wensen herkennen, privacyfilter |
| `test_dialogue.py` | Per requirement een gespreksscenario (FR-01 t/m FR-19, PC-02) |
| `test_api.py` | API, widget, demo, CORS |

---

## 4. Veelvoorkomende aanpassingen

### Een zin van Sabi veranderen
Alle teksten staan in **`src/texts.py`**. Pas ze daar aan; de logica hoef je niet aan te raken.

### Een tour toevoegen of een prijs aanpassen
1. Via het dashboard → *Tours beheren* (wordt gecontroleerd, met back-up), of direct in `data/tours.csv`.
2. Vul altijd de bron-URL in. Bij `alleen/stel/gezin/vrienden` zet je in `bron_geschiktheid` of het van de site komt (`site: …`) of een eigen inschatting is (`teamindeling: …`).
3. Herstart de API-server.
4. Klopt `uv run python -m scripts.validate_data` niet meer? Draai dan:
   ```bash
   uv run python -m scripts.build_test_wishes   # testwensen + labels opnieuw (rubriek)
   uv run python -m scripts.tune_weights        # gewichten opnieuw kiezen
   ```
   Neem de gekozen gewichten over in `config.FINAL_WEIGHTS` en draai `uv run pytest`.

> **Regel:** pas nooit labels of de rubriek aan omdat het model ze mist. Verander je de rubriek, leg dan in het verslag uit waarom.

### Het intentmodel verbeteren
Voeg voorbeeldzinnen toe aan `data/intents.csv` (kolommen `tekst,intent`) en bekijk het effect in het dashboard → *Intentmodel*. Kijk vooral naar de lijst met fout geclassificeerde zinnen.

### Een kennisbank-antwoord toevoegen
Voeg een rij toe aan `data/knowledge_base.csv` met de kolommen `onderwerp, trefwoorden, antwoord, bron`. De bron **moet** een pagina op orangesuriname.com zijn; de tests controleren dat.

### Een foto bij een tour
Dashboard → *Tours beheren* → *Foto per tour*. De foto komt in `assets/tours/`. Gebruik alleen foto's waarvoor toestemming is.

---

## 5. Samenwerken met Git

Zie ook [CONTRIBUTING.md](../CONTRIBUTING.md). In het kort:

```bash
git switch main && git pull                 # altijd eerst bijwerken
git switch -c feature/korte-omschrijving    # eigen branch
# ... werken, testen ...
git add -A && git commit -m "Voeg FAQ over vervoer toe"
git push -u origin feature/korte-omschrijving
```

Maak daarna op GitHub een **Pull Request** en vraag een groepsgenoot om een review.

**Nooit committen:** `.venv/`, `.streamlit/secrets.toml` en `data/backups/`. Die staan al in `.gitignore`.

---

## 6. Problemen oplossen

| Probleem | Oplossing |
|---|---|
| `streamlit`/`uvicorn: command not found` | Gebruik `uv run …` |
| Projectmap wordt honderden GB | Kan niet door dit project: de code is ± 3 MB, `.venv` ± 650 MB en de uv-cache ± 700 MB. Zoek met `du -sh .[!.]* * \| sort -h` (Linux) of WinDirStat (Windows). Meestal zitten er zips-in-zips of meerdere kopieën in OneDrive. Weggooien en opnieuw `git clone` is veilig. |
| Sabi verschijnt niet op de demopagina | Draait de API? Kijk in de browserconsole (F12) naar fouten. |
| Bladwijzer werkt niet op orangesuriname.com | Sta "lokaal netwerk" toe in de browserprompt, of gebruik de demopagina. |
| `ModuleNotFoundError: src` | Start vanuit de projectmap. |
| Poort bezet | `--port 8001` (uvicorn) of `--server.port 8502` (streamlit) |
| Dashboard-wachtwoord vergeten | Kijk in `.streamlit/secrets.toml` of verwijder dat bestand (dan geldt `oranje2026`) |

---

## 7. Op een echte server zetten (optioneel)

De app werkt lokaal zonder extra diensten. Voor een online demo:

1. Zet de API op een host met Python, bijvoorbeeld een kleine VPS of Render, met het startcommando `uvicorn src.api:app --host 0.0.0.0 --port $PORT`.
2. Zet er HTTPS voor; dat is nodig om de widget op een https-site te laden.
3. Op de website komt één regel: `<script src="https://jouw-server/widget/sabi.js" defer></script>`.
4. Beperk in `src/api.py` de CORS-instelling `allow_origins` tot de echte domeinnaam.
