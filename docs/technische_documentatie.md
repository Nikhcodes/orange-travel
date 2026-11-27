# Technische documentatie – Orange Travel Intelligent Travel Advisor

*UNASAT · Beroepsproduct SH1123AS · Onderwerp 8: Orange Travel – reisadvies op basis van wensen*

Dit document legt het project van begin tot eind uit, zodat **iedereen in de groep** elke keuze kan uitleggen en verdedigen. Alle getallen komen uit echte runs van de code (`uv run python -m scripts.tune_weights` en het beheervenster).

---

## 1. Projectoverzicht

### Probleem
Bij het reisbureau hangt het advies af van de medewerker. Een gesprek kost tijd, en klanten krijgen soms reizen die te duur zijn.

### Oplossing
Een chatbot (**Lora**) stelt de klant vier vragen: soort reis, reisgezelschap, aantal dagen en budget. Daarna geeft de bot maximaal **drie bestemmingen** die het meest op die wensen lijken, met per bestemming de prijs en de reden. Een reis boven het budget wordt **nooit** aanbevolen. Past er niets, dan zegt de bot dat en noemt hij de goedkoopste reis van die soort alleen ter informatie.

### Scope
Binnen de scope vallen het advies, de uitleg, de evaluatie en het beheer van de (fictieve) data. **Buiten** de scope vallen, volgens de opdracht: boeken en betalen, vluchten, visum, beschikbaarheid, weer en seizoen, en beoordelingen van reizigers. Daarom laten we bijvoorbeeld geen aantal overstappen zien en geen label "beste ervaring". Daarvoor zouden we beoordelingen moeten verzinnen.

---

## 2. Technologie

Bij elke technologie: wat het is, wat het in ons project doet, waarom we het gebruiken, en een voorbeeld.

| Technologie | Wat het is | In ons project | Waarom |
|---|---|---|---|
| **Python** | Programmeertaal | Alle code | Vereist; standaard in ML |
| **Pandas** | Tabellen (DataFrames) | CSV inlezen, valideren, `get_dummies` | Opdracht vraagt Pandas; data is een tabel |
| **NumPy** | Rekenen met arrays | Vectoren, afstanden in de uitleg | scikit-learn werkt met NumPy-arrays |
| **scikit-learn** | ML-bibliotheek | `StandardScaler`, `NearestNeighbors` | Betrouwbare, echte implementatie |
| **Streamlit** | Web-UI in Python | Chatbot + beheervenster | Alles in Python, snel te bouwen |
| **Plotly** | Grafieken | Confusion matrices en grafieken in het beheervenster | Interactief (hover), werkt offline |
| **pytest** | Testframework | 33 tests | Bewijst de budgetregel automatisch |
| **uv** | Pakketbeheer | `pyproject.toml` + `uv.lock` | Opdracht vraagt reproduceerbaarheid |

**Voorbeeld one-hot:** de soort `Strand` wordt `soort_Strand=1, soort_Natuur=0, soort_Stad=0`.

**Voorbeeld StandardScaler:** een prijs van $2.850 wordt `(2850 − 2054) / 1203 = 0,66` standaardafwijkingen boven het gemiddelde.

---

## 3. Architectuur en datastroom

```
Klant (chat of vrije tekst)
   │  src/ui/client.py  ·  src/text_parser.py
   ▼
validate_preferences()          budget > 0, dagen ≥ 1, geldige soort/gezelschap
   │                            (groepsbudget → budget per persoon)
   ▼
FeaturePreprocessor             one-hot (pd.get_dummies) + StandardScaler + gewichten
   │  src/preprocessing.py      klant krijgt exact dezelfde 9 kolommen als de bestemmingen
   ▼
NearestNeighbors (euclidisch)   afstand tot ALLE 45 bestemmingen, gesorteerd
   │  src/recommendation_engine.py
   ▼
Harde filters                   prijs ≤ budget  EN  soort = gekozen soort
   ▼
Top 3 + uitleg                  build_reasons() → i18n → kaartjes in de chat
```

| Bestand | Rol |
|---|---|
| `config.py` | Constanten en `FINAL_WEIGHTS` |
| `data_loader.py` | Inlezen en valideren van de CSV's |
| `preprocessing.py` | Featurevectoren |
| `recommendation_engine.py` | KNN, filters, ranking, uitleg |
| `rubric.py` | Verwachte uitkomst voor testwensen (los van het model) |
| `evaluation.py` / `experiments.py` | Metrics, confusion matrices, tuning, onderzoeksvragen |
| `ui/client.py` / `ui/admin.py` | Klantpagina en beheervenster |

