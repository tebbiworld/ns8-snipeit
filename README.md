# ns8-snipeit

[Snipe-IT](https://snipeitapp.com/) for [NethServer 8](https://github.com/NethServer/ns8-core):
IT asset management — hardware, software licenses, accessories, consumables
and components, who has what (check-out/check-in with acceptance), audits,
maintenances and reports, with a REST API.

The module runs the official image `snipe/snipe-it` (Apache, PHP, Laravel)
with a MariaDB database in a rootless Podman pod behind the Traefik proxy of
the node.

## Features

- Installation without the public web installer: the first configuration
  creates the super user, the installer is closed before the Traefik route
  exists
- Login with a user domain of the cluster or an LDAP server of its own,
  optionally limited to the members of a group (nested groups count);
  directory passwords are never stored in Snipe-IT
- Daily import of the directory users (members of the login group)
- Mails through the cluster smarthost
- Real client addresses in the Snipe-IT logs and login throttling
  (Traefik is the only trusted proxy)
- Scheduled tasks (alerts, reminders, clean-up) from a systemd timer
- Backup and restore with an SQL dump, clone-module
- Secrets (application key, database and bind passwords) in
  `state/passwords.env` (mode 0600), never in the module environment

## Install

```bash
add-module ghcr.io/tebbiworld/snipeit:latest 1
```

## Configure

The first configuration must create the super user:

```bash
api-cli run module/snipeit1/configure-module --data '{
  "host": "assets.example.org", "lets_encrypt": true, "http2https": true,
  "admin_user": "admin", "admin_password": "a long secret password",
  "admin_email": "admin@example.org", "site_name": "Example IT"
}'
```

| Parameter | Description |
| --- | --- |
| `host` | Host name of Snipe-IT |
| `lets_encrypt` | Request a Let's Encrypt certificate |
| `http2https` | Redirect HTTP to HTTPS |
| `admin_user`, `admin_password`, `admin_email` | First configuration only: the first super user. The password needs at least 12 characters and is not stored by the module. |
| `site_name` | First configuration only, optional: name shown by Snipe-IT |
| `mail_from` | Optional sender address of mails; default `snipeit@<host>` |
| `timezone` | Optional IANA time zone, e.g. `Europe/Zurich` (default: the node time zone at installation). Must exist under `/usr/share/zoneinfo` of the node. See "Time zone" below |
| `first_name_attribute` | `login` (default) or `givenname`: directory attribute for the first name, see below |
| `ldap_enabled` | Login with a user domain or LDAP server |
| `ldap_*` | Directory settings, see below |

Without a super user the configuration is refused (`admin_user_required`):
the Snipe-IT web installer would otherwise be open to whoever reaches the
host name first.

Further settings (locale, currency, labels, custom fields, permission
groups, two-factor authentication, password rules) are made in the Snipe-IT
web interface (Admin → Settings) and kept in its database.

### Login with a user domain or LDAP server

| Parameter | Description |
| --- | --- |
| `ldap_source` | `domain`: a user domain of the cluster (recommended); `custom`: an LDAP server of its own |
| `ldap_domain` | `domain`: name of the user domain |
| `ldap_group` | Optional: only members of this group may log in and are imported (nested groups count). Active Directory only |
| `ldap_url` | `custom`: `ldaps://host:636` or `ldap://host:389` |
| `ldap_start_tls` | `custom`: StartTLS for `ldap://` |
| `ldap_tls_verify` | `custom`: verify the server certificate (default true) |
| `ldap_schema` | `custom`: `ad` or `rfc2307` |
| `ldap_base_dn`, `ldap_bind_dn`, `ldap_bind_password` | `custom`: search base and service account |
| `ldap_user_attribute` | `custom`, optional: login attribute (default `sAMAccountName` or `uid`) |

```bash
api-cli run module/snipeit1/configure-module --data '{
  "host": "assets.example.org", "lets_encrypt": true, "http2https": true,
  "ldap_enabled": true, "ldap_source": "domain",
  "ldap_domain": "ad.example.org", "ldap_group": "snipeit-users"
}'
```

Directory attributes: login name `sAMAccountName` (AD) or `uid`, mail
`mail`, display name `displayName`, last name `sn`. Snipe-IT maps a single
attribute per field, without fallback, and needs a first name: its daily
import skips a user without one. `first_name_attribute` chooses it:

- `login` (default): the login name, present for every user. NS8 creates
  users without `givenName`.
- `givenname`: `givenName`, for directories where every user has one; users
  without it are skipped by the import (listed in the journal of
  `snipeit-ldap-sync.service`).

The change applies at the next login or import of a user. Users show up with
their display name, or with first and last name when it is empty.

### Time zone

Snipe-IT shows and takes times in the zone of `timezone`; it has no setting
of its own for it. Laravel stores date-time values as wall clock of that
zone, so a change on an installed instance converts them: `configure-module`
(step `08timezone`) stops the app, converts every `datetime`/`timestamp`
column of the database from the old to the new zone with MariaDB
`CONVERT_TZ` in one transaction, and starts it again. Date columns (purchase
date, expected check-in) are calendar days and stay. Times inside texts, e.g.
the old and new values in the activity log, are not converted. If the
conversion fails, nothing is changed. Back up before changing it.

A directory user is created in Snipe-IT on the first login (or by the daily
import, `snipeit-ldap-sync.timer`) **without permissions**: a super user
grants them in Snipe-IT, per user or with a permission group. Local accounts,
like the super user, keep working. The module writes the directory settings
into the Snipe-IT database at every start of the app (the bind password
encrypted with the application key), so a new bind password of a user domain
is applied by the event `user-domain-changed`. Changes made on the LDAP page
of the Snipe-IT settings are overwritten at the next start: change them in
the NS8 module settings. If the directory cannot be prepared (e.g. the login
group does not exist, the certificate is not valid) the directory login is
switched off and the reason is logged; local accounts still work.

## Data and backup

- Database: MariaDB 11.4 in the volume `mysql-data`. The backup contains an
  SQL dump (`state/snipeit.sql`, written by `bin/module-dump-state`), not the
  raw volume; restore loads the dump into a new volume.
- Files: uploads, OAuth keys of the REST API in the volume `snipeit-data`
  (backed up). The weekly Snipe-IT backups in `snipeit-data/dumps` are not
  part of the NS8 backup (`etc/state-exclude.conf`).
- Secrets: `state/passwords.env`, backed up. The application key encrypts
  sessions, the stored LDAP bind password and encrypted custom fields: a
  restore must bring back the same file.

## Images and updates

- `docker.io/snipe/snipe-it`, pinned by tag and digest
- `docker.io/library/mariadb` (11.4 LTS), pinned by tag and digest

The Snipe-IT image is based on Ubuntu 24.04 and uses its PHP 8.3. Ubuntu
backports security fixes without changing the upstream version: PHP reports
8.3.6 also after the fix of CVE-2026-109618/109619 ("PHP2Shell"). The fix is
in the **package** version `8.3.6-0ubuntu0.24.04.13` (see
`/usr/share/doc/php8.3-common/changelog.Debian.gz` in the container). Check:

```bash
runagent -m snipeit1 podman exec snipeit-app dpkg-query -W php8.3-common libapache2-mod-php8.3
```

`.github/workflows/auto-release.yml` checks every week for new releases of
Snipe-IT, of MariaDB on the 11.4 LTS line and of the Node.js 24 image that
builds the UI. It refuses a Snipe-IT image whose PHP package is older than
the fixed one, pins tag and digest, and releases a new module version after
at least 42 days. `renovate.json` describes the same pins for Renovate, if it
is enabled for the repository. On
`update-module` the app container starts on the new image and its entrypoint
migrates the database.

## Services

| Unit | Purpose |
| --- | --- |
| `snipeit.service` | pod (slirp4netns with host loopback, web port on 127.0.0.1) |
| `snipeit-mariadb.service` | database |
| `snipeit-app.service` | web server; `bin/snipeit-config` (environment) before, `bin/snipeit-sync` (API keys, directory login) after the start |
| `snipeit-scheduler.timer` | `artisan schedule:run`, every minute (replaces the loop of the image) |
| `snipeit-ldap-sync.timer` | daily directory user import, only with the directory login on |

## Security notes and known limits

- The application key and the database password reach the app container as
  environment variables (visible to the module user with `podman inspect`),
  as in other NS8 modules: a deviation from keeping secrets out of the
  environment, limited to the module user.
- Between the start of the services and the creation of the super user in
  the first configuration (seconds), the Snipe-IT installer answers on the
  node loopback port of the instance; it is not routed through Traefik.
  Local processes connecting to that port are treated as the trusted proxy
  and may set `X-Forwarded-For`.
- The route is published only while Snipe-IT reports a completed setup; a
  backup fails when the database of a configured instance cannot be dumped
  or has no users or settings any more (an emptied database would otherwise
  push good snapshots out of the retention), and a restore without a dump of
  an installed instance is refused.
- `clone-module` keeps the host name: a copy (not a move) needs a new host
  name before both are used.
- An LDAP server of its own is checked against the system CA certificates of
  the container; a private CA cannot be added yet (switch the check off only
  in a trusted network).
- The task input of `configure-module` (super user and bind password) is kept
  in the NS8 task history like for every module.

## Uninstall

```bash
remove-module --no-preserve snipeit1
```

## Testing

The tests (Robot Framework, `tests/`) run on throwaway NS8 nodes (QEMU,
Rocky Linux 9 and Debian 13) in the CI after every branch build
(`.github/workflows/test-module-qemu.yml`).

## Documentation

`docs/`: requirements, functional specification, risk assessment for a use
under GMP, administrator and user manual, development log and software bill
of materials (`docs/sbom/`, CycloneDX).

## License

The module is licensed under GPL-3.0-or-later. Snipe-IT is licensed under
AGPL-3.0 by Grokability, Inc.; its name and logo are used to identify the
software only.
