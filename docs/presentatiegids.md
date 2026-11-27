# Presentatiegids

**Format:** iedereen presenteert **een eigen deel** met een **eigen PowerPoint** van **3 tot 4 minuten**. Daarna volgt een vragenronde over het **hele** project. Iedereen moet dus alles kunnen uitleggen.

## Voorgestelde verdeling (5 personen)

Wissel gerust onderling; zorg dat elk deel gedekt is.

| # | Deel | Inhoud (± 3,5 min) | Laat zien |
|---|---|---|---|
| 1 | **Probleem, requirements & live demo** | Situatie bij Orange Travel, wat Sabi doet, de botsingen met de opdracht (FR-07, FR-12) | Demopagina + bladwijzer op orangesuriname.com |
| 2 | **Data** | 42 echte tours, bron en datum, teamindeling vs. site, 60 testwensen, rubriek, bias | `data/tours.csv`, dashboard → Tours beheren |
| 3 | **KNN-advies** | Features (one-hot, log, StandardScaler), gewichten, budgetregel, rekenvoorbeeld Maratakka vs. Myrysji | Dashboard → Advies testen |
| 4 | **Intentmodel, kennisbank & privacy** | TF-IDF + logistische regressie, confusion matrix, vangnetregels, FR-13/14 met bron, FR-19 | Dashboard → Intentmodel, privacy live |
| 5 | **Evaluatie & onderzoeksvragen** | Train/test-split, succescriteria, relevantiematrix, OV1–OV3, beperkingen | Dashboard → Onderzoek |

## Demoscript (deel 1, ± 90 seconden)

**Voorbereiding:**
- Start de API (`uv run uvicorn src.api:app`) en het dashboard.
- Open de demopagina in tabblad 1 en orangesuriname.com in tabblad 2.
- Zet de browserzoom op 110%.

| Doe | Zeg |
|---|---|
| Tabblad 2, klik de bladwijzer | "Zo ziet Sabi eruit op de echte site van Orange Travel. Dit gebeurt alleen in mijn browser; de site zelf is niet aangepast." |
| Klik Sabi, kies *Binnenland* → *Met z'n tweeën* → *2–3 dagen* → *€400* | "Vier korte vragen, één tegelijk. Je kunt klikken of typen." |
| Wijs naar de kaartjes | "Drie tours binnen budget, met prijs voor de groep en de reden. Een uitroepteken betekent dat iets niet past: eerlijk, zoals FR-11 vraagt." |
| Klik **Vergelijk** | "Sabi zet de verschillen naast elkaar en zegt welke het best past." |
| Typ *"toch liever 1 dag"* | "Wensen kun je met een gewoon bericht aanpassen." |
| Typ *"hoeveel kost awarradam?"* | "Informatie komt van de website, met een bronlink." |
| Typ *"mijn email is test@test.sr"* | "Persoonsgegevens worden al in de browser verwijderd en Sabi waarschuwt." |
| Typ *"20 euro"* | "Past niets? Dan zegt Sabi dat en toont hij de goedkoopste opties, duidelijk boven budget." |

**Als het internet of de bladwijzer hapert:** gebruik de demopagina (<http://localhost:8000/demo>) of de schermafbeeldingen in `docs/img/`.

## Kernzinnen per deel

1. *"Sabi beveelt nooit een tour boven het budget aan. Dat is een harde regel en geen voorkeur, en we bewijzen het met een test over 648 wensen."*
2. *"Waar de site iets zegt over geschiktheid gebruiken we dat letterlijk; waar niet, staat er 'teamindeling'. Dat is een bewuste en zichtbare bron van bias."*
3. *"KNN geeft een afstand, geen regel. In het rekenvoorbeeld wint Maratakka met 0,661 tegen 0,668, terwijl hij niet voor stellen bedoeld is. Daarom tonen we drie opties met uitleg."*
4. *"Het intentmodel haalt 0,70 accuracy op 13 klassen, waar gokken 0,08 geeft. Voor boeken en privacy vertrouwen we niet alleen op het model."*
5. *"We hebben op 30 wensen getuned en op 30 andere gemeten: 27 van de 30 in de top 3, 100% binnen budget en 94,7% juiste soort reis."*

## Vragen die zeker komen (antwoorden in de [technische documentatie §12](technische_documentatie.md#12-vragen-die-de-docent-kan-stellen))

- Waarom dit model? · Supervised of unsupervised? · Is er overfitting? · Welke bias zit in je data?
- Waarom geen accuracy alleen? · Hoe werkt StandardScaler? · Waarom one-hot?
- Wat gebeurt er zonder budget als feature? · Waarom gebruiken jullie echte data, terwijl de opdracht verzonnen data noemt?

## Checklist

- [ ] Iedereen heeft `git clone`, `uv sync` en `uv run pytest` gedaan (63 passed).
- [ ] Iedereen kan de demo zelf geven.
- [ ] Docent heeft de keuzes bij FR-07, FR-12 en echte data gezien.
- [ ] Eigen PowerPoint per persoon, getimed.
- [ ] Back-up: schermafbeeldingen in `docs/img/`.