---

## 4. Data

### Bestemmingen (`data/destinations.csv`)
45 verzonnen bestemmingen: 15 per soort. Per soort is elk reisgezelschap 3 tot 4 keer vertegenwoordigd. De prijzen lopen van $380 tot $4.900 per persoon, de duur van 3 tot 14 dagen. Kolommen: `id, bestemming, prijs_usd, dagen, soort, geschikt_voor`, plus `beschrijving` en `afbeelding` voor de klantweergave.

**Datakwaliteit:** `validate_destinations()` controleert verplichte kolommen, lege waarden, positieve gehele getallen, toegestane categorieën en unieke namen. Een fout geeft een melding met het rijnummer.

### Testwensen (`data/test_customers.csv`)
60 verzonnen wensen, gemaakt met een vaste *seed* (reproduceerbaar):
- **30 ontwikkelwensen**: alleen gebruikt om de gewichten te kiezen (tuning);
- **30 testwensen**: alleen gebruikt voor de eindmeting.

Elke split bevat 3 wensen waarin niets binnen het budget past.

### De verwachte beste bestemming (rubriek)
De labels komen uit een **geschreven rubriek** (`src/rubric.py`) en níet uit het model:
1. Geschikt = juiste soort én prijs ≤ budget. Niets geschikt → `GEEN`.
2. Voorkeur voor reizen die passen bij het reisgezelschap (als die er zijn).
3. Daarbinnen het kleinste verschil met het gewenste aantal dagen.
4. Bij gelijkspel: de prijs die het dichtst bij het budget ligt.

Een test (`test_labels_follow_rubric`) controleert dat elk label hieruit volgt.

### Mogelijke bias
- **Ontwerpbias:** wij hebben zowel de data als de rubriek gemaakt. Het model wordt dus beoordeeld op óns idee van een goede reis, niet op echte klanttevredenheid.
- **Verdeling:** niet elke combinatie bestaat in elke prijsklasse. Een gezinsreis naar de stad kost minimaal $950, een gezinsreis in de natuur al $380. Klanten met een klein budget krijgen daardoor vaker een reis die niet bij hun gezelschap past.
- **Kleine dataset:** met 45 bestemmingen komen dezelfde reizen vaak terug.

---

## 5. Machine learning stap voor stap

### Stap 1 – One-hot encoding
KNN rekent afstanden, dus tekst moet getallen worden. Strand=1, Natuur=2, Stad=3 zou betekenen dat Stad "verder" van Strand ligt dan Natuur, en dat is onzin. Met `pd.get_dummies()` krijgt elke waarde een eigen kolom met 0 of 1.

**Valkuil die we oplossen:** `get_dummies` op één klantrij maakt alleen de kolom die voorkomt. Wij maken van de kolom eerst een `pd.Categorical` met een vaste lijst categorieën en doen daarna een `reindex` naar de trainingskolommen. Zo heeft een klant altijd exact dezelfde 9 kolommen (getest in `test_customer_vector_matches_training_columns`).

### Stap 2 – StandardScaler
Prijs loopt tot in de duizenden, dagen tot 14. Zonder schalen zou de prijs de afstand domineren. De scaler rekent elke waarde om naar `(x − gemiddelde) / standaardafwijking`. In onze data: prijs gemiddeld **$2.054**, standaardafwijking **$1.203**; dagen gemiddeld **6,8**, standaardafwijking **2,9**. De scaler wordt **alleen op de bestemmingen** gefit en daarna hergebruikt voor de klant (getest).

### Stap 3 – Het budget als prijswens
De klant heeft een budget, een bestemming een prijs. We zetten het budget in de prijskolom van de klantvector. Daarmee zeggen we: "de klant zoekt een reis rond dit prijsniveau". Het budget wordt dus twee keer gebruikt: als **zachte** wens in de afstand en als **harde** grens in het filter.

### Stap 4 – Gewichten
Na het schalen vermenigvuldigen we elke featuregroep met een gewicht. Een gewicht *w* maakt de bijdrage van die groep aan de gekwadrateerde afstand *w²* keer zo groot. De gewichten zijn gekozen met tuning (zie §6): **prijs ×0,25 · dagen ×1 · soort ×1 · gezelschap ×3**.

