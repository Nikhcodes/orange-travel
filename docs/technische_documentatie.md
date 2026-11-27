# Technische documentatie: Sabi, reisadviseur voor Orange Travel

*UNASAT · Beroepsproduct SH1123AS · Onderwerp 8: Orange Travel, reisadvies op basis van wensen*

Dit document legt het project van begin tot eind uit, zodat **iedereen in het team** elke keuze kan uitleggen. Alle getallen komen uit echte runs (`uv run python -m scripts.tune_weights` en het dashboard).

---

## 1. Probleem en oplossing

**Situatie.** Een klant weet niet welke tour bij zijn budget en wensen past. Het advies hangt af van de medewerker, een gesprek kost tijd, en soms worden te dure reizen genoemd.

**Oplossing.** **Sabi** is een chatbot die als knop op de website zit. Hij:
1. stelt vier vragen (budget, duur, soort reis, gezelschap);
2. geeft maximaal 3 passende tours van Orange Travel in Suriname, met prijs en reden;
3. beantwoordt vervolgvragen en informatievragen met een bronlink;
4. verwijst door voor boeken en voor persoonlijke hulp.

**Scope.** Sabi informeert en adviseert, maar voert geen acties uit (PC-01). Vluchten, visum, beschikbaarheid, weer en reviews vallen buiten de scope.

---

## 2. Requirements versus de opdracht: bewuste keuzes

De requirementslijst van de groep en de opdracht van de docent botsen op drie punten. Zo hebben we dat opgelost:

| Punt | Opdracht | Requirements | Onze keuze |
|---|---|---|---|
| Data | Verzonnen bestemmingen | Echte tours van Orange Travel (FR-08, FR-13) | Echte tours, met toestemming van Orange Travel; datum van controle vastgelegd; site is leidend |
| Te laag budget | Goedkoopste alleen "ter informatie", nooit aanbevelen | Goedkoopste "aanbevelen" met melding (FR-12) | Advies blijft 100% binnen budget; goedkoopste opties apart, rood gemarkeerd met "+€… boven budget" |
| Prioriteit | Soort reis klopt in ≥ 90% | Budget > duur > type (FR-07) | Duur weegt zwaarder dan type, maar bij het tunen eisen we ≥ 90% type-match |

Zie ook [requirements.md](requirements.md) voor de volledige koppeling requirement → code → test.

---

## 3. Architectuur

```
Browser (widget/sabi.js)         Server (FastAPI, src/api.py)
┌───────────────────────┐        ┌────────────────────────────────────────────┐
│ chatknop + venster    │  JSON  │ Conversation.handle()  (src/dialogue.py)   │
│ maskeert persoons-    │ ─────► │  1. privacyfilter          (nlu/privacy)   │
│ gegevens vóór verzend │        │  2. intent + wensen        (nlu/*)         │
│ toont kaartjes,       │ ◄───── │  3. KNN-advies / kennisbank / doorverwijzen │
│ tabellen, knoppen     │        │  sessie = alleen reiswensen, 1 uur in RAM   │
└───────────────────────┘        └────────────────────────────────────────────┘
```

| Bestand | Rol |
|---|---|
| `src/api.py` | Web-API (`/api/chat`, `/api/tours`, illustraties), levert de widget en de demo |
| `src/dialogue.py` | Gespreksmanager: bepaalt per bericht wat Sabi doet |
| `src/nlu/intent_classifier.py` | ML-model: welke intentie heeft een bericht? |
| `src/nlu/slots.py` | Herkent budget, duur, type, gezelschap en aantal personen in vrije tekst |
| `src/nlu/understanding.py` | Combineert het intentmodel met een paar vangnetregels |
| `src/nlu/privacy.py` | Herkent en verwijdert persoonsgegevens |
| `src/preprocessing.py` | Maakt van tours en wensen vectoren (one-hot, log, StandardScaler, gewichten) |
| `src/recommendation_engine.py` | KNN, budgetregel, FR-12-alternatieven, uitleg |
| `src/knowledge.py` | Beantwoordt vragen met een bron (TF-IDF-zoeken) |
| `src/rubric.py` | Geschreven regel voor de *verwachte* beste tour in de testwensen |
| `src/evaluation.py`, `src/experiments.py` | Metrics, confusion matrix, tuning, onderzoeksvragen |
| `dashboard.py` | Teamdashboard (Streamlit) |

