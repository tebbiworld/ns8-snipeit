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

`.github/workflows/auto-release.yml` checks every week for a new Snipe-IT
release, refuses one whose PHP package is older than the fixed one, pins tag
and digest, and releases a new module version after at least 42 days. On
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

## Uninstall

```bash
remove-module --no-preserve snipeit1
```

## Testing

```bash
./test-module.sh <NODE_ADDR> ghcr.io/tebbiworld/snipeit:latest
```

The tests (Robot Framework, `tests/`) also run on QEMU nodes in the CI.

## Documentation

`docs/`: requirements, functional specification, risk assessment for a use
under GMP, administrator and user manual, development log and software bill
of materials (`docs/sbom/`, CycloneDX).

## License

The module is licensed under GPL-3.0-or-later. Snipe-IT is licensed under
AGPL-3.0 by Grokability, Inc.; its name and logo are used to identify the
software only.