### Stap 5 – NearestNeighbors
`NearestNeighbors(metric="euclidean")` berekent de afstand van de klant tot **alle** bestemmingen. We vragen bewust niet alleen de 3 dichtstbijzijnde op: als we daarna filteren, zouden er te weinig overblijven terwijl er wél betaalbare opties bestaan.

**Rekenvoorbeeld** (klant: $3.000, 9 dagen, Strand, Stel):

| Kenmerk | Klant | Solenta Eiland ($2.850, 10 d, Stel) | Verschil² | Tamarel Strand ($3.100, 10 d, Gezin) | Verschil² |
|---|---|---|---|---|---|
| prijs (×0,25) | 0,197 | 0,165 | 0,001 | 0,217 | 0,000 |
| dagen | 0,766 | 1,107 | 0,116 | 1,107 | 0,116 |
| soort_Strand | 1 | 1 | 0 | 1 | 0 |
| gezelschap_Stel (×3) | 3 | 3 | 0 | 0 | 9 |
| gezelschap_Gezin (×3) | 0 | 0 | 0 | 3 | 9 |
| **Afstand** = √som | | | **0,343** | | **4,256** |

Solenta Eiland ligt veel dichterbij en wordt nummer 1. Tamarel Strand valt af, omdat het gezelschap niet past én de prijs boven het budget ligt.

### Stap 6 – Harde filters en top 3
Na de ranking vallen alle reizen af met prijs > budget of een andere soort. De eerste drie die overblijven zijn het advies. Zijn er minder dan drie, dan tonen we er minder en vullen we **nooit** aan. Een `assert` in de code en een test over 1.008 combinaties bewaken dat het budget nooit wordt overschreden.

### Stap 7 – Uitleg
Het model levert alleen een afstand op. `build_reasons()` vergelijkt daarom de **echte waarden** van de bestemming met de wens en maakt daar bouwstenen van: past het gezelschap, hoeveel dagen verschil, hoeveel budget blijft er over. Ook wat **niet** past wordt eerlijk getoond ("Let op: bedoeld voor vriendengroepen"). Daarna maakt `i18n.py` er zinnen van in het Nederlands of Sranan Tongo.

### Supervised of unsupervised?
`NearestNeighbors` is **unsupervised**: er wordt geen label voorspeld, het model zoekt alleen gelijkenis. Het enige wat we "leren" uit data zijn de gemiddelden en spreidingen (scaler) en de gewichten (tuning op de ontwikkelset). De testwensen met verwachte uitkomsten gebruiken we als **evaluatie**, vergelijkbaar met een test set bij supervised learning.

---

## 6. Train/test-split en tuning (overfitting voorkomen)

De opdracht vraagt een aparte test set. Wij splitsen de **testwensen**: de bestemmingslijst is het "aanbod" en geen trainingsdata die je kunt opsplitsen.

1. **Ontwikkelset (30):** we proberen 80 combinaties van gewichten (prijs 0–1, dagen 0,5–2, gezelschap 1–3) en kiezen de beste: meeste treffers op plek 1, dan in de top 3, dan de kleinste afwijking van gewicht 1 (bij gelijkspel wint het eenvoudigste model).
2. **Testset (30):** we meten het gekozen model **één keer**. Die cijfers rapporteren we.

| Model | Ontwikkel: plek 1 | Ontwikkel: top 3 | **Test: plek 1** | **Test: top 3** |
|---|---|---|---|---|
| Model A (alle gewichten 1) | 20/30 | 25/30 | 17/30 | 25/30 |
| Model B (zonder prijs) | 23/30 | 29/30 | 21/30 | 25/30 |
| **Eindmodel (getuned)** | 29/30 | 30/30 | **30/30** | **30/30** |

**Is er overfitting?** De testscore is niet lager dan de ontwikkelscore, dus we zien geen overfitting op de gewichten. Kanttekening: de rubriek is zelf een vaste regel. Het getunede model "leert" in feite die regel na, en dat lukt goed met 3 gewichten. Een hoge score betekent dat het model ónze afwegingen consequent volgt. Of echte klanten deze afwegingen ook zo maken, hebben we niet getest.

---

## 7. Evaluatie

### Succescriteria (testset, eindmodel)

| Criterium | Eis | Resultaat |
|---|---|---|
| Aanbevelingen binnen budget | 100% | **100%** (79 aanbevelingen) |
| Soort klopt | ≥ 90% | **100%** |
| Verwachte beste in top 3 | ≥ 24/30 | **30/30** |
| Extra: verwachte beste op plek 1 | – | 30/30 |

