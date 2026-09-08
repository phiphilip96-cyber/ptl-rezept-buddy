# Brief für Claude Code (CRM-Repo "App P1 OS") — Host-basiertes Routing für PTL

---
Das Pipeline CRM soll zusätzlich unter landingpage.ptl-pforzheim.de, leads.ptl-pforzheim.de erreichbar sein. Baue eine kleine Host-Weiche, ohne die bestehenden Routen unter crm.p1-pforzheim.de zu verändern:

1. Konfiguration (ENV oder config-Datei): Mapping Host → Mandant + Startroute:
   - crm.p1-pforzheim.de → mandant p1, Startroute / (wie bisher)
   - landingpage.ptl-pforzheim.de → mandant ptl, Startroute /ptl (die bestehende 12-Wochen-Landingpage, aktuell unter crm.p1-pforzheim.de/ptl), Rechner unter /rechner
   - leads.ptl-pforzheim.de → mandant ptl, Startroute /ptl/board (Lead-Board/Dienst); nur eingeloggte Mitarbeiter
2. Backend-Middleware liest den Host, setzt request.state.mandant; öffentliche PTL-Endpunkte (/api/public/ptl/lead, Tracking) akzeptieren die PTL-Hosts in CORS; interne CRM-Routen antworten auf den PTL-Hosts mit 404 (keine interne Oberfläche unter der Kundendomain).
3. Frontend: beim Laden Host prüfen und die Startroute setzen; auf den PTL-Hosts keine CRM-Navigation rendern, Titel "Personal Training Lounge", Favicon PTL, Design aus dem Skill p1-ptl-design (references/ptl.md). Canonical-Tag auf https://landingpage.ptl-pforzheim.de/ setzen; die Wix-Seite ptl-pforzheim.de bleibt die Hauptseite und verlinkt auf die Landingpage.
4. Impressum/Datenschutz bleiben Links auf www.ptl-pforzheim.de/impressum und /datenschutz (Wix-Seite bleibt bestehen) — nichts ändern.
5. Tests: Host-Weiche (3 Hosts), 404 für interne Routen auf PTL-Hosts, Canonical im HTML.
Nach dem Deploy: https://landingpage.ptl-pforzheim.de muss die PTL-Landingpage zeigen, Formular muss einen Lead mit mandant=ptl anlegen.
---
