from ki.parser import plaene_extrahieren, titel_ableiten

WOCHENPLAN = '''Gerne! Ich achte auf Muskelaufbau und Gluten.

**Montag** – Frühstück: Porridge …

```json
{"typ":"wochenplan","titel":"Glutenfreier Plan","tage":[{"tag":"Montag","mahlzeiten":[{"name":"Frühstück","gericht":"Porridge","kcal":520,"protein_g":28}]}]}
```

Prep-Tipps: …'''


def test_wochenplan_wird_extrahiert():
    text, plaene = plaene_extrahieren(WOCHENPLAN)
    assert len(plaene) == 1 and plaene[0]["typ"] == "wochenplan"
    assert "```json" not in text and "Prep-Tipps" in text
    assert titel_ableiten(plaene[0]) == "Glutenfreier Plan"


def test_rezept_wird_extrahiert():
    t = 'Hier:\n```json\n{"typ":"rezept","titel":"Bowl","zutaten":[{"menge":"300 g","name":"Hähnchen"}],"schritte":["braten"]}\n```'
    _, plaene = plaene_extrahieren(t)
    assert plaene[0]["typ"] == "rezept"


def test_ungueltiges_json_wird_ignoriert():
    text, plaene = plaene_extrahieren('Text\n```json\n{"typ":"wochenplan", kaputt\n```\nEnde')
    assert plaene == [] and "Ende" in text


def test_fremdes_json_bleibt_stehen():
    t = 'Nährwerte:\n```json\n{"kcal": 500}\n```'
    text, plaene = plaene_extrahieren(t)
    assert plaene == [] and '"kcal": 500' in text


def test_unvollstaendiger_plan_wird_verworfen():
    _, plaene = plaene_extrahieren('```json\n{"typ":"wochenplan","titel":"leer"}\n```')
    assert plaene == []


def test_kein_json_kein_plan():
    text, plaene = plaene_extrahieren("Iss vor dem Training eine Banane.")
    assert plaene == [] and text.startswith("Iss")
