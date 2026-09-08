# Startbefehl für Claude Code (Fortsetzung)

Schritte 1–7 sind gebaut (siehe STAND.md). Im Ordner `ptl-rezept-buddy` `claude` starten und einfügen:

---
Lies CLAUDE.md, SPEC.md, STAND.md und prompts/rezept_buddy.md. Backend und Frontend stehen. Bring es zuerst lokal zum Laufen:
1. `cp .env.example .env` — ich trage ANTHROPIC_API_KEY und COACH_PASSWORT ein.
2. `docker compose up -d mongo`, dann Backend (`cd backend && pip install -r requirements.txt && uvicorn main:app --reload`) und Frontend (`cd frontend && npm install && npm run dev`).
3. BLS-CSV liegt unter backend/data/bls4.csv → `python scripts/bls_import.py data/bls4.csv`. Wenn die Spalten nicht erkannt werden, passe SPALTEN in scripts/bls_import.py an.
4. Öffne http://localhost:5173/coach/login, leg mich als Testkunde an, nimm den angezeigten Magic-Link, fülle das Profil (vegan, Nüsse, Fettabbau) und fordere einen Wochenplan an.
Dann prüfe die Abnahmekriterien aus SPEC.md §9 und melde mir jeden Verstoß. Ändere nichts am Design, bevor ich die PTL-Farben liefere.
---

Danach: "Schritt 8" = Deploy auf Hetzner (Caddy, Subdomain, nächtlicher Dump auf die Synology).

## Vor dem Start bereitlegen
- Anthropic API-Key
- BLS 4.0 CSV (blsdb.de, CC BY 4.0)
- optional SMTP-Zugang (ohne: Magic-Link wird im Coach-Bereich angezeigt)
- PTL-Farben/Schrift → frontend/src/index.css, Block @theme
