# Deploy on Unraid

This stack is a single FastHTML container. PostgreSQL is **not** part of the compose file. Point `.env` at the Postgres server you already run (the same database that [eloverblick](https://github.com/PsyCrow1976/eloverblick) and [elprisenligenu](https://github.com/PsyCrow1976/elprisenligenu) write to).

The compose file uses `build: .`, so Unraid needs the GitHub repo on disk (Dockerfile, `web/`). Pasting only `docker-compose.yml` into Compose Manager is not enough.

The container joins the existing Docker network named `home` and reaches the shared database as host `homepostgresql-db` (port `5432` inside Docker).

GitHub: https://github.com/PsyCrow1976/TheFamilyDashboard

## What you need

- Unraid 6.10 or later, Docker enabled
- [Community Applications](https://unraid.net/community/apps)
- Postgres already running on the `home` network (or reachable at `POSTGRES_HOST`)
- Price and usage rows already stored (`PRISKLASSE` = `DK1` or `DK2`)

## 1. Install Compose Manager

1. Open the **Apps** tab.
2. Search for **Compose Manager Plus** (or **Docker Compose Manager** on older CA listings).
3. Install the plugin.
4. Open the **Docker** tab. A **Compose** section should appear.

The original Docker Compose Manager plugin is deprecated; Compose Manager Plus is the drop-in replacement.

## 2. Put the project on the array

Do not store the stack on the Unraid USB stick. Use appdata.

In the Unraid terminal:

```bash
mkdir -p /mnt/user/appdata/thefamilydashboard
cd /mnt/user/appdata/thefamilydashboard
git clone https://github.com/PsyCrow1976/TheFamilyDashboard.git .
```

If `git` is not installed, download the repo ZIP from GitHub, extract it, and copy the files into `/mnt/user/appdata/thefamilydashboard` so that `Dockerfile` and `docker-compose.yml` sit in that folder.

You should see at least:

- `docker-compose.yml`
- `Dockerfile`
- `requirements.txt`
- `.env.example`
- `web/`

## 3. Create `.env`

```bash
cd /mnt/user/appdata/thefamilydashboard
cp .env.example .env
nano .env
```

Set:

```bash
PRISKLASSE=DK2
POSTGRES_HOST=homepostgresql-db
POSTGRES_PORT=5432
POSTGRES_USER=home
POSTGRES_PASSWORD=your-postgres-password
POSTGRES_DB=home
WEB_HOST=0.0.0.0
WEB_PORT=8089
TZ=Europe/Copenhagen
GOOGLE_CALENDAR_ICS_URL=
```

`GOOGLE_CALENDAR_ICS_URL` is optional. Paste the secret iCal address for the one calendar that should appear on the Calendar tab. Leave it empty to keep that tab blank. Do not commit the address.

`POSTGRES_HOST` must be an address **the container** can reach:

- On the shared `home` network, use the Postgres **container name** (`homepostgresql-db`).
- Do **not** use `127.0.0.1` or `localhost`. Inside the container that is the container itself.
- If you are not on that network, use the LAN IP of the machine that runs Postgres (for example `192.168.*.*`) and publish `5432` on the host.

Do not commit `.env`. It is gitignored.

If compose fails with `network home declared as external, but could not be found`, create it once (`docker network create home`) or attach this stack to the same network as Postgres.

## 4. Add the stack in Compose Manager

1. Docker tab → Compose → **Add New Stack**.
2. Name it `thefamilydashboard`.
3. Open **Advanced** / **Advanced Options**.
4. Set **Indirect Path** to `/mnt/user/appdata/thefamilydashboard` so the plugin uses the cloned repo as the compose project (build context included).
5. Save. Do not paste a second copy of the compose file into the USB plugin folder.

If the plugin has no Indirect Path field, skip the UI stack and start it from the terminal (step 5b).

Optional UI label: the compose file already sets `net.unraid.docker.webui` so Unraid can offer a WebUI link on port `8089`.

## 5. Start

### Compose Manager

On the Docker tab, for the `thefamilydashboard` stack:

1. **Compose Up** (first run builds the image; that can take a minute).
2. Confirm the `thefamilydashboard` container is running.
3. Open `http://<unraid-ip>:8089` (or the container WebUI link).

If Up does not rebuild after a later `git pull`, use the terminal command below.

### Terminal

```bash
cd /mnt/user/appdata/thefamilydashboard
docker compose up -d --build
docker compose ps
docker compose logs -f web
```

The app listens on port **8089**. If that port is already used on Unraid, pick another `808x` host port on the left-hand side in `docker-compose.yml`:

```yaml
ports:
  - "8090:8089"
```

Then the UI is `http://<unraid-ip>:8090`. `WEB_PORT` stays `8089` (port inside the container).

## 6. Check it

- `http://<unraid-ip>:8089` shows **The Family Dashboard** and the prices tab.
- `http://<unraid-ip>:8089/?tab=usage` shows the latest usage day.
- `http://<unraid-ip>:8089/health` returns `ok`.
- Tabs switch by themselves every five minutes.

## Update

```bash
cd /mnt/user/appdata/thefamilydashboard
git pull
docker compose up -d --build
```

`.env` is not in git, so pull will not overwrite the database password.

## Stop / remove

```bash
cd /mnt/user/appdata/thefamilydashboard
docker compose down
```

That stops the web container only. It does not delete Postgres or the price/usage tables.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Build fails, missing Dockerfile | Indirect path is not the cloned repo, or files were not copied next to `docker-compose.yml`. |
| Container starts then dies | `docker compose logs web`. Missing `PRISKLASSE` or Postgres settings in `.env`. |
| Cannot connect to Postgres | `POSTGRES_HOST` is `localhost`; container is not on network `home`; `pg_hba.conf` rejects the Docker IP. |
| Port already allocated | Change the host port mapping (`"8090:8089"`). |
| Empty prices / usage | The other two apps have not pulled that date yet. Usage is usually a day behind. Tomorrow’s prices usually arrive after 13:00. |
| Compose Up does nothing after git pull | Rebuild: `docker compose up -d --build`. |
