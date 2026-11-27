# Presentatiegids – Orange Travel

**Format volgens de opdracht:** elke student presenteert **zijn eigen deel** met een **eigen PowerPoint**, in **3 tot 4 minuten**. Daarna volgt een vragenronde over het **hele** beroepsproduct. Iedereen moet dus de hele bot kennen, niet alleen het eigen deel.

> Vraag de docent naar de beoordelingsrubriek (bijlage 6). Die was bij het maken van deze gids nog niet beschikbaar.

---

## 1. Voorgestelde verdeling (4 personen)

Pas de namen aan. Bij 3 personen voeg je deel 3 en 4 samen; bij 5 personen splits je deel 2 in "data" en "rubriek".

| Deel | Onderwerp | Inhoud (± 3,5 min) | Te tonen |
|---|---|---|---|
| **1** | Probleem & oplossing + **live demo** | Situatie bij het reisbureau, wat de bot doet, scope. Demo van 1 advies en 1 geen-advies. | Klantpagina |
| **2** | Data & rubriek | 45 bestemmingen, 60 testwensen, split 30/30, hoe de verwachte uitkomst is bepaald, bias. | `destinations.csv`, beheer → Bestemmingen |
| **3** | Het model | One-hot, StandardScaler, NearestNeighbors, filters, gewichten, rekenvoorbeeld. | Beheer → Uitleg model |
| **4** | Evaluatie & onderzoek | Succescriteria, beide confusion matrices, precision/recall/F1, overfitting, OV1–OV3, beperkingen. | Beheer → Testen en Onderzoek |

---

## 2. Opbouw per deel (dia's en kernzinnen)

### Deel 1 – Probleem, oplossing, demo
1. **Titeldia**: logo, "Lora – reisadvies op basis van wensen".
2. **Probleem**: advies verschilt per medewerker, gesprekken kosten tijd, klanten krijgen soms te dure reizen.
3. **Oplossing**: 4 vragen → maximaal 3 reizen met prijs en reden, nooit boven budget.
4. **Live demo** (zie §3).

> *"De belangrijkste regel van onze bot is dat hij nooit een reis aanbeveelt die duurder is dan het budget. Dat is geen wens maar een harde grens, en die hebben we met tests bewezen."*

### Deel 2 – Data en rubriek
1. **Bestemmingen**: 45 verzonnen reizen, 15 per soort, $380–$4.900, 3–14 dagen.
2. **Testwensen**: 60 wensen met een vaste seed; 30 om te tunen, 30 om te meten.
3. **Rubriek**: de vier regels (zie technische documentatie §4).
4. **Bias**: wij maakten de data én de rubriek; kleine dataset; niet elke combinatie in elke prijsklasse.

> *"We hebben de verwachte beste bestemming vastgelegd met een geschreven regel, vóórdat we het model gingen afstellen. Zo kan het model zijn eigen antwoorden niet goedkeuren."*

### Deel 3 – Het model
1. **Waarom getallen?** KNN rekent afstanden → one-hot met `pd.get_dummies`.
2. **Waarom schalen?** Prijs in duizenden, dagen in eenheden → StandardScaler, alleen gefit op de bestemmingen.
3. **KNN**: afstand tot alle 45 bestemmingen → filter (budget, soort) → top 3.
4. **Rekenvoorbeeld**: Solenta Eiland (afstand 0,343) tegenover Tamarel Strand (4,256).
5. **Gewichten**: gezelschap ×3, prijs ×0,25, gekozen op de ontwikkelset.

> *"NearestNeighbors is unsupervised: het voorspelt geen label, het zoekt de reizen die het meest lijken op de wens."*

