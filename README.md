# TeamTracks

TeamTracks ist eine Webapp zum synchronen Abspielen mehrerer konvertierter Audio-Stems im Browser. Das Backend verwaltet Organisationen, Songs, WAV-Uploads, Conversion-Jobs, Manifest-Erzeugung und geschuetztes Media-Serving. Das Frontend bietet Organisationsauswahl, Plattformverwaltung, Organisations-Admin-Workflows und einen Player mit Mute, Seek und Fokusmodus.

## Erststart mit Docker Compose

Voraussetzungen:

- Docker mit Docker Compose v2
- Freie lokale Ports `8000` und `5173`
- Eine leere Installation. Die Organisations-Einfuehrung migriert keine alten globalen Daten.

Start:

```sh
cp .env.example .env
# PLATFORM_ADMIN_PASSWORD und AUTH_SECRET in .env ersetzen
docker compose up --build
```

Danach:

- Frontend: http://localhost:5173
- Organisationsauswahl: http://localhost:5173/organizations
- Plattform-Admin: http://localhost:5173/platform/login
- Backend Healthcheck: http://localhost:8000/health
- API und Media liegen unter `http://localhost:8000/api/...` und `http://localhost:8000/media/...`

Beim Start fuehrt der `migrate`-Service `alembic upgrade head` aus. Backend und Worker starten erst nach erfolgreicher Migration.

Persistente Daten liegen in Docker-Volumes:

- `db_data`: SQLite-Datenbank
- `media_storage`: Organisationsbilder, hochgeladene WAVs und konvertierte M4A-Dateien

Zum Beenden:

```sh
docker compose down
```

Zum Zuruecksetzen aller Daten:

```sh
docker compose down -v
```

## Konfiguration

Vor einem Produktivstart muessen mindestens `PLATFORM_ADMIN_PASSWORD`, `AUTH_SECRET`, `CORS_ORIGINS` und `COOKIE_SECURE` angepasst werden.

| Variable | Bedeutung | Produktivwert |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy-Datenbank-URL. Der Compose-Standard nutzt SQLite in `/data/db/teamtracks.db`. | Persistente Datenbank im Zielsystem, mit Backup eingeschlossen. |
| `STORAGE_ROOT` | Wurzelverzeichnis fuer Organisationsbilder, WAV-Uploads und konvertierte Audio-Dateien. | Persistentes Volume oder gemounteter Storage, mit Backup eingeschlossen. |
| `CORS_ORIGINS` | Erlaubte Frontend-Origin-Liste als JSON-Array. | Ausschliesslich die oeffentliche HTTPS-Origin des Frontends, z. B. `["https://teamtracks.example.com"]`. |
| `STEM_CACHE_MAX_AGE_SECONDS` | Private Cache-Laufzeit fuer geschuetzte Audioantworten. | Kann lang bleiben, weil Media-URLs versioniert sind und jede Antwort serverseitig autorisiert wird. |
| `PLATFORM_ADMIN_PASSWORD` | Globales Passwort fuer die Plattformverwaltung. | Langes, zufaelliges Passwort aus einem Passwortmanager. Nicht der Beispielwert. |
| `AUTH_SECRET` | Kryptografisches Secret fuer Browser-Sessions und Invite-Signaturen. | Mindestens 32 zufaellige Bytes, z. B. mit `openssl rand -hex 32`. Nicht rotieren, ohne aktive Sessions und Invite-Links bewusst zu widerrufen. |
| `PLATFORM_ADMIN_SESSION_HOURS` | Laufzeit der separaten Plattform-Admin-Session. | Kurz halten, z. B. `8` bis `12`; maximal erlaubt sind `720`. |
| `COOKIE_SECURE` | Setzt Session-Cookies auf HTTPS-only. | `true` hinter HTTPS. Nur lokale HTTP-Entwicklung nutzt `false`. |

