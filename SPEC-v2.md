# SPEC v2 — PTL Coaching System = Rezept-Buddy + Natty-Gains-Funktionen

Stand: 06.09.2026 · Baut auf dem fertigen v1 (SPEC.md) auf. Alles bleibt ein Repo, ein Backend, eine Kunden-App.
Grundsatz: **Der Buddy ist die Bedienoberfläche, die Module sind seine Datenquellen.** Jedes Modul liefert Daten in den Systemprompt und bekommt Tools, mit denen der Buddy schreiben darf.

## Modulübersicht und Bau-Reihenfolge

| # | Modul | Nutzen | Hängt ab von |
|---|---|---|---|
| M1 | Tracking + Tagesbilanz | Kunde hakt Mahlzeiten ab, sieht Ist/Soll | v1 (plaene, lebensmittel) |
| M2 | Rezeptbibliothek + Einkaufsliste | Wiederverwendung, Tausch, Coach kuratiert | M1 |
| M3 | Check-ins + Körperdaten | Fortschritt sichtbar, Buddy passt Ziele an | v1 |
| M4 | Erinnerungen + Onboarding-Strecke | Kunde bleibt dran ohne Coach-Aufwand | M1, M3 |
| M5 | Coach-Cockpit | Ampel je Kunde, Wochenreport, Eingriffe | M1–M4 |
| M6 | Training | Plan, Übungen, Logging | eigenständig, zuletzt |
| — | Abrechnung | bleibt im Pipeline CRM (Stripe/SEPA dort), hier nur Status-Flag `aktiv` | CRM |

Reihenfolge M1→M2→M3→M4→M5→M6. Jedes Modul einzeln abnehmbar, jedes erweitert Systemprompt + Tools des Buddys.

---

## M1 — Tracking + Tagesbilanz

### Daten
**tagebuch** — ein Dokument je Kunde und Tag
`kunde_id, datum (YYYY-MM-DD), eintraege[], summe {kcal, protein_g, fett_g, kh_g}, ziel {kcal, protein_g}, notiz, aktualisiert_am`

**eintraege[]**
`id, mahlzeit (fruehstueck|mittag|abend|snack), quelle (plan|rezept|bls|frei|buddy), ref_id?, bezeichnung, menge_g?, kcal, protein_g, fett_g?, kh_g?, erledigt (bool), erstellt_am`

**aktiver_plan** am Kunden: `plan_id, start_datum` — der Wochenplan, der gerade "läuft". Tage des Plans werden beim ersten Öffnen eines Tages als Einträge mit `quelle=plan, erledigt=false` vorbelegt.

### API
- `GET /tagebuch/{datum}` → Tag inkl. Summe/Ziel (legt Einträge aus aktivem Plan an, falls leer)
- `POST /tagebuch/{datum}/eintraege` {mahlzeit, quelle, ref_id?, bezeichnung, menge_g?, kcal…}
- `PATCH /tagebuch/{datum}/eintraege/{id}` {erledigt?, menge_g?, …}
- `DELETE /tagebuch/{datum}/eintraege/{id}`
- `GET /tagebuch?von=&bis=` → Wochen-/Monatsübersicht (Summen je Tag)
- `PUT /plaene/{id}/aktivieren` {start_datum} → setzt aktiver_plan
- `GET /lebensmittel?q=` existiert; neu `GET /lebensmittel/barcode/{ean}` → Open Food Facts (Cache in Collection barcodes)

### Buddy-Erweiterung
Systemprompt bekommt: heutige Bilanz (gegessen/offen), letzte 7 Tage Trefferquote (Tage im ±10 %-Korridor), aktiver Plan.
Neue Tools: `eintrag_anlegen(datum, mahlzeit, bezeichnung, menge_g, kcal, protein_g)` — damit "Ich hatte gerade eine Pizza" direkt gebucht wird, Rückfrage nur wenn Menge fehlt. `tag_lesen(datum)`.
Regel in prompts/rezept_buddy.md ergänzen: Bei Abendfrage zuerst die offene Bilanz nennen ("Dir fehlen noch 40 g Protein").

### UI Kunde
- **/heute** wird Startseite (statt /chat): Ring kcal + Balken Protein, darunter Mahlzeiten mit Abhaken, "+ Eintrag" (Suche BLS / Barcode / freier Text / "Buddy fragen"). Wischen für Vortag/Folgetag.
- Tab-Leiste unten: Heute · Chat · Pläne · Ich (Profil/Check-ins)
- Im Chat: Wochenplan-Karte bekommt Knopf "Ab Montag aktiv".


