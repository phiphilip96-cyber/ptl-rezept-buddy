# PTL Rezept-Buddy

KI-Ernährungscoach für PTL-Kunden. Spezifikation in SPEC.md, Projektgedächtnis für Claude Code in CLAUDE.md.

## Lokal starten
```bash
cp .env.example .env            # Keys eintragen (ANTHROPIC_API_KEY, COACH_PASSWORT, ggf. MAIL_*)
docker compose up -d mongo
cd backend && pip install -r requirements.txt
python scripts/bls_import.py data/bls4.csv     # einmalig, BLS 4.0 CSV von blsdb.de
uvicorn main:app --reload --port 8000
```
API-Doku: http://localhost:8000/docs · Coach-Login: POST /api/auth/coach/login mit COACH_EMAIL/COACH_PASSWORT aus .env

Ohne MAIL_HOST werden Magic-Links nicht gemailt, sondern in der Konsole ausgegeben bzw. beim Anlegen eines Kunden (POST /api/coach/kunden) direkt in der Antwort zurückgegeben — reicht zum Testen.

## Tests
```bash
cd backend && pytest
```
Laufen ohne MongoDB und ohne Anthropic-API (mongomock + gemockter Client).
