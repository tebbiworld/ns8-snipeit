# Administrator manual — ns8-snipeit

Installation, configuration parameters, directory login, backup, images and
updates: see [README](../README.md). This page adds operation and
troubleshooting.

## Roles

- NS8 cluster administrator: installs, configures, updates, backs up the
  module; has database access (`runagent -m snipeitN`).
- Snipe-IT super user: created by the first configuration; manages users,
  permission groups and settings in Snipe-IT.
- Directory users: no permissions until granted.

## Status and logs

```bash
runagent -m snipeit1 systemctl --user status snipeit.service snipeit-app.service snipeit-mariadb.service
runagent -m snipeit1 journalctl --user -u snipeit-app.service -f        # app, Apache, Laravel (stderr)
runagent -m snipeit1 journalctl --user -u snipeit-scheduler.service     # scheduled tasks
runagent -m snipeit1 journalctl --user -u snipeit-ldap-sync.service     # directory import (table)
```

## Troubleshooting

| Symptom | Cause / action |
| --- | --- |
| configure-module: `admin_user_required` | first configuration without super user: send `admin_user`, `admin_password`, `admin_email` |
| Directory users cannot log in, journal: "LDAP login disabled, cannot prepare it" | group not found, directory not reachable or certificate not valid; fix the settings and save, or check the user domain |
| Login works locally but users are rejected after a restore | the user domain does not exist on this cluster: choose an existing one |
| Mails are not sent | no smarthost in the cluster settings: Snipe-IT logs them (`MAIL_MAILER=log`) |
| API: "Personal access client not found" | fixed by `bin/snipeit-sync` at every start; restart `snipeit-app.service` |
| configure-module: `timezone_unknown` | the zone does not exist under `/usr/share/zoneinfo` of the node: choose one of the list |
| Time zone change fails: "MariaDB does not know the time zone" | the time zone tables of MariaDB lack the zone; nothing was changed. Choose an equivalent zone or report it |
| Backup fails: "the database has no users or no settings any more" | the database was emptied: restore the last good backup, or create a new super user if the data is meant to be gone |
| Directory users are missing after the import, journal of `snipeit-ldap-sync.service`: first name required | `first_name_attribute` is `givenname` and these users have none: switch to `login` or fill `givenName` |
| Locked out of the super user | `runagent -m snipeit1 podman exec -it -u docker snipeit-app php artisan snipeit:create-admin ...` (interactive), or reset the password in Snipe-IT with another super user |

## Decommissioning

Export the data you need (reports, CSV), keep the last NS8 backup for the
retention period, then `remove-module --no-preserve snipeitN`.