### M1b — Foto-Erfassung (Essen gehen, unterwegs)
- Kunde fotografiert den Teller (Kamera direkt aus /heute, "+ Eintrag → Foto"). Bild wird verkleinert (max. 1024 px, JPEG) und an die Anthropic API geschickt (Vision), **zusammen mit dem Profil** (Ernährungsart, Unverträglichkeiten) und optionalem Kurztext ("Italiener, Pizza Margherita, groß").
- Modell liefert JSON: `komponenten[{bezeichnung, menge_g_geschaetzt, sicherheit (hoch|mittel|niedrig)}]`. Nährwerte werden **nicht** vom Modell übernommen, sondern je Komponente über das BLS-Tool nachgeschlagen und mit der Menge multipliziert — gleiche Regel wie überall: Zahlen aus BLS, Mengen aus dem Modell.
- Antwort an den Kunden: Vorschau-Karte "Pizza Margherita ca. 350 g · Beilagensalat 80 g → ca. 890 kcal, 38 g Protein" mit Schieberegler für die Portionsgröße (klein/normal/groß = ×0,75/×1/×1,3) und "Buchen". Erst nach Tippen wird der Eintrag mit `quelle=foto` angelegt. Sicherheitsstufe wird angezeigt ("grobe Schätzung" bei niedrig).
- Warnung aus dem Profil: erkennt das Modell eine Zutat, die gegen eine Unverträglichkeit verstößt, zeigt die Karte das vor dem Buchen an (z. B. "enthält vermutlich Gluten").
- Foto wird nach der Analyse **nicht** gespeichert (nur der Eintrag), außer der Kunde tippt "Foto behalten" → dann privat auf Hetzner wie M3-Fotos.
- Ehrliche Erwartung, die auch im UI steht: Foto-Schätzungen liegen typischerweise ±20–30 % daneben (verdeckte Öle, Saucen, Portionsgröße ohne Referenz). Für den Coaching-Zweck (Größenordnung halten, nicht grammgenau) reicht das; die Alternative "gar nichts erfassen beim Essen gehen" ist schlechter.
- Kosten: ca. 1.500 Bild-Tokens + Text je Foto → deutlich unter 1 Cent je Erfassung; Logging wie beim Chat.
- Tests: 10 Referenzfotos (bekannte Gerichte mit Waage-Gewicht) als Regression — Zielwerte siehe unten.

#### Genauigkeit erhöhen (Pflichtbestandteil von M1b)
1. **Kontext mitschicken:** Kurztext (Restaurant/Gericht/Größe), Profil mit Tagesziel, Uhrzeit; Ort nur mit Opt-in. Kamera-Screen zeigt ein Textfeld "Was ist das?" direkt unter dem Sucher.
2. **Größenreferenz:** Kamera-Overlay "Gabel oder Hand daneben legen". Ohne Referenz Annahme Teller 27 cm; optional zweites Foto schräg für Volumen.
3. **Ketten-Datenbank:** Collection `ketten_gerichte` (kette, gericht, portion, naehrwerte, quelle_url) — Startbestand von Hand (McDonald's, Burger King, Vapiano, L'Osteria, dean&david, Subway); erkennt das Modell die Kette oder der Kunde wählt sie aus einer Chip-Liste, werden exakte Werte statt Schätzung gebucht (`quelle=kette`).
4. **Lernende Korrektur:** Collection `foto_schaetzungen` `kunde_id, datum, komponenten_geschaetzt[], komponenten_gebucht[], faktor (gebucht/geschaetzt kcal), sicherheit, coach_urteil (passt|zu_hoch|zu_niedrig|null)`. Ab 5 Buchungen wird der Median-Faktor je Kunde als `kalibrierung` im Profil geführt und auf neue Schätzungen angewandt (Anzeige "an dich angepasst"). Coach-Stichprobe: wöchentlich 5 zufällige Foto-Buchungen im Cockpit (M5) mit Ein-Tipp-Urteil; Urteile fließen in einen globalen Faktor je Gerichtstyp.
5. **Unsicherheit anzeigen:** Ausgabe als Spanne (Sicherheit hoch ±10 %, mittel ±20 %, niedrig ±30 %), Regler startet in der Mitte. Bei "niedrig" zwei Pflicht-Rückfragen vor dem Buchen: "Öl/Dressing dabei?" und "Brot/Beilage dabei?" (die zwei häufigsten Unterschätzungen).
6. **Modell:** Few-Shot mit den 10 Referenzfotos im Prompt (Komponenten + gewogene Gramm), `sauce_oel` als Pflichtfeld je Komponente (nie null), bei Sicherheit "niedrig" zweiter Durchlauf mit Temperatur 0 und Mittelung.