*Soort klopt* is 100% doordat soort een hard filter is. Dat is geen verdienste van het model, maar een ontwerpkeuze.

### Confusion matrix 1 – relevantie
Voor elk paar (wens, bestemming), 30 × 45 = 1.350 paren: is de bestemming **relevant** volgens de rubriek (betaalbaar, juiste soort, passend gezelschap als dat bestaat) en heeft de bot haar **aanbevolen** (top 3)?

| | Aanbevolen | Niet aanbevolen |
|---|---|---|
| **Relevant** | TP = 62 | FN = 4 |
| **Niet relevant** | FP = 17 | TN = 1.267 |

- **Precision** = 62 / (62 + 17) = **0,78**: van wat de bot aanbeveelt is 78% relevant.
- **Recall** = 62 / (62 + 4) = **0,94**: van alle relevante reizen vindt de bot er 94%.
- **F1** = **0,86**.
- **Accuracy** = 0,98. Dat getal is misleidend, omdat bijna alle paren "niet relevant & niet aanbevolen" zijn. Daarom rapporteren we ook precision, recall en F1.

**Wat betekenen de fouten?**
- **FP (17):** als er maar 1 of 2 reizen voor jouw gezelschap binnen budget zijn, vult de bot de top 3 aan met andere betaalbare reizen. Die zijn volgens de rubriek "niet relevant", maar de kaart meldt eerlijk dat het gezelschap niet past. Dit is een bewuste keuze: liever een alternatief tonen dan niets.
- **FN (4):** als er méér dan 3 relevante reizen zijn, kunnen ze niet allemaal in de top 3.

Ter vergelijking: Model A haalt precision 0,43 / recall 0,52 / F1 0,47, Model B 0,54 / 0,65 / 0,59.

### Confusion matrix 2 – reisgezelschap (gewenst vs. plek 1)

| klant reist ↓ / plek 1 geschikt voor → | Alleen | Stel | Gezin | Vrienden |
|---|---|---|---|---|
| Alleen | **6** | 0 | 0 | 0 |
| Stel | 0 | **9** | 0 | 0 |
| Gezin | 0 | 0 | **3** | 0 |
| Vrienden | 0 | 0 | 1 | **8** |

De ene fout (Vrienden → Gezin) is een *conflict*-wens: binnen dat budget bestond geen vriendenreis in die soort. De bot meldt dat op de kaart.

---

## 8. Onderzoeksvragen

### OV1 – Welke wensen bepalen het meest of een reis past?
**Ablatie op de testset:** telkens één kenmerk uit de afstand halen.

| Variant | Plek 1 | Top 3 |
|---|---|---|
| Alle kenmerken | 30/30 | 30/30 |
| Zonder prijs | 26/30 | 29/30 |
| Zonder dagen | 21/30 | 30/30 |
| Zonder gezelschap | **11/30** | **20/30** |

**Conclusie:** het reisgezelschap weegt het zwaarst, daarna het aantal dagen en dan de prijs. De soort reis is als hard filter altijd beslissend; die halen we niet weg uit de afstand, want dat verandert niets.

### OV2 – Wat gebeurt er zonder budget als feature?
In alle modellen blijft het **harde budgetfilter** actief: nooit te duur. Alleen de afstand verschilt.
- **Model A** (prijs volledig meegeteld) trekt het advies naar reizen die dicht bij het budget liggen, ook als het gezelschap of de duur minder past: 17/30 op plek 1.
- **Model B** (zonder prijs) let alleen op dagen en gezelschap: 21/30. Zonder prijs gaat het onderscheid verloren tussen een reis van $500 en een van $2.900 bij een budget van $3.000.
- **Een kleine prijsweging (0,25)** werkt het best: de prijs is dan een tiebreaker en niet de hoofdzaak.

### OV3 – Hoe leg je een klant uit waarom?
Een afstand van 0,343 zegt een klant niets. Wiskundige gelijkenis is niet hetzelfde als een uitleg. Daarom tonen we per bestemming in gewone taal wat er klopt (✓) en wat afwijkt (!), gebaseerd op de echte waarden. Daarnaast: het label *Meest aanbevolen*, het resterende budget en de prijs voor de groep. In het beheervenster is per aanbeveling te zien welk deel van de afstand door welk kenmerk komt.

---

## 9. Ontwerpkeuzes