**Waarom FastAPI + een JavaScript-widget en niet alleen Streamlit?** Requirement FR-21 vraagt een chatknop op een website. Een widget die met één `<script>`-regel op elke site werkt, is hoe dat in de praktijk gaat. De intelligentie (ML, regels, data) zit volledig in Python. Streamlit gebruiken we voor het interne dashboard, omdat dat daar het snelst is.

---

## 4. Data

| Bestand | Inhoud | Herkomst |
|---|---|---|
| `tours.csv` | 42 tours: 12 *Stad & omgeving*, 21 *Binnenland & natuur*, 9 *Rondreis*; €27,50 – €2.150 p.p. | orangesuriname.com, gecontroleerd op 27-11-2026 |
| `test_wishes.csv` | 60 verzonnen klantwensen (30 ontwikkel, 30 test) | `scripts/build_test_wishes.py`, vaste seed 597 |
| `intents.csv` | 462 zelf geschreven voorbeeldzinnen, 13 intenties | team |
| `knowledge_base.csv` | 14 algemene onderwerpen, elk met bronlink | orangesuriname.com |

**Datakwaliteit en bias:**
- *Geschiktheid per gezelschap* staat niet overal op de site. Waar de site het zegt staat `site: …`, anders `teamindeling: …` (eigen inschatting). Dat is een bron van **ontwerpbias**.
- *Prijzen* zijn vanafprijzen; kleinere groepen betalen vaak meer. Dat staat in `opmerking` en Sabi meldt het.
- *Scheve verdeling:* er zijn veel meer binnenlandtours (21) dan rondreizen (9). Een klant die een rondreis wil met een klein budget krijgt dus vaak een binnenlandtour. Dat is correct volgens FR-07, en wordt gemeld.
- *Testwensen en rubriek* zijn door ons gemaakt. Een hoge score betekent dat het model **onze** afwegingen volgt, niet dat echte klanten tevreden zijn.

---

## 5. Model 1: KNN-reisadvies

### 5.1 Features
Elke tour en elke wens wordt dezelfde rij van 9 getallen:

| Feature | Tour | Klant | Bewerking |
|---|---|---|---|
| prijs | vanafprijs | budget p.p. ("rond dit prijsniveau") | `log(1+x)` → StandardScaler |
| duur | midden van de duur (bv. 3–5 → 4) | gewenste dagen (paar uur = 0,5) | `log2(x)` → StandardScaler |
| type (3 kolommen) | one-hot | one-hot | `pd.get_dummies` op een Categorical met vaste lijst |
| gezelschap (4 kolommen) | multi-hot, gedeeld door het aantal (som = 1) | one-hot | idem |

**Waarom log?** Het verschil tussen een tour van 3 uur en een van 1 dag is voor een klant groter dan tussen 15 en 16 dagen. Bij prijs geldt hetzelfde: €30 → €90 is een groot verschil, €1.900 → €1.960 niet.

**Waarom StandardScaler?** Zonder schalen zou prijs (honderden) de afstand domineren ten opzichte van duur. De scaler wordt **alleen op de tours** gefit: gemiddelde log-prijs 5,65 (≈ €285), standaardafwijking 1,22; gemiddelde log2-duur 1,44 (≈ 2,7 dagen), standaardafwijking 1,69. Een test bewijst dat klantinvoer de scaler niet verandert.

**Waarom one-hot?** Type 1/2/3 zou een volgorde suggereren die niet bestaat. De klantrij krijgt via een vaste categorielijst en `reindex` altijd exact dezelfde 9 kolommen (getest).

**Waarom multi-hot gedeeld door het aantal?** Een tour kan bij meerdere gezelschappen passen. Zonder deling zou een tour die bij iedereen past ver van elke klant liggen.

### 5.2 Gewichten (FR-07)
Na het schalen wordt elke groep met een gewicht vermenigvuldigd. Het gekozen eindmodel: **prijs × 1 · duur × 4 · type × 2 · gezelschap × 0,5**. Duur weegt dus het zwaarst, daarna type: precies de volgorde van FR-07.

