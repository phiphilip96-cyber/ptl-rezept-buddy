# Brief für Claude Code — Deploy Coaching-App + PTL-Subdomains

Terminal am Mac, `claude` starten, einfügen:

---
Ich deploye die Coaching-App (Repo ~/ptl-rezept-buddy, siehe CLAUDE.md dort) auf meinen Hetzner-Server 49.13.227.244, auf dem schon das Pipeline CRM (Repo "App P1 OS") mit Caddy läuft. DNS ist gesetzt: coaching., landingpage., leads.ptl-pforzheim.de → 49.13.227.244.

Mach das in dieser Reihenfolge, nach jedem Schritt kurz Status und warten auf mein Go:

1. Prüfe per `dig +short coaching.ptl-pforzheim.de` dass die IP stimmt. Prüfe per SSH, welche Ports das CRM-Backend und Caddy aktuell nutzen (`ss -tlnp`, `cat /etc/caddy/Caddyfile`). Passe die Portnummern in deploy/Caddyfile an das an, was wirklich läuft — die 8001 dort ist eine Annahme.
2. Lege /opt/coaching an, kopiere das Repo hin (rsync, ohne node_modules/.env), lege .env aus .env.example an — ANTHROPIC_API_KEY, JWT_SECRET (zufällig, 48 Zeichen), COACH_EMAIL, COACH_PASSWORT frage mich ab, tippe sie nicht selbst. APP_URL=https://coaching.ptl-pforzheim.de. Kopiere deploy/docker-compose.coaching.yml nach /opt/coaching/docker-compose.yml und starte `docker compose up -d --build`. Prüfe `curl localhost:8010/api/gesund`.
3. Ergänze den Caddyfile-Block für coaching.ptl-pforzheim.de (aus deploy/Caddyfile, mit flush_interval -1 für SSE), `caddy validate`, `systemctl reload caddy`. Prüfe https://coaching.ptl-pforzheim.de/api/gesund und dass die Login-Seite lädt.
4. BLS-Import: Datei backend/data/bls4.csv liegt im Repo-Ordner am Mac → hochkopieren, `docker compose exec backend python scripts/bls_import.py data/bls4.csv`.
5. Backup: deploy/backup-coaching.sh nach /opt/coaching/backup.sh, chmod +x, Cron 03:30 täglich. Der Synology-rsync-Pull (Aufgabenplaner) bekommt /opt/backups/coaching zusätzlich zum Paperless-Pfad — sag mir, welche Zeile ich dort ergänzen muss.
6. Ergänze den Caddy-Block für landingpage.ptl-pforzheim.de und leads.ptl-pforzheim.de → CRM-Backend. Im CRM-Repo: Host-basiertes Mandanten-Routing ergänzen (siehe BRIEF-crm-hosts.md), deployen, prüfen dass https://landingpage.ptl-pforzheim.de die PTL-Landingpage zeigt.

Die Hauptdomain ptl-pforzheim.de bleibt bei Wix — keinen Caddy-Block dafür anlegen.
---
