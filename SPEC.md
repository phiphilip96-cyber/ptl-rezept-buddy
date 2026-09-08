# SPEC — PTL Rezept-Buddy (Prototyp v1)

Stand: 06.09.2026 · Auftraggeber: Philip Nguyen (PTL Pforzheim) · Vorbild: KI-Agent im LearningSuite-Kundenportal

## 1. Ziel
Ein Kunde meldet sich an, füllt sein Profil aus, chattet mit dem Rezept-Buddy und bekommt in unter 30 Sekunden
einen zum Profil passenden Wochenplan oder ein Rezept. Der Coach sieht alles mit. Fertig ist v1, wenn die
Abnahmekriterien in §9 erfüllt sind. Kein Training, keine Check-ins, kein Mindset-Bot in v1.

## 2. Datenmodell (MongoDB, Collections)

### kunden
| Feld | Typ | Hinweis |
|---|---|---|
| _id | ObjectId | |
| email | str, unique | Login per Magic-Link |
| vorname | str | |
| erstellt_am | datetime | |
| aktiv | bool | Coach kann deaktivieren |

### profile (1:1 zu kunden)
| Feld | Typ | Werte / Hinweis |
|---|---|---|
| kunde_id | ObjectId | |
| ziel | enum | `muskelaufbau` · `fettabbau` · `gewicht_halten` · `leistung` |
| gewicht_kg | float | aktuelles Gewicht |
| groesse_cm | int | |
| geburtsjahr | int | |
| geschlecht | enum | `weiblich` · `maennlich` · `divers` |
| aktivitaet | enum | `sitzend` · `leicht` · `mittel` · `hoch` |
| ernaehrungsart | enum | `alles` · `vegetarisch` · `vegan` · `pescetarisch` |
| unvertraeglichkeiten | list[str] | frei + Vorschläge: gluten, laktose, nüsse, soja, ei, fisch, schalentiere, histamin |
| abneigungen | list[str] | frei, z. B. "Pilze", "Koriander" |
| kalorienziel | int | vom Coach gesetzt; Fallback: Mifflin-St Jeor × Aktivität ± Ziel-Offset |
| proteinziel_g | int | vom Coach gesetzt; Fallback: 2,0 g/kg (muskelaufbau, fettabbau), 1,6 g/kg sonst |
| mahlzeiten_pro_tag | int | 3–5, Default 3 |
| kochzeit_max_min | int | Default 30 |
| budget | enum | `guenstig` · `normal` · `egal` |
| notizen_coach | str | frei, fließt in den Systemprompt |
| aktualisiert_am | datetime | |

### konversationen
`_id, kunde_id, titel, erstellt_am, letzte_nachricht_am`

### nachrichten
`_id, konversation_id, rolle (kunde|buddy|coach), inhalt (Markdown), tool_aufrufe (list), tokens_in, tokens_out, erstellt_am`
Rolle `coach` = Notiz des Coaches im Chat, wird dem Buddy als Kontext mitgegeben.

### plaene
`_id, kunde_id, nachricht_id, typ (wochenplan|rezept), titel, daten (siehe §5), erstellt_am, favorit (bool)`

### lebensmittel (BLS 4.0)
`bls_code, name_de, kcal_100g, protein_g, fett_g, kh_g, ballaststoffe_g, kategorie` — Textindex auf `name_de`.

### coaches
`_id, email, passwort_hash, name`

## 3. API (FastAPI, Präfix /api)

Öffentlich
- `POST /auth/magic-link` {email} → Mail mit Link, Antwort immer 200
- `GET  /auth/einloesen?token=` → setzt JWT-Cookie, Redirect /profil oder /chat
- `POST /auth/coach/login` {email, passwort} → JWT-Cookie

Kunde (JWT Rolle kunde)
- `GET/PUT /profil`
- `GET  /konversationen` · `POST /konversationen` {titel?}
- `GET  /konversationen/{id}/nachrichten`
- `POST /konversationen/{id}/nachrichten` {inhalt} → **SSE-Stream** (`text`-Events, dann `plan_gespeichert` {plan_id}, dann `fertig`)
- `GET  /vorschlagsfragen` → 4 Fragen, abhängig vom Profil (z. B. bei `fettabbau`: "Was ist ein sättigendes Abendessen unter 500 kcal?")
- `GET  /plaene` · `GET /plaene/{id}` · `PATCH /plaene/{id}` {favorit}
- `GET  /lebensmittel?q=` → Top 10 aus BLS