### Deel 4 – Evaluatie en onderzoek
1. **Succescriteria (testset)**: budget 100%, soort 100%, top 3 30/30.
2. **Confusion matrix (relevantie)**: TP 62, FP 17, FN 4, TN 1.267 → precision 0,78, recall 0,94, F1 0,86. Leg uit waarom accuracy (0,98) misleidend is.
3. **Confusion matrix (gezelschap)**: 1 fout, en die is een conflictwens.
4. **Overfitting**: tunen op de ontwikkelset, één meting op de testset; test (30/30) is niet slechter dan ontwikkel (29/30).
5. **OV1**: zonder gezelschap 11/30, zonder dagen 21/30, zonder prijs 26/30.
6. **OV2**: Model A 17/30, Model B 21/30, eindmodel 30/30; het budgetfilter blijft altijd actief.
7. **OV3**: uitleg in gewone taal met ✓ en !, gebaseerd op echte waarden.
8. **Beperkingen**: eigen rubriek, kleine dataset, geen echte prijzen.

> *"Een hoge score betekent dat de bot ónze afwegingen consequent volgt. Of echte klanten het eens zijn, hebben we niet getest. Dat is de belangrijkste beperking."*

---

## 3. Demoscript (deel 1, ± 90 seconden)

**Voorbereiding:** start de app vóór de presentatie (`uv run streamlit run app.py`). Open de klantpagina in één tabblad en het beheervenster (ingelogd) in een tweede. Zet de browserzoom op 110–125%.

| Klik / doe | Zeg |
|---|---|
| Laat het startscherm zien | "Dit is Lora, de reisadviseur van Orange Travel. De klant krijgt vier vragen." |
| Klik **Strand** → **Met z'n tweeën** → **Een week · 7** | "Met knoppen, zodat iedereen het kan gebruiken." |
| Budget **Per persoon** op **$1.500**, klik **Zoek mijn reizen** | "Het budget kan per persoon of voor de hele groep." |
| Wijs naar de kaarten | "Drie reizen binnen het budget. *Meest aanbevolen* past het best; *Voordeligst* is de goedkoopste van de drie. Op elke kaart staat waarom, en ook wat níet past." |
| Klik **Opnieuw beginnen**, typ: *stad alleen, 5 dagen, 400 dollar* | "Je kunt ook gewoon typen." |
| Wijs naar het gestippelde kader | "Er past niets. De bot beveelt dan niets aan en noemt de goedkoopste stadsreis alleen ter informatie, zoals de opdracht vraagt." |
| (optioneel) Klik **Sranan** rechtsboven | "De bot werkt ook in het Sranan Tongo." |

**Als de demo hapert:** gebruik de schermafbeeldingen in `docs/img/`.

---

## 4. Vragen oefenen

Alle antwoorden staan in de [technische documentatie §11](technische_documentatie.md#11-vragen-die-de-docent-kan-stellen-met-antwoord). Oefen deze drie zeker, want die noemt de opdracht zelf:

1. **"Waarom dit model?"** → De opdracht vraagt KNN, en "lijkt deze reis op de wens?" is precies een afstandsvraag. Het is uitlegbaar: we kunnen per kenmerk laten zien waar de afstand vandaan komt.
2. **"Is er overfitting?"** → Gewichten gekozen op 30 ontwikkelwensen en één keer gemeten op 30 andere wensen. Het resultaat is gelijk of beter, dus geen teken van overfitting. De beperking is dat beide sets met onze eigen rubriek zijn gelabeld.
3. **"Welke bias kan er in je data zitten?"** → Ontwerpbias (wij maakten data en rubriek), ongelijke dekking per prijsklasse en gezelschap, en een kleine dataset.

**Oefentip:** laat een groepsgenoot willekeurige vragen stellen over een deel dat je níet zelf presenteert.

---

## 5. Checklist vóór de presentatie

- [ ] Iedereen heeft het project lokaal draaien (`uv sync`, `uv run streamlit run app.py`).
- [ ] `uv run pytest` geeft *33 passed*.
- [ ] Iedereen heeft de technische documentatie gelezen.
- [ ] Eigen PowerPoint per persoon, getimed op 3–4 minuten.
- [ ] Sranan Tongo-teksten zijn nagelezen (of laat de taalwissel weg in de demo).
- [ ] Beheerwachtwoord aangepast en bekend bij de groep.
- [ ] Back-up van de demo: schermafbeeldingen in `docs/img/`.
