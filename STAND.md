# Baustand

## 06.09.2026 — Schritte 1–7 (Backend + Frontend) fertig, 23 Backend-Tests grün, Frontend baut
Gebaut (von Claude im Chat, ohne Mac):
- Repo-Grundgerüst, docker-compose (mongo/backend/frontend), Config aus ENV, DB-Indexe, Coach-Seed beim Start
- BLS-Import-Skript mit toleranter Spaltenerkennung (`scripts/bls_import.py <csv>`), Endpoint `/api/lebensmittel?q=`
- Profil-Modell inkl. Fallback-Rechner kcal (Mifflin-St Jeor) / Protein; Kunde darf Kalorien-/Proteinziel nicht selbst setzen, nur der Coach
- Systemprompt-Builder (Regeln aus prompts/rezept_buddy.md + Profilblock + Coach-Notizen)
- Agent mit Anthropic-Streaming und Tool `naehrwerte_suchen` (max. 6 Runden)
- Parser: JSON-Blöcke wochenplan/rezept → Collection plaene, Text ohne JSON an den Kunden
- Chat-Routen mit SSE (Events: text, plan_gespeichert, fertig, fehler); Vorschlagsfragen je Ziel
- Auth: Magic-Link (30 Min, einmalig), Coach-Login, Cookie-JWT, Rollen-Trennung
- Coach-Routen: Kunden anlegen/deaktivieren/löschen (Hard-Delete), Profil setzen, Chats mitlesen, Notiz senden, Prompt-Editor mit Verlauf, Token-Kosten je Monat

Frontend (React 18 + Vite + TS + Tailwind 4, Mobile-first, keine externen UI-Libs):
- Kunde: /login (Magic-Link), /profil (Ziel-Kacheln, Chips für Unverträglichkeiten, Tagesziel-Anzeige), /chat mit SSE-Streaming, Vorschlagsfragen, Wochenplan als Tages-Streifen (Mo/Di/…, Tagessumme kcal/Protein), Rezept-Karte; Chat-Liste als Seitenmenü; /plaene mit Favoriten
- Coach: /coach/login, Kundenliste + Anlegen (zeigt Magic-Link, falls kein SMTP), Kunde mit Tabs Chats / Profil & Ziele (Kalorien-/Proteinziel, Notizen für den Buddy, DSGVO-Löschen), Chat mitlesen (5-s-Refresh, Token-Zähler) + Notiz senden, Regeln-Editor
- Design: eine Schrift (Avenir Next/Helvetica-Stack), Off-White #F7F5EF, Tinte #17201B, Akzent Wald #1F5A3A; noch KEINE echten PTL-Farben – in frontend/src/index.css unter @theme austauschen
- Kleiner eigener Markdown-Renderer (fett/kursiv/Listen), kein HTML-Passthrough

## Offen
- Visuelle Abnahme am echten Gerät (hier ohne Browser gebaut) — Feinschliff Abstände/Farben nach PTL-CI
- Schritt 8: Deploy Hetzner (Caddy, Subdomain, Backup auf Synology)
- Erster Live-Test mit echtem API-Key und BLS-Daten (Abnahmekriterien §9 prüfen, v.a. "vegan + Nüsse" 10 Stichproben)
- Noch nicht gebaut/entschieden: Preis je Mio. Tokens für die Kostenanzeige, Anthropic-DPA

## 08.09.2026 — Vorbereitung Deploy (Claude Code am Mac)
- Tests lokal mit Python 3.11 gefahren: bcrypt 5.0 bricht passlib 1.7.4 (Coach-Login wuerde beim
  Hashen abstuerzen, auch im Docker-Build, weil requirements unpinned waren) → `bcrypt<4.1` gepinnt.
- Nachrichten-Sortierung in routes/chat.py auf (erstellt_am, _id) erweitert: bei gleichem
  Millisekunden-Zeitstempel war die Reihenfolge Coach-Notiz/Kundenfrage zufaellig (Test war rot).
- Jetzt 23/23 Tests gruen.
- Deploy-Befund: Der Hetzner-Server laeuft mit Coolify/Traefik (CRM-Repo: docker-compose.coolify.yml),
  NICHT mit einem Host-Caddy + systemctl wie in deploy/Caddyfile angenommen. Weg: Coaching-App als
  eigene Coolify-Ressource (Docker Compose), Domain coaching.ptl-pforzheim.de auf den Frontend-Service;
  Backend-Proxy im nginx des Frontends (SSE ohne Puffer dort sicherstellen).

## 08.09.2026 — LIVE unter https://coaching.ptl-pforzheim.de (Coolify)
- Coolify-Projekt "PTL Coaching", Ressource aus GitHub-Repo phiphilip96-cyber/ptl-rezept-buddy
  (Build Compose, docker-compose.coolify.yml), Domain auf Service frontend, Push auf main deployt.
- /api/gesund 200, Coach-Login geprueft. Secrets: JWT_SECRET zufaellig (bleibt),
  ANTHROPIC_API_KEY PLATZHALTER (echten Schluessel in Coolify eintragen, dann Redeploy),
  COACH_PASSWORT Testwert (in Coolify aendern, main.py zieht den Hash beim Start nach).
- Scheduled Task "Mongo-Backup naechtlich" 03:30 (mongodump ins Volume backups_data, 14 Tage), Testlauf ok.
- deploy/Caddyfile + deploy/docker-compose.coaching.yml sind nur noch Referenz (Server laeuft unter Coolify/Traefik).
- Offen: BLS-Import (bls4.csv ins Volume bls_data, `python scripts/bls_import.py /data/bls4.csv`
  im Backend-Terminal von Coolify), erster Live-Test mit echtem Key, PTL-Farben.

## 08.09.2026 — v2-Module M1, M3, Einkaufsliste, Coach-Ampel (39 Tests gruen)
- M1 Tagebuch: /heute als Startseite (Ring kcal, Balken Protein, Mahlzeiten abhaken, + Eintrag per BLS-Suche
  oder frei, Gewicht in 10 s), Wochenplan per "Ab Montag aktiv" in den Tag vorbelegt (kunden.aktiver_plan).
- M3 Check-ins + Koerperdaten: /ich mit Gewichtskurve (7-Tage-Mittel), Wochen-Check-in (6 Fragen), Buddy-Einordnung
  in 3 Saetzen (kurz.py, scheitert lautlos ohne Key), Coach-Kommentar dazu.
- M2-Teil: Einkaufsliste am Plan (Rezept direkt aus Zutaten, Wochenplan per Buddy-Aufruf, gecacht), Teilen/Kopieren.
- Buddy: drei Schreib-Werkzeuge (eintrag_anlegen, tag_lesen, messung_speichern), Kontextbloecke TAGEBUCH und
  KOERPERDATEN im Systemprompt, neuer Regelabschnitt in prompts/rezept_buddy.md, SSE-Event "aktion".
- Coach: Ampel je Kunde (gruen/gelb/rot/grau, routes/cockpit.py) in der Liste, Tab "Woche" mit Bilanz 7 Tage,
  Gewicht, letztem Check-in und Kommentar.
- Tab-Leiste Heute · Chat · Plaene · Ich. Nicht gebaut: Foto-Erfassung (M1b), Barcode, Fotos im Check-in,
  Erinnerungen (M4), Training (M6).
