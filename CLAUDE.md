# PTL Rezept-Buddy — Projektgedächtnis für Claude Code

## Was das ist
Prototyp eines KI-Ernährungscoaches für die Kunden der Personal Training Lounge Pforzheim (PTL).
Kunde hat ein Profil (Ziel, Gewicht, Ernährungsart, Unverträglichkeiten, Kalorien-/Proteinziel),
chattet mit dem "Rezept-Buddy" und bekommt Wochenpläne und Einzelrezepte, die zum Profil passen.
Coach (Philip) sieht alle Chats mit. Erstes Modul der späteren PTL-Coaching-Plattform (Natty-Gains-Nachbau).

## Stack (verbindlich)
- Backend: Python 3.12, FastAPI, Motor (MongoDB async), Anthropic SDK
- Frontend: React 18 + Vite, TypeScript, Tailwind — Mobile-first (Kunden nutzen iPhone)
- DB: MongoDB (lokal per Docker, prod auf Hetzner neben dem Pipeline CRM)
- LLM: Anthropic Messages API, Modell per ENV `ANTHROPIC_MODEL` (Default: claude-sonnet-4-6), Streaming
- Nährwerte: Bundeslebensmittelschlüssel BLS 4.0 (CC BY 4.0), importiert als Collection `lebensmittel`
- Auth: Magic-Link per E-Mail für Kunden, Coach-Login mit Passwort. Keine Drittanbieter-Auth.

## Repo-Layout
backend/
  main.py              FastAPI-App, Router-Registrierung, CORS
  config.py            ENV (MONGO_URL, ANTHROPIC_API_KEY, ANTHROPIC_MODEL, JWT_SECRET, MAIL_*)
  db.py                Motor-Client, Index-Anlage
  models/              Pydantic-Modelle (siehe SPEC.md §2)
  routes/
    auth.py            Magic-Link, Coach-Login
    profil.py          Kundenprofil lesen/schreiben
    chat.py            Chat-Endpunkte, SSE-Streaming
    plaene.py          Gespeicherte Pläne/Rezepte
    coach.py           Coach-Ansicht: Kundenliste, Chats mitlesen, Kommentare
    bls.py             Lebensmittelsuche/Nährwerte
  ki/
    systemprompt.py    Baut den Systemprompt aus Profil + prompts/rezept_buddy.md
    agent.py           Anthropic-Aufruf, Streaming, Tool "naehrwerte_suchen"
    parser.py          Erkennt Wochenplan-/Rezept-Blöcke in der Antwort und speichert sie strukturiert
  scripts/
    bls_import.py      CSV → lebensmittel-Collection
  tests/
frontend/
  src/pages/           Login, Profil, Chat, Plaene, Coach
  src/components/      ChatBubble, WochenplanTabelle, RezeptKarte, Vorschlagsfragen
prompts/
  rezept_buddy.md      Verhaltensregeln des Buddys (vom Coach editierbar, KEIN Code)
docker-compose.yml     mongo + backend + frontend

## Regeln
- Sprache im gesamten UI und in allen Feldnamen: Deutsch (z. B. `ernaehrungsart`, `unvertraeglichkeiten`).
- Nie den Kunden an einen anderen Anbieter verweisen; der Buddy spricht als Teil von PTL.
- Kein medizinischer Rat. Bei Krankheit/Medikamenten → Hinweis "bitte mit Coach besprechen".
- Der Buddy erfindet keine Nährwerte: Kalorien/Protein pro Gericht kommen aus dem Tool `naehrwerte_suchen` (BLS) oder werden als "ca." markiert.
- Jede Antwort, die einen Wochenplan oder ein Rezept enthält, wird strukturiert gespeichert (nicht nur als Text).
- Coach kann jeden Chat lesen und dem Kunden dazu eine Notiz schicken.
- Tests: pytest für Parser, Systemprompt-Builder und Routen (mit Anthropic-Mock). Kein Test ruft die echte API.
- Kleine, überprüfbare Schritte. Nach jedem Schritt: `pytest` grün und Frontend baut.

## Bau-Reihenfolge
Siehe SPEC.md §8. Nicht vorgreifen. Erst Schritt 1–3 (Backend + Chat ohne UI-Politur), dann UI.
