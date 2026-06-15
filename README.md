# TeamTracks

TeamTracks ist eine Webapp zum synchronen Abspielen mehrerer konvertierter Audio-Stems im Browser. Das Backend verwaltet Songs, WAV-Uploads, WAV-Imports, Conversion-Jobs, Manifest-Erzeugung und Media-Serving. Das Frontend bietet Admin-Workflows und einen Player mit Mute, Seek und Fokusmodus.

## Start mit Docker Compose

Voraussetzungen:

- Docker mit Docker Compose v2
- Freie lokale Ports `8000` und `5173`

Start:

```sh
cp .env.example .env
# ADMIN_PASSWORD und ADMIN_SESSION_SECRET in .env ersetzen
docker compose up --build
```

Danach:

- Frontend: http://localhost:5173
- User-Ansicht: http://localhost:5173/songs
- Admin-Login: http://localhost:5173/admin/login
- Backend Healthcheck: http://localhost:8000/health
- API und Media liegen unter `http://localhost:8000/api/...` und `http://localhost:8000/media/...`

Beim Start fuehrt der `migrate`-Service `alembic upgrade head` aus. Backend und Worker starten erst nach erfolgreicher Migration.

Persistente Daten liegen in Docker-Volumes:

- `db_data`: SQLite-Datenbank
- `media_storage`: hochgeladene WAVs und konvertierte M4A-Dateien
- `source_imports`: optionaler Import-Ort fuer lokale WAV-Quellen

Zum Beenden:

```sh
docker compose down
```

Zum Zuruecksetzen aller Daten:

```sh
docker compose down -v
```

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

## Beispiel-Workflow

1. `docker compose up --build` starten.
2. Unter `/admin/login` anmelden und einen Song anlegen.
3. In der Admin-Ansicht WAV-Stems hochladen.
4. Fuer jeden Stem Rolle und Name setzen.
5. Conversion starten.
6. Warten, bis die Stems den Status `ready` haben und der Song abspielbereit ist.
7. Der Song erscheint nun in der oeffentlichen Suche; dort den Player oeffnen.
8. Warten, bis alle Stems automatisch geladen und dekodiert wurden.
9. `Play` klicken. Beim ersten Klick wird der Audio-Kontext direkt aus der Benutzerinteraktion gestartet.
10. Danach Play, Pause, Stop, Seek, Mute und Fokus verwenden.
