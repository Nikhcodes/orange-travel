# Data

| Bestand | Inhoud |
|---|---|
| `tours.csv` | 42 tours en rondreizen van Orange Travel Suriname, alleen binnen Suriname (FR-08) |
| `test_wishes.csv` | 60 testwensen: 30 `ontwikkel` (tunen) en 30 `test` (eindmeting); gemaakt met `scripts/build_test_wishes.py` |
| `intents.csv` | Gelabelde voorbeeldzinnen voor het intentmodel (zelf geschreven, geen klantdata) |
| `knowledge_base.csv` | Algemene vragen en antwoorden (contact, betalen, boeken, maatwerk), elk met bronlink (FR-13, FR-14) |

## Bron en controle

- **Bron:** de officiële website <https://www.orangesuriname.com> (tourpagina's, contactpagina, betalingsbeleid).
- **Laatst gecontroleerd:** 27 november 2026.
- **Prijzen** zijn *vanafprijzen* per persoon in euro, zoals op de site. Bij kleinere groepen is de prijs vaak hoger; dat staat dan in `opmerking`.
- **Uitgesloten:** tours buiten Suriname (Guyana, Frans-Guyana, Three Guianas) en tours waarvan prijs of duur niet op de site stond (bijv. Menimi Eco Resort).

## Kolommen in `tours.csv`

| Kolom | Betekenis |
|---|---|
| `type` | `Stad & omgeving` (Paramaribo, Commewijne, Peperpot, rivier), `Binnenland & natuur` (jungle, stuwmeer, Galibi), `Rondreis` (meerdaagse rondreis door Suriname) |
| `dagen_min`, `dagen_max` | Duur in dagen. Tours tot ± 6,5 uur = 0,5 (dagdeel); 7–12 uur = 1 |
| `alleen`, `stel`, `gezin`, `vrienden` | 1 = geschikt voor dit reisgezelschap |
| `bron_geschiktheid` | `site: …` = staat letterlijk op de tourpagina. `teamindeling: …` = onze eigen inschatting (bijv. op basis van het minimum aantal personen of de naam van de reis) |
| `opmerking` | Belangrijke kanttekeningen (seizoen, toeslagen, onduidelijkheden op de site) |

> **Let op:** prijzen en aanbod kunnen veranderen. De bot linkt daarom altijd naar de tourpagina en zegt dat de website leidend is.
