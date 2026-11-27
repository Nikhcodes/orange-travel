# Requirements → implementatie → test

Bij elke requirement uit de requirementslijst van de groep staat hier hoe hij is gebouwd, waar dat in de code staat en welke test hem bewijst. Alle tests draai je met `uv run pytest`.

Legenda: ✅ volledig · 🟡 met kanttekening (zie de toelichting onderaan)

## Functionele requirements

| ID | Requirement (kort) | Hoe | Waar | Test |
|---|---|---|---|---|
| FR-01 | Wensen achterhalen: budget, duur, type, gezelschap | Vier vragen + aantal personen bij gezin/vrienden | `src/dialogue.py` (`_ask_next`) | `test_fr01_fr03_nfr08_…` ✅ |
| FR-02 | Knoppen én zelf typen | Snelkeuzeknoppen (payloads) en vrije tekst via NLU | `widget/sabi.js`, `src/nlu/slots.py` | `test_fr02_…` ✅ |
| FR-03 | Gerichte vervolgvragen | Vraagt alleen wat nog ontbreekt, één tegelijk | `src/dialogue.py` (`_missing`) | `test_fr01_fr03_nfr08_…` ✅ |
| FR-04 | Wensen wijzigen met een nieuw bericht | Elk bericht wordt op wensen gescand; wijziging wordt gemeld en het advies opnieuw berekend | `src/dialogue.py` (`_preferences`) | `test_fr04_…` ✅ |
| FR-05 | Advies bij twijfel tussen soorten reizen | Uitleg van de drie soorten, met een voorbeeld binnen het budget | `src/dialogue.py` (`_doubt`), `src/texts.py` | `test_fr05_…` ✅ |
| FR-06 | Vervolgvragen, ook als de klant niet tevreden is | "Waarom?", "andere opties", "goedkoper", "langer/korter", "rustiger/avontuurlijker" | `src/dialogue.py` (`_why`, `_more`) | `test_fr06_…` ✅ |
| FR-07 | Prioriteit: budget, duur, type reis | Budget = harde regel; duur weegt het zwaarst in de afstand (gewicht 4), dan type (2); de rubriek volgt dezelfde volgorde | `src/rubric.py`, `config.FINAL_WEIGHTS` | `test_fr07_labels_follow_the_rubric` 🟡 |
| FR-08 | Alleen tours van Orange Travel binnen Suriname | 42 tours van orangesuriname.com; Guyana en Frans-Guyana uitgesloten | `data/tours.csv` | `test_fr08_…` ✅ |
| FR-09 | Prijs, specificaties en reden per reis | Kaartjes met prijs p.p. en totaal, duur, soort, minimum aantal personen en redenen | `src/recommendation_engine.py`, `widget/sabi.js` | `test_fr09_…` ✅ |
| FR-10 | Verschillen toelichten en de beste aanwijzen | Vergelijkingstabel + "past het beste" met reden | `src/dialogue.py` (`_compare`) | `test_fr09_fr10_…` ✅ |
| FR-11 | Duidelijk aangeven wat niet aansluit | Elke afwijking krijgt **!** en het label "Past deels" | `build_reasons()` | `test_fr11_…` ✅ |
| FR-12 | Te laag budget: goedkoopste opties tonen, met melding dat ze boven budget liggen | Aparte lijst `over_budget`, rood gestippeld met "+€… boven budget" | `RecommendationEngine.recommend` | `test_fr12_…` 🟡 |
| FR-13 | Vragen beantwoorden met info van de website | Tourfeiten + kennisbank (TF-IDF-zoekfunctie) | `src/knowledge.py`, `data/knowledge_base.csv` | `test_fr13_fr14_…` ✅ |
| FR-14 | Bron vermelden met een link | Elk antwoord krijgt een link naar orangesuriname.com | `src/dialogue.py` (`_answer`) | `test_fr13_fr14_…` ✅ |
| FR-15 | Zeggen wanneer hij iets niet begrijpt of niet weet | Lage zekerheid van het intentmodel / onbekende woorden / geen kennisbankmatch | `src/nlu/understanding.py`, `texts.NOT_KNOWN` | `test_fr15_…` ✅ |
| FR-16 | Doorverwijzen naar een reisadviseur | Telefoon, openingstijden, contactpagina | `src/dialogue.py` (`_human`) | `test_fr16_…` ✅ |
| FR-17 | Zeggen dat hij niet kan boeken of annuleren | Vangnetregel + intentmodel | `src/nlu/understanding.py`, `_booking` | `test_fr17_fr18_…` ✅ |
| FR-18 | Relevante link of instructie geven | Link naar de tourpagina ("Book now"), contact en betalingsbeleid | `_booking` | `test_fr17_fr18_…` ✅ |
| FR-19 | Waarschuwen bij persoonsgegevens | Gemaskeerd in de browser én gecontroleerd op de server | `widget/sabi.js` (`mask`), `src/nlu/privacy.py` | `test_fr19_…` (3 tests) ✅ |
| FR-20 | Webinterface | Chatwidget + demopagina | `widget/`, `demo/`, `src/api.py` | `test_widget_demo_…` ✅ |
| FR-21 | Openen via een chatbotknop | Ronde knop rechtsonder met Sabi | `widget/sabi.js` | `test_widget_demo_…` ✅ |