Coach (JWT Rolle coach)
- `GET  /coach/kunden` (mit letzter Aktivität, Anzahl Chats)
- `POST /coach/kunden` {email, vorname} → legt Kunde an + schickt Magic-Link
- `GET/PUT /coach/kunden/{id}/profil`
- `GET  /coach/kunden/{id}/konversationen` · `GET /coach/konversationen/{id}/nachrichten`
- `POST /coach/konversationen/{id}/notiz` {inhalt} → Nachricht mit Rolle `coach`
- `GET/PUT /coach/prompt` → liest/schreibt `prompts/rezept_buddy.md` (Versionierung: Kopie unter prompts/verlauf/YYYYMMDD-HHMM.md)

## 4. KI-Aufruf

### Systemprompt = drei Teile, in dieser Reihenfolge
1. `prompts/rezept_buddy.md` (Verhalten, Ton, Formatregeln — Coach-editierbar)
2. Profilblock (vom Builder erzeugt, Beispiel):
```
KUNDENPROFIL
Vorname: Lena · Ziel: Muskelaufbau · Gewicht: 56 kg · Größe: 165 cm · Alter: 29
Ernährungsart: alles · Unverträglichkeiten: Gluten · Abneigungen: Pilze
Tagesziel: ca. 2.100 kcal, 115 g Protein · 3 Mahlzeiten · max. 30 Min Kochzeit · Budget normal
Coach-Notizen: trainiert Mo/Mi/Fr abends, braucht Pre-Workout-Snack
```
3. Letzte Coach-Notizen aus dem Chat (Rolle coach), falls vorhanden.

### Verlauf
Letzte 20 Nachrichten der Konversation als `messages`. Rolle `coach` wird als user-Nachricht mit Präfix `[Notiz vom Coach]` übergeben.

### Tool `naehrwerte_suchen`
Input `{begriff: str}` → Top 3 aus `lebensmittel` mit kcal/Protein/Fett/KH pro 100 g.
Der Buddy nutzt es für Nährwertangaben; max. 6 Tool-Aufrufe pro Antwort, danach ohne Tool weiter.

### Parameter
`max_tokens 4000`, `temperature 0.7`, Streaming an, Timeout 60 s. Bei Fehler: Nachricht "Der Buddy ist gerade nicht erreichbar – bitte in einer Minute nochmal." und Fehler ins Log.

## 5. Strukturierte Ausgabe (Parser)
Der Buddy antwortet in Markdown, aber Wochenpläne und Rezepte zusätzlich in einem JSON-Block, den der Parser ausschneidet und in `plaene.daten` speichert. Der Kunde sieht nur die gerenderte Tabelle, nie das JSON.

```json
{"typ":"wochenplan","titel":"Glutenfreier Wochenplan Muskelaufbau",
 "tage":[{"tag":"Montag","mahlzeiten":[
   {"name":"Frühstück","gericht":"Protein-Porridge aus glutenfreien Haferflocken, Milch, Banane, Erdnussmus","kcal":520,"protein_g":28}
 ]}]}
```
```json
{"typ":"rezept","titel":"Hähnchen-Bowl mit Basmatireis","portionen":2,"zeit_min":25,
 "zutaten":[{"menge":"300 g","name":"Hähnchenbrust"}],"schritte":["…"],"kcal_pro_portion":610,"protein_g_pro_portion":48}
```
Parser-Regel: JSON zwischen ```json … ``` mit Feld `typ` ∈ {wochenplan, rezept}. Ungültiges JSON → Antwort wird trotzdem angezeigt, kein Plan gespeichert, Warnung ins Log.

