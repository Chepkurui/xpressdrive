# XpressDrive — Regional road freight & backhaul matching

XpressDrive matches cargo owners with trucks already heading their way, especially trucks and empty containers **returning to base**, across Uganda, Kenya, Rwanda, Tanzania, South Sudan and DR Congo. Customers book anything from a parcel to a full 20ft/40ft container. Operations allocates trips to drivers and follows them on a live map. Drivers use the mobile app to accept trips, post milestones and share their position.

| Part | Stack | Folder |
|---|---|---|
| API + staff admin | Django 6, DRF, PostgreSQL, SimpleJWT | `backend/`: models in `apps/data`, driver/fleet API in `apps/fleet`, routes in `apps/apis/urls.py` |
| Website, customer portal, staff operations | Vue 3, Vite, Pinia, Leaflet (OpenStreetMap tiles) | `web/` |
| Customer + driver mobile app | Flutter (Android / iOS), geolocator | `mobile/` |

## Concepts

- **Booking** (model `Shipment`, API `/api/shipments/`): one customer's cargo on one lane (`origin → destination`, from `/api/places/`). Load types: parcel, part load, full truck, 20ft and 40ft container.
  Milestones: `booked → confirmed → allocated → loaded → in_transit ⇄ at_border → arrived → delivered` (+ `on_hold`, `cancelled`).
- **Trip** (model `Trip`, formerly `Batch`): one truck journey carrying one or many bookings, optionally flagged as a **return/backhaul leg**.
  Stages: `planned → allocated (awaiting driver) → accepted → loading → in_transit ⇄ at_border → arrived → completed`. Moving a trip moves every open booking on it.
- **Empty leg**: a driver says "my truck or container goes back empty from X to Y on date D". Operations turns it into a backhaul trip in one click. Open legs and planned backhaul trips are shown on the public **return-truck board** (lane, date and space only; no driver or plate).
- **Drivers** are user accounts with `is_driver` (set in Staff Operations → People). Their tokens carry a `driver` scope, on mobile too. They only ever see trips allocated to them.
- **Privacy**: GPS positions (`TripPosition`) and the ops log (`TripEvent`) are for staff and the trip's driver only. Cargo owners and the public tracker only see milestones with a **place name** (town, weighbridge, border post), never coordinates, driver or truck.

## Features

**Customers (web + mobile):** book a truck (route, pickup address/date, load type, weight, value, receiver), edit or cancel until confirmed, track milestones, see charges. Public tracking by number, a rate card with per-lane plans, an estimator (road volumetric divisor 3000) and the return-truck board.

**Drivers (mobile):** sign in with a driver account to get the driver app. It shows new allocations (polled every 60 s; badge and snackbar), accept/decline with a reason, stage buttons (start loading → depart → border → arrived → complete), "report a checkpoint" (pick a place or type one), mark each booking delivered, and offer return space. While a trip is live the phone shares its position: batched every 30 s, buffered without signal, plus a heartbeat fix when parked. On Android a foreground-service notification is shown; on iOS the location background mode is used. Sharing stops automatically when the trip ends.

**Staff Operations (web `/staff`):** an overview with the pipeline and "needs attention" (trucks not reporting for 30 min, declined trips, bookings with no truck, open empty legs), a **live map** of all trucks (15 s refresh, GPS trail of the selected trip), trips (create, allocate to a driver and truck, move, post a checkpoint, fill level, ops log), bookings (assign to a trip, with same-lane trips flagged ★), empty legs, drivers & trucks, people (toggle driver), pricing plans per lane, and messages. Sections follow Django permissions and token scopes: `shipments`, `trips`, `trucks`, `emptylegs`, `users`, `rates`, `messages`.

## Running locally

### Backend
```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # edit POSTGRES_* to match your database
.venv/bin/python manage.py migrate      # also seeds the indicative rate card
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver 4444    # http://127.0.0.1:4444, admin at /admin/
.venv/bin/python manage.py test         # 91 tests
.venv/bin/python manage.py seed_demo    # demo drivers, trucks, live trips with GPS trails (password Admin@123)
```
Or with Docker: `docker compose up --build` (Postgres + Redis + API).

### Web
```bash
cd web && npm install && npm run dev    # http://localhost:5175 (proxies /api → :4444)
npm run build                            # production bundle in web/dist
```

### Mobile
```bash
cd mobile && flutter pub get
flutter run                                                    # Android emulator → http://10.0.2.2:4444
flutter run --dart-define=API_BASE_URL=http://localhost:4444   # iOS simulator
flutter build apk --dart-define=API_BASE_URL=https://xpressdrive.co.ug   # release (https required)
```