### 5.3 Van afstand naar advies
1. `NearestNeighbors(metric="euclidean")` berekent de afstand van de wens tot **alle** 42 tours. Niet alleen de 3 dichtstbijzijnde, want na het filteren kunnen er dan te weinig overblijven.
2. **Budgetregel (hard):** alleen tours met prijs ≤ budget p.p. Een `assert` en een test over 648 wensen × 3 modellen bewaken dat.
3. De eerste 3 die overblijven vormen het advies. Zijn het er minder, dan vullen we niet aan.
4. Past er niets (FR-12), dan tonen we apart de goedkoopste tours van het gekozen type, gemarkeerd als *boven budget*.

### 5.4 Rekenvoorbeeld
Klant: €400 p.p., 2,5 dagen, Binnenland & natuur, stel (2 personen).

| Feature | Klant | Maratakka (€295, 2–3 d, gezin/vrienden) | verschil² | Myrysji Lodge (€215, 2–3 d, iedereen) | verschil² |
|---|---|---|---|---|---|
| prijs | 0,280 | 0,030 | 0,062 | −0,229 | 0,259 |
| duur | −0,280 | −0,280 | 0 | −0,280 | 0 |
| type_Binnenland (×2) | 2 | 2 | 0 | 2 | 0 |
| gezelschap_Stel (×0,5) | 0,5 | 0 | 0,250 | 0,125 | 0,141 |
| gezelschap_Gezin / Vrienden / Alleen | 0 | 0,25 / 0,25 / 0 | 0,125 | 0,125 elk | 0,047 |
| **afstand** = √som | | | **0,661** | | **0,668** |

Maratakka wint nipt, omdat de prijs dichter bij het budget ligt. Toch is Maratakka niet bedoeld voor stellen en geldt er een minimum van 4 personen. Sabi zet daar daarom twee **!** bij (FR-11). De rubriek (§6) had Myrysji gekozen.

Dit is een goed voorbeeld van een **zwakte van KNN**: een afstand is een compromis, geen regel. Daarom tonen we 3 opties met uitleg, en niet één.

---

## 6. Evaluatie van het advies

### 6.1 Verwachte uitkomst: de rubriek
Voor elke testwens bepaalt een **geschreven regel** (`src/rubric.py`, géén KNN) de beste tour, volgens FR-07:
1. prijs ≤ budget, anders `GEEN`;
2. duur past (0 = past, 1 = maximaal ×2 ernaast, 2 = verder);
3. juiste soort reis;
4. past bij het gezelschap;
5. kleinste exacte duurverschil, daarna de prijs het dichtst bij het budget.

### 6.2 Train/test-split en tuning (overfitting voorkomen)
- **Ontwikkelset (30):** 192 gewichtcombinaties proberen. Alleen combinaties die de opdrachteisen halen (type ≥ 90%, top-3 ≥ 80%) doen mee. Daarvan kiezen we de meeste treffers op plek 1, en bij gelijkspel het eenvoudigste model.
- **Testset (30):** één keer meten. Die cijfers rapporteren we.

| Model | Ontwikkel plek 1 / top 3 | **Test plek 1 / top 3** | Test type klopt |
|---|---|---|---|
| Model A: alle gewichten 1 | 11 / 15 | 19 / 22 | 94,7% |
| Model B: zonder prijs | 10 / 18 | 16 / 23 | 94,7% |
| **Eindmodel (getuned)** | 23 / 25 | **23 / 27** | **94,7%** |

**Overfitting?** De testscore (23/27) is gelijk aan of hoger dan de ontwikkelscore (23/25), dus we zien geen overfitting. Wel is de set klein: één wens meer of minder goed scheelt 3%.

### 6.3 Succescriteria (testset, eindmodel)

| Criterium | Eis | Resultaat |
|---|---|---|
| Aanbevelingen binnen budget | 100% | **100%** (76 aanbevelingen) |
| Soort reis klopt | ≥ 90% | **94,7%** |
| Verwachte tour in top 3 | ≥ 24/30 | **27/30** |

### 6.4 Confusion matrix: relevantie
We tellen over alle 30 × 42 = 1.260 paren (wens, tour): is de tour **relevant** volgens de rubriek (even goed als de beste op regels 1–4) en heeft Sabi hem **aanbevolen**?

| | Aanbevolen | Niet aanbevolen |
|---|---|---|
| **Relevant** | TP = 39 | FN = 14 |
| **Niet relevant** | FP = 37 | TN = 1.170 |