Zielwerte: ±15–20 % bei Schätzungen (Referenztest: ≥ 8 von 10 unter 20 %), Ketten-Gerichte exakt, Kalibrierung senkt die persönliche Abweichung nach 4 Wochen messbar (im Cockpit als Kennzahl je Kunde).

### Abnahme
Plan aktivieren → /heute zeigt Montag vorbelegt → 2 Mahlzeiten abhaken → Ring stimmt mit Summe überein → "Ich hatte einen Apfel" im Chat → Eintrag erscheint auf /heute ohne Reload → Foto eines Tellers → Vorschau-Karte mit BLS-basierten Werten → Buchen legt Eintrag mit quelle=foto an.

---

## M2 — Rezeptbibliothek + Einkaufsliste

### Daten
**rezepte** — kuratierte Bibliothek (Coach) + freigegebene Buddy-Rezepte
`titel, quelle (coach|buddy), kunde_id? (null = für alle), tags[] (vegan, glutenfrei, schnell, …), portionen, zeit_min, zutaten[{menge_g, name, bls_code?}], schritte[], naehrwerte_pro_portion {kcal, protein_g, fett_g, kh_g}, bild_url?, freigegeben (bool), erstellt_am`
Nährwerte werden beim Speichern aus zutaten × BLS berechnet, nicht vom Modell übernommen.

### Funktionen
- Buddy-Rezepte aus v1 (`plaene.typ=rezept`) werden beim Speichern zusätzlich als `rezepte` mit `quelle=buddy, freigegeben=false` angelegt; Coach gibt frei → für alle sichtbar.
- **Tausch:** im Wochenplan je Gericht "Tauschen" → Buddy-Tool `gericht_tauschen(plan_id, tag, mahlzeit, wunsch?)`, Filter: gleiche Mahlzeit, ±100 kcal, Profilregeln.
- **Einkaufsliste:** `GET /plaene/{id}/einkaufsliste` → Zutaten aller Tage aggregiert nach Kategorie (BLS-Hauptgruppe), Mengen addiert, abhakbar (Collection einkaufslisten), Export als Text für WhatsApp-Teilen.
- Bibliothek-Seite /rezepte mit Filter-Chips; "In meinen Plan" fügt ein Rezept in einen Tag ein.

### Abnahme
Wochenplan → Einkaufsliste zeigt aggregierte Mengen ("Hähnchenbrust 900 g") → Gericht tauschen ersetzt genau eine Zelle → Coach gibt Buddy-Rezept frei → Kunde B sieht es in /rezepte.

---

## M3 — Check-ins + Körperdaten

### Daten
**messungen** `kunde_id, datum, gewicht_kg?, umfaenge {taille, huefte, brust, oberarm, oberschenkel}?, fotos[] (Dateipfad, privat), erstellt_am`
**checkins** `kunde_id, woche (ISO), antworten {schlaf 1-5, energie 1-5, hunger 1-5, stress 1-5, training_einheiten, plan_eingehalten 1-5, freitext}, buddy_zusammenfassung, coach_kommentar?, erstellt_am`
**checkin_vorlage** (Coach-editierbar wie die Buddy-Regeln): Fragen, Skalen, Wochentag.

### Funktionen
- Gewicht täglich in 10 Sekunden (Startseite, ein Feld), Umfänge/Fotos wöchentlich.
- Wochen-Check-in als 6-Fragen-Screen; nach Absenden schreibt der Buddy eine 3-Satz-Einordnung und schlägt bei Bedarf eine Zielanpassung vor — **Anpassung nur nach Coach-Freigabe** (Coach-Cockpit M5, bis dahin Aufgabe per Mail).
- Verlaufs-Charts: Gewicht 7-Tage-Mittel, Umfänge, Trefferquote aus M1.
- Fotos: nur Kunde und Coach sehen sie; Speicherung verschlüsselt auf Hetzner, nie an die KI.

