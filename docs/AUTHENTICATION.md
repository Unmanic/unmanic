# Authentication

Unmanic can require a username and password before anything on the web UI or API can be
reached. It is **disabled by default**; enabling it is entirely opt-in, and no existing
installation changes behaviour until you turn it on.

## What this protects against, and what it does not

This exists so that other devices and people on your local network cannot reach Unmanic.
Without it, anyone who can route to the port can browse your filesystem, delete files from
your library, and reconfigure your workers.

**It does not make Unmanic safe to expose to the internet.** Unmanic runs ffmpeg against
paths under its control and exposes a filesystem browser, so a single authentication bypass
is a host compromise, not a nuisance. If you need access from outside your network, use a
VPN or put Unmanic behind an authenticating reverse proxy. A password is not a substitute
for either.

Over plain HTTP, credentials are recoverable by anyone who can capture traffic on your
network. If that is part of your threat model, enable TLS with the `ssl_enabled`,
`ssl_certfilepath` and `ssl_keyfilepath` settings.

## Turning it on

### From the command line

```bash
unmanic --set-password
```

For Docker:

```bash
docker exec -it unmanic unmanic --set-password
```

Restart Unmanic afterwards.

### With environment variables

```yaml
environment:
  auth_enabled: "true"
  auth_username: "your-username"
  auth_password: "your-password"
```

The password is hashed at startup and is never written to `settings.json`. Note that
environment variables are visible to anyone able to run `docker inspect` on the container.

### From a browser

Set `auth_enabled` to `true` and restart. Unmanic will serve a one-time setup page at
`/unmanic/setup` for you to choose a username and password, and every other page redirects
to it until you do. Until you complete it, anyone who can reach the installation can claim
it, so do this straight away.

## If you lock yourself out

```bash
unmanic --disable-auth
```

For Docker, `docker exec -it unmanic unmanic --disable-auth`. Then restart.

## Signing out

Signing out revokes that browser's session immediately. Changing your password revokes
every session on every device.

## API and remote installations

Browsers use a session cookie. Scripts and linked Unmanic installations use HTTP Basic with
the same username and password:

```bash
curl -u your-username:your-password http://your-host:8888/unmanic/api/v2/version/read
```

Remote installation links already support this: set the link's auth mode to `Basic` and fill
in the username and password on the *Settings > Link* page of the installation doing the
connecting.

Basic authentication can be turned off with the `auth_allow_basic` setting if you only ever
use a browser. Doing so will break remote installation links.

## Settings reference

| Setting | Default | Purpose |
|---|---|---|
| `auth_enabled` | `false` | Master switch |
| `auth_allow_basic` | `true` | Accept HTTP Basic on API requests |
| `auth_session_idle_timeout_days` | `7` | Sign out after this long without activity |
| `auth_session_max_age_days` | `30` | Absolute session lifetime |
| `auth_trusted_origins` | `[]` | Extra origins accepted by the cross-origin check, for reverse proxies that rewrite `Host` |

## Behind a reverse proxy

If your proxy rewrites the `Host` header, the cross-origin protection will reject form
submissions. Add the address you use in the browser to `auth_trusted_origins`, including the
scheme:

```json
"auth_trusted_origins": ["https://unmanic.example.com"]
```

`X-Forwarded-Host` is deliberately not trusted, because anyone able to set that header could
use it to defeat the check.

## How it works

For anyone reviewing or extending this:

- **Passwords** are hashed with `hashlib.scrypt` (`n=32768, r=8, p=1`), stored as
  `scrypt$n$r$p$salt$hash` so the parameters travel with the hash and can be raised later
  without a migration. Credentials live in the database, not in `settings.json`, which is
  routinely pasted into bug reports.
- **Sessions** are 256-bit random tokens. Only their SHA-256 is stored, so a leaked database
  yields nothing replayable. They carry a sliding idle timeout under an absolute cap.
- **The session cookie** is `HttpOnly`, `SameSite=Lax`, and `Secure` only when TLS is
  enabled - setting `Secure` over plain HTTP would stop the cookie being sent at all.
- **Enforcement** happens in one place, `UnmanicWebApplication.find_handler`, so every route
  is covered by construction: the REST API, the frontend, static assets, the WebSocket
  handshake, the Swagger UI, and dynamically registered plugin handlers. An endpoint cannot
  be left unprotected by forgetting a decorator.
- **Cross-site protection** is `SameSite=Lax`, plus an `Origin` check on state-changing
  requests, plus rejection of `Sec-Fetch-Site: cross-site` on `/unmanic/api/`,
  `/unmanic/plugin_api/` and `/unmanic/panel/`. The third layer exists because `SameSite=Lax`
  still attaches the cookie to top-level GET navigation and browsers do not send `Origin` on
  those. An absent `Sec-Fetch-Site` header is allowed, because browsers do not send it on
  WebSocket handshakes.
- **`WWW-Authenticate` is never sent.** Browsers therefore never cache Basic credentials, so
  Basic never becomes an ambient credential and never becomes a cross-site request forgery
  vector. Machine clients such as `requests.HTTPBasicAuth` send credentials preemptively and
  never need the challenge.
- **Failed attempts** are throttled per client address with an escalating lockout, and logged
  at warning level with the source address so tools like fail2ban have something to act on.