- **Precision 0,51:** de helft van wat Sabi toont is "even goed als de beste". De rest zijn alternatieven die op één punt afwijken; die worden met **!** gemarkeerd.
- **Recall 0,74:** van de relevante tours vindt Sabi er driekwart.
- **F1 0,60.**
- **Accuracy 0,96:** misleidend, omdat bijna alle paren terecht "niet relevant, niet aanbevolen" zijn.

Ter vergelijking: Model A haalt F1 0,43, Model B 0,53.

---

## 7. Model 2: intentclassifier

**Doel.** Begrijpen wat de klant wil met een getypt bericht: wens geven, tourvraag, vergelijken, waarom, andere opties, twijfel, boeken, medewerker, bedankt, opnieuw, over de bot, buiten de scope of groet.

**Model.** `TfidfVectorizer` op woorden (1–2-grammen) én tekens (1–4-grammen, robuust tegen typfouten), met daarop `LogisticRegression` (C = 10, gebalanceerde klassen). We kozen dit model met 5-voudige cross-validatie uit varianten met LinearSVC en Naive Bayes; die scoorden ongeveer gelijk (0,71–0,75). Logistische regressie geeft daarnaast een **kans**, die we gebruiken voor "niet begrepen" (FR-15).

**Evaluatie.** Gestratificeerde split 75/25 (346 train, 116 test):

| | Waarde |
|---|---|
| Accuracy | **0,70** (kans bij gokken: ± 0,08) |
| Macro-F1 | **0,71** |

De meeste fouten zitten tussen intenties die op elkaar lijken, zoals *vergelijken* en *twijfel_type*, of *meer_opties* en *voorkeur*. De volledige confusion matrix en alle fout geclassificeerde zinnen staan in het dashboard.

**Vangnetregels.** Voor situaties waarin een fout schadelijk is, gaat een paar trefwoordregels vóór het model: boeken/annuleren (FR-17), een mens spreken (FR-16) en opnieuw beginnen. Daarnaast geldt: bevat een bericht twee of meer reiswensen, dan is het een voorkeur. En kent het model geen enkel woord (zoals "asdkjh"), dan zegt Sabi dat hij het niet begrijpt in plaats van te gokken.

**Beperking.** Met 462 zinnen is het model beperkt. Meer voorbeeldzinnen in `intents.csv` verbeteren het direct. De knoppen in de widget gaan helemaal buiten het model om.

---

## 8. Vragen beantwoorden met bron (FR-13, FR-14)

1. **Gaat de vraag over een tour?** Dat herkennen we via bijnamen ("brownsberg", "dolfijn") en fuzzy matching. Dan antwoordt Sabi met de feiten uit `tours.csv` waar naar gevraagd wordt (prijs, duur, minimum, intensiteit, geschikt voor kinderen) en linkt hij naar de tourpagina.
2. **Anders:** TF-IDF op tekentrigrammen + cosinusgelijkenis met `knowledge_base.csv`. Onder 0,12 zegt Sabi dat hij het niet zeker weet en verwijst hij door (FR-15, NFR-06). Voor vragen buiten de scope geldt een strengere drempel van 0,3.

Sabi verzint nooit iets: wat niet in de data staat ("is lunch inbegrepen?") verwijst naar de tourpagina.

---

## 9. Privacy (FR-19, NFR-07)

- **In de browser** worden e-mailadressen, telefoonnummers en kaartnummers al vervangen door `[verwijderd]`, vóórdat er iets wordt verstuurd.
- **Op de server** controleert `privacy.py` opnieuw: e-mail, telefoon (+597 en 7-cijferige nummers), IBAN, creditcard (met Luhn-controle), geboortedatum, paspoort/ID, adres en "mijn naam is …".
- Sabi waarschuwt, gebruikt de gegevens niet en gaat verder met de rest van het bericht.
- De server bewaart **alleen reiswensen** per anoniem sessie-id, maximaal 1 uur, alleen in het geheugen. Berichten worden niet opgeslagen of gelogd.

---

## 10. Onderzoeksvragen

### OV1: Welke wensen bepalen het meest of een reis past?
Ablatie op de testset: steeds één kenmerk weglaten uit de afstand.