## 6. Frontend (Mobile-first, iPhone-Breite zuerst)
Seiten
- **/login** — E-Mail-Feld, "Link schicken". Coach-Login unter /coach/login.
- **/profil** — Formular §2, Chips für Unverträglichkeiten, Speichern. Pflicht vor dem ersten Chat.
- **/chat** — Kopf: Avatar "Rezept-Buddy · aktiv". Oben 4 Vorschlagsfragen als Chips (verschwinden nach erster Nachricht). Bubbles, Streaming-Text, Wochenplan als scrollbare Tabelle (Tag × Mahlzeit), Rezept als Karte mit Zutaten/Schritte/Nährwerte. Button "Als Plan speichern" ist überflüssig — Speichern passiert automatisch; stattdessen ★ Favorit.
- **/plaene** — Liste gespeicherter Pläne/Rezepte, Favoriten oben, Detailansicht.
- **/coach** — Kundenliste → Kunde: Profil bearbeiten (inkl. Kalorien-/Proteinziel), Chats lesen, Notiz senden. Reiter "Buddy-Regeln" = Editor für prompts/rezept_buddy.md.

Design: PTL-CI (Farben/Schrift aus dem PTL-Auftritt übernehmen; bis Philip sie liefert: Schwarz/Weiß + ein Akzent). Keine Standard-Tailwind-Optik, kein Emoji-Overkill.

## 7. Nicht in v1
Training, Check-ins/Körperdaten-Verlauf, Push, Einkaufsliste, Barcode-Scan, Bezahlung, Mehrsprachigkeit, Mindset-Bot.
Einkaufsliste aus Wochenplan ist der naheliegendste v1.1-Schritt.

## 8. Bau-Reihenfolge (jeder Schritt einzeln abnehmbar)
1. Repo-Grundgerüst, docker-compose (mongo/backend/frontend), Config, DB-Indexe, Coach-Seed-Skript.
2. BLS-Import-Skript + `/lebensmittel?q=` (Test: "Haferflocken" liefert Treffer mit kcal).
3. Profil-Modell + Systemprompt-Builder + Fallback-Rechner für kcal/Protein (Tests mit 3 Beispielprofilen).
4. Chat-Backend: Konversationen, Nachrichten, Anthropic-Streaming, Tool `naehrwerte_suchen`, Parser → `plaene`. Test mit gemocktem Anthropic-Client.
5. Auth: Magic-Link (Mailversand per SMTP aus ENV), Coach-Login, JWT-Middleware.
6. Frontend Kunde: Login, Profil, Chat mit Streaming + Tabellen-/Rezept-Rendering, Pläne.
7. Frontend Coach: Kundenliste, Profil, Chats mitlesen, Notiz, Prompt-Editor.
8. Deploy: Docker auf Hetzner, Subdomain `coach.ptl-pforzheim.de`, HTTPS via Caddy/Traefik, Backup-Dump nachts auf die Synology (rsync-Pull, wie bei Paperless).

## 9. Abnahmekriterien
- Neuer Kunde per Coach-Anlage → Magic-Link → Profil → erste Antwort in < 30 s (Streaming sichtbar nach < 3 s).
- Profil "vegan + Nüsse + Fettabbau": Wochenplan enthält keine tierischen Produkte und keine Nüsse (10 Stichproben, 0 Verstöße).
- Wochenplan wird als Tabelle gerendert und liegt unter /plaene.
- Coach sieht den Chat innerhalb von 5 s nach Absenden und kann eine Notiz senden, die der Buddy in der nächsten Antwort berücksichtigt.
- Prompt-Änderung im Coach-Editor wirkt beim nächsten Chat ohne Neustart.
- `pytest` grün, keine echte API in Tests.
- Kosten: pro Wochenplan-Antwort < 0,05 € (Tokens loggen, Coach-Dashboard zeigt Summe/Monat).

## 10. DSGVO-Minimum für v1
Daten auf Hetzner (EU). Anthropic-AVV/DPA für die API abschließen (Region-Frage prüfen). Datenschutzhinweis im Profil: "Deine Profildaten werden zur Erstellung deiner Pläne an einen KI-Dienst übermittelt." Löschfunktion: Coach kann Kunde inkl. aller Chats/Pläne löschen (Hard-Delete).