## API overview (additions)

| Method | Path | Who | Purpose |
|---|---|---|---|
| GET | `/api/places/`, `/api/capacity/` | public | Towns/ports/borders; return-truck board |
| GET | `/api/driver/summary/`, `/api/driver/trips/` | driver | Pending allocations, active trip, own trips |
| POST | `/api/driver/trips/{code}/respond/` · `status/` · `checkpoint/` · `positions/` | driver | Accept/decline, move, milestone, GPS batch |
| POST | `/api/driver/trips/{code}/bookings/{tn}/delivered/` | driver | Hand-over |
| GET/POST/PATCH/DELETE | `/api/driver/empty-legs/` | driver | Offer / withdraw return space |
| GET | `/api/staff/live/`, `/api/staff/trips/{code}/positions/` | staff:trips | Live map, GPS trail |
| GET/POST/PATCH | `/api/staff/trips/…` (`allocate/`, `move/`, `checkpoint/`) | staff:trips | Trip management |
| GET/POST/PATCH | `/api/staff/trucks/`, `/api/staff/empty-legs/` (`{id}/create-trip/`), `/api/staff/drivers/` | staff | Fleet |

Tracking numbers start with `XD` (older `WD…` numbers still track).

## Security (OWASP Top 10 / ASVS / MASVS)

- **Broken access control (A01):** every customer query is scoped to `owner=request.user`, so other users' shipments return 404 (no IDOR). UUID primary keys; 50-bit random tracking numbers. Server-controlled fields (status, charges, owner, measurements) are not writable (no mass assignment). Default DRF permission requires a signed-in user whose token has the `account` scope; staff endpoints additionally need the matching `staff:<section>:<action>` scope **and** live Django permission (least-privilege tokens; see *Roles & scoped tokens*). Covered by tests.
- **Cryptographic failures (A02):** Argon2 password hashing; HSTS, SSL redirect and secure cookies when `DEBUG=false`; release mobile builds refuse non-HTTPS API URLs; Android cleartext traffic and backups disabled.
- **Injection (A03):** ORM only, no raw SQL; strict serializer validation with bounds and lengths; tracking numbers checked against a regex; Vue templates escape output (no `v-html`).
- **Insecure design / auth failures (A04/A07):** short-lived (10 min) access tokens; rotating refresh tokens with blacklist and reuse detection; refresh token kept in an **httpOnly SameSite=Strict cookie** on web (access token in memory only) and in **Keychain/Keystore** on mobile; cookie refresh needs a custom header (CSRF defence in depth); password change/reset revokes all sessions; generic login errors and non-enumerating password reset; Django password validators (min 10, common, numeric, similarity).
- **Security misconfiguration (A05):** `DEBUG` off by default; missing `SECRET_KEY` is a hard error; non-default admin URL; JSON-only API renderer in production; strict CSP / `X-Frame-Options: DENY` / `nosniff` / Referrer-Policy / Permissions-Policy / CORP on every response; CORS allow-list only (empty by default); `manage.py check --deploy` is clean apart from opt-in HSTS preload.
- **Rate limiting / DoS:** DRF throttles per scope (login 5/min, register, password reset, refresh, tracking, estimate, contact) plus optional nginx `limit_req`; request body size limits; pagination capped at 100. Use `REDIS_URL` in production so throttles are shared across workers. `NUM_PROXIES` stops spoofed `X-Forwarded-For` headers from bypassing throttles.
- **Logging & monitoring (A09):** `security` logger records registrations, logins (success/failure), password events and 401/403/429 responses, with IPs and no secrets. Unhandled errors return a generic 500 with no stack trace.
- **Vulnerable components (A06):** dependencies are pinned to supported major versions; run `pip-audit`, `npm audit` and `flutter pub outdated` regularly.

## Before going live

- Set real `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_ADMIN_URL`, DB credentials, SMTP email, `REDIS_URL`
- Review the indicative road rate card (Staff Operations → Pricing)
- Use a commercial (or self-hosted) map tile provider for the live map in production; the public OpenStreetMap tiles are for light use. Update `FleetMap.vue` and the nginx CSP `img-src`.
- Add push notifications (FCM/APNs) if drivers need allocation alerts while the app is closed
- Replace the placeholder office details/contact email in `web/src/components/AppFooter.vue` and `AboutView.vue`
- Deploy with `deploy/nginx.conf` (same-site SPA + API), `DJANGO_BEHIND_PROXY=true`, `DJANGO_NUM_PROXIES=1`
- Enable 2FA / strong passwords for staff admin accounts