| Variant | Plek 1 | Top 3 | Type klopt |
|---|---|---|---|
| Alle kenmerken | 23/30 | 27/30 | 94,7% |
| Zonder prijs | 20/30 | 25/30 | 93,4% |
| **Zonder duur** | **15/30** | **21/30** | 94,7% |
| Zonder type | 21/30 | 28/30 | **80,3%** |
| Zonder gezelschap | 20/30 | 26/30 | 94,7% |

**Conclusie:** **duur** is het belangrijkst; zonder duur zakt de score het hardst. Zonder type blijft de top 3 goed, maar klopt het type nog maar in 80% van de gevallen: dan zakken we onder de eis. Prijs en gezelschap verfijnen het advies.

### OV2: Wat gebeurt er als je het budget weglaat als feature?
De budgetregel blijft altijd actief, dus er komt nooit iets te duurs in het advies. Model B (zonder prijs in de afstand) scoort 16/30 op plek 1, tegen 23/30 voor het eindmodel. Zonder prijs ziet het model geen verschil tussen een tour van €95 en een van €375 bij een budget van €400, terwijl de rubriek "het budget goed benutten" laat meewegen.

### OV3: Hoe leg je uit waarom de bot een tour aanbeveelt?
Een afstand van 0,661 zegt een klant niets: wiskundige gelijkenis is geen uitleg. Daarom vergelijkt `build_reasons()` de **echte waarden** van de tour met de wens. Elk punt krijgt ✓ (klopt), **!** (wijkt af) of *i* (tip). Daarnaast tonen we "Past deels", een vergelijkingstabel en een bronlink. In de code (`distance_shares`) kunnen we ook laten zien welk deel van de afstand door welk kenmerk komt.

---

## 11. Beperkingen en verbeteringen

| Beperking | Verbetering |
|---|---|
| Geschiktheid per gezelschap deels eigen inschatting | Laten nalopen door medewerkers van Orange Travel |
| Rubriek en testwensen door ons gemaakt | Echte (geanonimiseerde) adviezen van medewerkers als grondwaarheid |
| Intentmodel 70% op 13 klassen | Meer en echtere voorbeeldzinnen; eventueel een groter taalmodel |
| Alleen Nederlands | Engelse versie (veel toeristen); de site is tweetalig |
| Prijzen veranderen | Periodiek de tourpagina's controleren, of een koppeling met hun systeem |
| Geen beschikbaarheid, seizoen of boeken | Buiten de scope; doorverwijzing naar de site |

---

## 12. Vragen die de docent kan stellen

**Waar zit de machine learning?** In twee modellen: KNN (`NearestNeighbors`) voor het advies en een supervised intentclassifier (TF-IDF + logistische regressie) voor tekst. De gewichten van KNN zijn getuned op data.

**Supervised of unsupervised?** KNN-advies is unsupervised: er is geen label. De intentclassifier is supervised: hij is getraind op gelabelde zinnen.

**Train/test?** Het intentmodel gebruikt een gestratificeerde split van 75/25. Voor het advies zijn de testwensen gesplitst in 30 ontwikkel (tunen) en 30 test (één keer meten).

**Waarom deze metrics?** Accuracy alleen is misleidend: bij de relevantiematrix zijn bijna alle paren TN. Daarom rapporteren we ook precision, recall en F1.

**Is er overfitting?** Het advies scoort op de test niet slechter dan op ontwikkel. Het intentmodel scoort in cross-validatie ± 0,74 en op de testset 0,70: dat is vergelijkbaar.

**Welke bias?** Eigen inschatting bij de geschiktheid, een door ons gemaakte rubriek, meer binnenlandtours dan rondreizen, en zelf geschreven zinnen voor het intentmodel.

**Waarom nooit boven budget, terwijl FR-12 dat vraagt?** Het advies blijft binnen het budget (eis van de opdracht). De goedkoopste opties staan apart en zijn duidelijk gemarkeerd (FR-12).

**Waarom log-transformatie?** Relatieve verschillen tellen: 3 uur vs. 1 dag is groter dan 15 vs. 16 dagen.

**Waarom 3 opties en niet 1?** De afstand is een compromis (zie het rekenvoorbeeld). Met drie opties en uitleg kiest de klant zelf.

**Hoe voorkom je dat Sabi dingen verzint?** Hij antwoordt alleen uit `tours.csv` en `knowledge_base.csv`, met een bron. Onder de drempel zegt hij "dat weet ik niet zeker".