## Niet-functionele requirements

| ID | Hoe |
|---|---|
| NFR-01 Usability | Knoppen bij elke vraag, maximaal 3 tips, één scherm, werkt op mobiel (volledig scherm) |
| NFR-02 Performance | Een antwoord kost op de server ± 5–20 ms; de widget wacht bewust ± 0,5 s ("typt…") zodat het natuurlijk voelt |
| NFR-03 Duidelijkheid | Korte zinnen, vaste opbouw van kaartjes, ✓ / ! / i-iconen |
| NFR-04 Beknoptheid | Maximaal 3 aanbevelingen; details staan achter "Waarom?" en "Vergelijk" |
| NFR-05 Communicatiestijl | Alle zinnen staan centraal in `src/texts.py` (gastvrij, je-vorm, professioneel) |
| NFR-06 Betrouwbaarheid | Alleen feiten uit `tours.csv` en `knowledge_base.csv`, altijd met bron; bij twijfel "dat weet ik niet zeker"; prijzen zijn *vanafprijzen*; de site is leidend |
| NFR-07 Privacy | Persoonsgegevens worden verwijderd vóór verwerking; de server bewaart alleen reiswensen per anoniem sessie-id (max. 1 uur, alleen in geheugen) en logt geen berichten |
| NFR-08 Geleidelijk | Eén vraag per beurt, geen formulier vooraf (`test_fr01_fr03_nfr08_…`) |

## Projectbeperkingen

| ID | Hoe |
|---|---|
| PC-01 Informerend, geen agent | Sabi voert geen acties uit; boeken en betalen verwijzen naar de website of een adviseur |
| PC-02 Alleen Orange Travel-context | Vragen buiten het onderwerp krijgen een vriendelijke weigering (`test_pc02_…`) |

---

## Toelichting bij de kanttekeningen

### FR-07 en de eis "soort reis klopt ≥ 90%"
FR-07 zet de **duur vóór het type reis**. Gevolg: als er geen tour van het gekozen type binnen het budget of de duur past, raadt Sabi een ander type aan. Dat wordt op het kaartje gemeld. De opdracht van de docent eist daarnaast dat het type in ≥ 90% van de aanbevelingen klopt.

Bij het tunen houden we beide eisen vast: alleen gewichten die op de ontwikkelset ≥ 90% type-match halen, doen mee. Resultaat op de testset: **94,7%**.

### FR-12 en de eis "100% binnen budget"
De opdracht zegt: *"De bot beveelt nooit een bestemming aan die duurder is dan het budget"* en *"noemt de prijs van de goedkoopste ter informatie, maar beveelt die niet aan"*. FR-12 wil de goedkoopste opties wél *aanbevelen*, met een melding.

**Onze oplossing:**
- Het advies (`recommendations`) ligt **altijd** binnen het budget. Daardoor blijft budget compliance 100%.
- Alleen als er niets past, toont Sabi apart de goedkoopste opties (`over_budget`). Die zijn duidelijk gemarkeerd ("+€65 boven budget", rode stippellijn) en tellen niet als advies.

Laat de docent bevestigen dat dit voor beide eisen geldt.

### FR-13 en de opdracht
De opdracht zegt dat de bestemmingen verzonnen zijn en dat je geen uitspraken doet over het echte aanbod. De groep heeft toestemming van Orange Travel en kiest in de requirements bewust voor echte tours.

Om onjuiste informatie te voorkomen (NFR-06):
- staat in de data wanneer alles is gecontroleerd (`data/README.md`);
- noemt Sabi prijzen *vanaf*;
- linkt Sabi altijd naar de site, die leidend is.