| Keuze | Waarom | Alternatief | Waarom niet |
|---|---|---|---|
| `NearestNeighbors` | Opdracht; begrijpelijk; geen labels nodig | `KNeighborsClassifier` | Er is geen klasse om te voorspellen |
| Euclidische afstand | Standaard, goed uit te leggen | Cosine, Manhattan | Geen duidelijk voordeel bij 9 features |
| Afstand tot álle bestemmingen, dan filteren | Mist nooit een betaalbare reis | `k=3`, dan filteren | Kan 0–1 resultaten geven terwijl er meer bestaan |
| Soort als hard filter | Klant vraagt expliciet een soort | Alleen als feature | Zou soms een andere soort tonen |
| Gezelschap als zachte feature | Anders vaak 0 resultaten | Hard filter | Te weinig data per combinatie |
| Gewichten tunen op aparte set | Eerlijk meten, overfitting zien | Gewichten met de hand | Niet te verantwoorden |
| Labels uit een rubriek | Vooraf vastgelegd, controleerbaar | Labels met de hand | Inconsistent, moeilijk te verdedigen |
| Chatbot in plaats van formulier | Opdracht noemt het een "bot"; voelt als een gesprek | Formulier | Minder persoonlijk |
| Eigen illustraties | Geen foto's van echte plekken bij verzonnen bestemmingen | Stockfoto's | Misleidend en auteursrechten |

---

## 10. Beperkingen en verbeteringen

| Beperking | Mogelijke verbetering |
|---|---|
| 45 verzonnen bestemmingen | Echte (geanonimiseerde) catalogus van het reisbureau |
| Labels uit onze eigen rubriek | Laat medewerkers de verwachte uitkomst bepalen (echte experts) |
| 4 kenmerken | Seizoen, activiteiten, toegankelijkheid toevoegen |
| Geen echte prijzen of beschikbaarheid | Koppeling met een boekingssysteem (buiten scope) |
| Vrije tekst met trefwoorden | Taalmodel of classifier voor intentie |
| Sranan Tongo niet gecontroleerd | Laten nalezen door iemand die de taal goed spreekt |

---

## 11. Vragen die de docent kan stellen (met antwoord)

**Waarom KNN?** Omdat de opdracht het vraagt, en omdat "lijkt deze reis op wat de klant zoekt?" precies een afstandsvraag is. KNN is ook goed uit te leggen.

**Is dit supervised of unsupervised?** `NearestNeighbors` is unsupervised: er is geen label om te voorspellen. We evalueren wel met vooraf bepaalde verwachte uitkomsten, zoals bij een test set.

**Waarom one-hot en geen 1-2-3?** Getallen 1-2-3 suggereren een volgorde en afstand die niet bestaan.

**Waarom StandardScaler?** Zonder schalen domineert de prijs (duizenden) de afstand ten opzichte van dagen (eenheden).

**Waarom fit je de scaler alleen op de bestemmingen?** De bestemmingen zijn de referentie. Als je op klantinvoer fit, verschuift de schaal per klant en zijn afstanden niet meer vergelijkbaar.

**Hoe garandeer je dat nooit iets boven budget komt?** Een hard filter ná de ranking, een `assert` in de code, en een test over 1.008 klantcombinaties × 2 modellen.

**Is er overfitting?** We tunen alleen op de ontwikkelset en meten één keer op de testset. De testscore (30/30) is niet lager dan de ontwikkelscore (29/30). Wel volgt het model onze eigen rubriek, en dat is een vorm van ontwerpbias.

**Welke bias zit in je data?** Wij maakten zowel de data als de rubriek. Daarnaast is er ongelijke dekking per prijsklasse en gezelschap, en de dataset is klein.

**Waarom is accuracy 0,98 maar precision 0,78?** Bijna alle paren zijn terecht "niet relevant en niet aanbevolen" (TN). Accuracy is bij zulke scheve data misleidend.

**Wat gebeurt er als je het budget weglaat?** Zie OV2: het filter blijft actief, maar de keuze binnen het budget wordt minder goed (21/30 in plaats van 30/30 op plek 1).

**Waarom niet `k=3` direct?** Na het filteren blijven er dan soms te weinig over.

**Wat als twee afstanden gelijk zijn?** We sorteren stabiel op afstand, dan op prijs, dan op id. Zo is de uitkomst deterministisch.

**Waarom staat er geen "beste ervaring"?** Daarvoor zijn beoordelingen nodig, en die vallen buiten de scope. We zouden ze moeten verzinnen.
