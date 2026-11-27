# Orange Travel – Intelligent Travel Advisor

Een reisadvies-chatbot voor het fictieve reisbureau **Orange Travel Suriname**. De klant beantwoordt vier vragen aan **Lora**, de oranje lovebird: soort reis, reisgezelschap, aantal dagen en budget. Daarna krijgt de klant maximaal drie passende bestemmingen, elk met prijs en uitleg. Het advies wordt gemaakt met **K-Nearest Neighbors** (scikit-learn).

> **Studieproject (UNASAT, beroepsproduct SH1123AS).** Alle bestemmingen, prijzen en klantwensen zijn verzonnen. Dit is geen product van, en geen uitspraak over, het echte Orange Travel.

---

## Wat kan de app?

**Voor de klant** (`http://localhost:8501`)
- Een kort gesprek met Lora: kies met knoppen, of typ je wens in één zin (*"strand met mijn vriendin, 7 dagen, $1500"*).
- Budget per persoon óf voor de hele groep. De app rekent het om.
- Maximaal 3 reizen met foto of illustratie, prijs per persoon en voor de groep, en labels: *Meest aanbevolen*, *Voordeligst* en *Langst genieten*.
- **Nooit** een reis boven het budget. Past er niets, dan zegt Lora dat en noemt ze de goedkoopste reis alleen ter informatie.
- Nederlands en Sranan Tongo.

**Voor het projectteam** (`http://localhost:8501/beheer`, met wachtwoord)
- **Testen**: plak of upload een testbestand. Kolommen en scheidingsteken worden automatisch herkend. Je krijgt alle metrics, twee confusion matrices en een tabel per wens.
- **Bestemmingen**: bestemmingen, prijzen en beschrijvingen aanpassen en foto's uploaden.
- **Onderzoek**: de drie onderzoeksvragen met echte metingen.
- **Uitleg model**: KNN, schalen en one-hot encoding uitgelegd met live rekenvoorbeelden.

## Snel starten

Je hebt [uv](https://docs.astral.sh/uv/) nodig. Op Fedora: `sudo dnf install uv`.

```bash
uv sync                          # maakt .venv en installeert exact de versies uit uv.lock
uv run streamlit run app.py      # start de app
uv run pytest                    # alle tests (± 1 minuut)
```

Uitgebreide installatie-instructies, ook voor pip en de fish-shell, staan in [`docs/ontwikkelaarshandleiding.md`](docs/ontwikkelaarshandleiding.md).

## Resultaten (testset, 30 wensen die niet voor tuning zijn gebruikt)

| Succescriterium | Eis | Resultaat |
|---|---|---|
| Aanbevelingen binnen budget | 100% | **100%** |
| Soort reis klopt | ≥ 90% | **100%** (hard filter) |
| Vooraf bepaalde beste bestemming in top 3 | ≥ 24/30 | **30/30** |
| Extra: beste bestemming op plek 1 | – | 30/30 |
| Precision / recall / F1 (relevantie) | – | 0,78 / 0,94 / 0,86 |

Hoe deze cijfers tot stand komen en waarom ze niet "te mooi" zijn, staat in de [technische documentatie](docs/technische_documentatie.md#7-evaluatie).

## Mappenstructuur

```
orange-travel/
├── app.py                      # start de app: klantpagina + /beheer
├── pyproject.toml, uv.lock     # dependencies (reproduceerbaar met uv)
├── requirements.txt            # alternatief voor pip
├── data/
│   ├── destinations.csv        # 45 fictieve bestemmingen
│   └── test_customers.csv      # 60 testwensen: 30 ontwikkel + 30 test
├── src/
│   ├── config.py               # paden, kolomnamen, getunede gewichten
│   ├── data_loader.py          # CSV inlezen en valideren
│   ├── preprocessing.py        # one-hot (get_dummies) + StandardScaler + gewichten
│   ├── recommendation_engine.py# NearestNeighbors, budgetfilter, top 3, uitleg
│   ├── rubric.py               # de geschreven rubriek voor de verwachte uitkomst
│   ├── evaluation.py           # metrics + confusion matrices
│   ├── experiments.py          # tuning en onderzoeksvragen
│   ├── text_parser.py          # vrije tekst van de klant begrijpen
│   ├── test_file.py            # testbestanden automatisch herkennen
│   ├── illustrations.py        # eigen reisposter-illustraties (SVG)
│   ├── i18n.py                 # Nederlands en Sranan Tongo
│   └── ui/                     # client.py, admin.py, theme.py, media.py, model_info.py
├── scripts/                    # validate_datasets, build_test_scenarios, tune_weights
├── tests/                      # pytest
├── assets/                     # logo, lovebird, geüploade foto's
└── docs/                       # handleidingen en documentatie
```

## Documentatie

| Document | Voor wie |
|---|---|
| [`docs/klanthandleiding.pdf`](docs/klanthandleiding.pdf) / [`.md`](docs/klanthandleiding.md) | Klanten en medewerkers van het reisbureau |
| [`docs/ontwikkelaarshandleiding.md`](docs/ontwikkelaarshandleiding.md) | Groepsleden: installeren, testen, data aanpassen |
| [`docs/technische_documentatie.md`](docs/technische_documentatie.md) | Verslag en verdediging: hoe en waarom alles werkt |
| [`docs/presentatiegids.md`](docs/presentatiegids.md) | Taakverdeling, demoscript en vragen van de docent |

## Bekende beperkingen

- Kleine, verzonnen dataset (45 bestemmingen). Met weinig data herhalen aanbevelingen zich snel.
- Vier kenmerken; er is geen informatie over seizoen, activiteiten of beoordelingen.
- Geen echte prijzen, vluchten, visum of beschikbaarheid. Die vallen volgens de opdracht buiten de scope.
- De verwachte uitkomsten komen uit onze eigen rubriek. Een hoge score betekent dat het model ónze afwegingen volgt, niet dat echte klanten tevreden zijn.
- De Sranan Tongo-teksten moeten nog worden nagelezen door iemand die de taal goed spreekt.