Wenn das Frontend getrennt vom Backend gebaut und ohne denselben Origin oder Reverse Proxy ausgeliefert wird, muss beim Frontend-Build `VITE_API_BASE_URL` auf die oeffentliche Backend-Origin gesetzt werden. Beim mitgelieferten Development-Compose ist das nicht noetig, weil Vite `/api`, `/media` und `/health` an das Backend proxyt. Das Production-Nginx-Image proxyt diese Pfade ebenfalls an den Backend-Service.

## Organisationsmodell

Ein Browser kann gleichzeitig fuer mehrere Organisationen freigeschaltet sein. Diese Zugriffe liegen serverseitig in einer langlebigen Browser-Session. Das `HttpOnly`, `SameSite=Lax` Cookie wird bei jeder authentifizierten API- oder Media-Nutzung erneut auf zwei Jahre verlaengert. Der Plattform-Admin verwendet davon getrennt die kurzlebige Session unter `/api/platform/session`.

Organisationen werden ueber die Plattformverwaltung erstellt. Jede Organisation besitzt einen Namen, ein Bild, ein User-Passwort, ein Admin-Passwort und einen dauerhaften Invite-Link. Der Organisations-Admin kann Stammdaten, Bild, Passwoerter und Invite-Link unter `/org/{organization_id}/admin/organization` verwalten. Das Regenerieren des Invite-Links widerruft nur den alten Link, nicht bereits freigeschaltete Browser.

Alle Inhalts-APIs sind organisationsbezogen:

- User-Zugriffe: `/api/organizations/{organization_id}/songs`
- Admin-Zugriffe: `/api/organizations/{organization_id}/admin/...`
- Media-Zugriffe: `/media/organizations/{organization_id}/songs/...`

Geschuetzte Audiodateien werden mit privaten Cache-Headern ausgeliefert. Direkte Media-URLs funktionieren nur mit gueltigem User-Zugriff auf die passende Organisation. Lokale Player-Einstellungen werden pro Organisation im Browser gespeichert.

## Plattform-Admin-Workflow

1. `docker compose up --build` starten.
2. Im Browser `/platform/login` oeffnen.
3. Mit `PLATFORM_ADMIN_PASSWORD` anmelden.
4. Unter `/platform/organizations` eine Organisation mit Name, Bild, User-Passwort und Admin-Passwort anlegen.
5. Die Organisation in der oeffentlichen Organisationsauswahl oeffnen und mit dem User-Passwort freischalten.
6. Optional den Invite-Link im Organisations-Adminbereich kopieren und an Benutzer weitergeben. Benutzer nehmen ihn ueber `/invite/{token}` an.
7. Fuer Admin-Aufgaben in `/org/{organization_id}/admin/login` mit dem Admin-Passwort die Admin-Rolle freischalten.
8. Songs, Stems, Conversion und Einstellungen unter `/org/{organization_id}/admin/...` verwalten.
9. Zwischen freigeschalteten Organisationen ueber den Umschalter oben rechts wechseln.

Organisations-Admins sehen keine Plattformverwaltung. Plattform-Admins verwalten Organisationen global, arbeiten aber nicht automatisch als Organisations-User oder Organisations-Admin.

## Beispielablauf

1. Plattform-Admin unter `/platform/login` anmelden.
2. Unter `/platform/organizations` zwei Organisationen anlegen.
3. Erste Organisation auf der Organisationsauswahl mit User-Passwort freischalten.
4. In `/org/{organization_id}/admin/login` Admin freischalten.
5. Unter `/org/{organization_id}/admin/settings` Player- und Conversion-Einstellungen pruefen.
6. Unter `/org/{organization_id}/admin/songs` einen Song anlegen.
7. In der Song-Admin-Ansicht WAV-Stems hochladen.
8. Fuer jeden Stem Rolle und Name setzen.
9. Conversion starten und warten, bis die Stems den Status `ready` haben.
10. Song in `/org/{organization_id}/songs` oeffnen und Playback pruefen.
11. Invite-Link im Organisations-Adminbereich kopieren oder regenerieren.
12. Zweite Organisation freischalten und ueber den Organisationsumschalter wechseln.