### Buddy-Erweiterung
Systemprompt: Gewichtstrend 4 Wochen, letzter Check-in, offene Coach-Kommentare. Tool: `messung_speichern(datum, gewicht_kg)` für "wiege heute 55,4".

### Abnahme
4 Wochen Beispieldaten → Chart plausibel → Check-in absenden → Buddy-Einordnung erscheint < 30 s → Coach kommentiert → Kommentar erscheint beim Kunden.

---

## M4 — Erinnerungen + Onboarding-Strecke

- **Kanäle:** Web-Push (PWA) + E-Mail; WhatsApp später über den Cloud-API-Kanal des Pipeline CRM (kein zweiter WA-Stack hier).
- **Fest verdrahtete Abläufe (kein Workflow-Builder, wie im CRM beschlossen):**
  - Onboarding: Tag 0 Willkommen + Profil, Tag 1 erster Wochenplan, Tag 3 "Wie läuft's?", Tag 7 erster Check-in
  - Täglich 20:00: "Tag abschließen" wenn < 2 Mahlzeiten abgehakt
  - Wöchentlich (Wochentag aus checkin_vorlage): Check-in fällig, Erinnerung nach 24 h
  - Sonntag 17:00: "Neuen Wochenplan holen?" wenn aktiver Plan ausläuft
  - Inaktiv 5 Tage: freundliche Nachricht vom Buddy; 10 Tage: Aufgabe für Coach
- Scheduler-Worker im Backend (APScheduler), Collection `benachrichtigungen` mit Status, Ruhezeiten 22–7 Uhr, Opt-out je Kanal im Profil.
- PWA: manifest + Service Worker, "Zum Home-Bildschirm" auf iPhone.

---

## M5 — Coach-Cockpit

- Kundenliste mit **Ampel**: grün (Bilanz ≥ 5/7 Tage im Korridor, Check-in erledigt), gelb (3–4 Tage oder Check-in überfällig), rot (< 3 Tage oder 5 Tage inaktiv oder Gewicht gegen Ziel 2 Wochen).
- Kunde-Detail: Woche auf einen Blick (Bilanz, Gewicht, Check-in-Antworten, Buddy-Chats), Aktionen: Ziel anpassen (mit Buddy-Vorschlag aus M3 übernehmen/ablehnen), Notiz an Buddy, Nachricht an Kunde.
- Montag 8:00 Wochenreport per Mail an Coach: 5 Zeilen je roter/gelber Kunde.
- Kosten: Tokens × Preis aus ENV je Kunde/Monat.

---

## M6 — Training

- **uebungen** (Bibliothek, Coach-gepflegt; Video-Link, Muskelgruppen), **trainingsplaene** (Wochen-Split, Sätze/Wdh/Pause), **trainingslog** (Datum, Übung, Sätze mit Gewicht/Wdh).
- Buddy bekommt Trainingstage in den Systemprompt (Pre-/Post-Workout-Mahlzeiten passen sich an) und ein Tool `training_loggen`.
- Erst bauen, wenn M1–M5 drei Monate laufen — oder streichen, falls das Ernährungscoaching ohne Training verkauft wird.

---

## Technische Leitplanken für alle Module
- Jedes Modul = eigener Router unter backend/routes/, eigene Collections, eigene Tests; Buddy-Tools in backend/ki/tools/<modul>.py registrieren; Systemprompt-Blöcke in backend/ki/kontext/<modul>.py.
- Kein Modul greift direkt auf ein anderes zu — nur über Funktionen im jeweiligen Modul (kein Cross-Collection-Query in Routen).
- Prompt-Regeln je Modul als eigener Abschnitt in prompts/rezept_buddy.md, damit der Coach sie im Editor sieht.
- Datenschutz: Fotos und Freitext-Check-ins nie an die KI; Kunde kann jedes Modul-Datum selbst löschen; Export als JSON auf Anfrage.

## Was das kostet, grob (Claude-Code-Aufwand, nicht Geld)
M1 ~2 Tage (+1 Tag Foto inkl. Genauigkeits-Paket) · M2 ~2 Tage · M3 ~2 Tage · M4 ~1,5 Tage · M5 ~1,5 Tage · M6 ~3 Tage. Zusammen ein solider Natty-Gains-Ersatz in 2–3 Wochen Abendarbeit, wenn nebenher Vertrieb läuft.