## Backup und Loeschen

Regelmaessige Backups muessen Datenbank und Storage gemeinsam sichern. Bei Docker Compose sind das die Volumes `db_data` und `media_storage`. Beide gehoeren logisch zusammen, weil die Datenbank auf Dateien im Storage verweist.

Vor produktiven Backups sollten Backend und Worker gestoppt oder ein konsistentes Volume-Snapshot-Verfahren verwendet werden:

```sh
docker compose stop backend worker
# Snapshot oder Backup von db_data und media_storage erstellen
docker compose start backend worker
```

Das Loeschen einer Organisation entfernt die Datenbankdaten und das Storage-Verzeichnis dieser Organisation. Diese Aktion ist dauerhaft und sollte nur nach einem aktuellen Backup ausgefuehrt werden. Ein Plattform-Admin kann Organisationen unter `/platform/organizations` loeschen; ein Organisations-Admin kann die eigene Organisation unter `/org/{organization_id}/admin/organization` nach Admin-Passwort-Bestaetigung loeschen.

## Rollout mit frischen Volumes

Die Organisationsversion setzt frische Volumes voraus. Fuer eine bestehende alte Installation gibt es keine automatische Uebernahme globaler Bestandsdaten.

1. Bestehende Installation stoppen.
2. Falls Alt-Daten aufbewahrt werden muessen, Datenbank und Storage ausserhalb der neuen TeamTracks-Volumes archivieren.
3. Neue `.env` aus `.env.example` erstellen und Produktionswerte setzen.
4. Alte Compose-Volumes entfernen oder neue leere Volumes verwenden.
5. `docker compose up --build -d` starten.
6. `docker compose ps` pruefen.
7. `docker compose logs migrate backend worker` auf erfolgreiche Migration und Startfehler pruefen.
8. `curl -f http://localhost:8000/health` oder den oeffentlichen Healthcheck ausfuehren.

## Smoke-Test

Nach dem Rollout in der Zielumgebung:

1. `/platform/login` oeffnen und mit dem Plattform-Admin anmelden.
2. Organisation mit Bild, User-Passwort und Admin-Passwort anlegen.
3. Abmelden oder privaten Browser nutzen und Organisation per User-Passwort freischalten.
4. Invite-Link im Organisations-Adminbereich kopieren, in einem zweiten Browser annehmen und pruefen, dass die Songliste der Organisation geoeffnet wird.
5. Admin-Rolle freischalten.
6. Song anlegen, WAV-Stem hochladen, Stem benennen und Conversion starten.
7. Warten, bis der Stem `ready` ist.
8. Song im Player oeffnen, Laden der Audio-Datei und Playback pruefen.
9. Zweite Organisation anlegen und freischalten.
10. Zwischen beiden Organisationen wechseln und pruefen, dass Songs, Player-Zustand und Admin-Daten nicht organisationsuebergreifend sichtbar sind.
11. User-Passwort einer Organisation aendern und in einem anderen Browser pruefen, dass der alte Zugriff widerrufen wurde.
12. Testorganisation loeschen und pruefen, dass sie nicht mehr in der Auswahl erscheint.

## Tests

Backend-Test-Suite im Container:

```sh
docker compose run --rm backend-test
```

Frontend-Test-Suite im Container:

```sh
docker compose run --rm frontend-test
```

Direkt ohne Test-Profil funktionieren ebenfalls:

```sh
docker compose run --rm backend pytest
docker compose run --rm frontend npm test
```

Lokale Frontend-Pruefung:

```sh
cd frontend
npm test
npm run build
```

Die Sicherheits-Testabdeckung prueft Rollen- und Plattformgrenzen, Cross-Organization-Zugriffe fuer alle Inhaltsbereiche, Token-Manipulation, Path-Traversal, sensible Antwortfelder und die Schutz-Dependencies aller im OpenAPI-Schema sichtbaren Admin-Routen.
