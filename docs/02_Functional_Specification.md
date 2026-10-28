# Functional specification and implementation plan — ns8-snipeit

Version 0.2, 2026-10-28 (U-13, U-14, backup check). References: Snipe-IT 8.8.3 source in the image
`snipe/snipe-it:v8.8.3` (paths below are inside `/var/www/html`), NS8
developer manual and the conventions of the tebbiworld NS8 modules.

## Solution overview

Rootless Podman pod `snipeit` (slirp4netns, host loopback reachable as
10.0.2.2) with two containers: `snipeit-mariadb` (MariaDB 11.4) and
`snipeit-app` (official Snipe-IT image: Apache, Ubuntu PHP 8.3, Laravel 12).
Only the web port is published, on 127.0.0.1, for the Traefik route. The NS8
agent actions (Python/Bash in `imageroot/`) configure the instance; a PHP
helper (`imageroot/container/ns8-snipeit.php`, mounted read-only) writes the
Snipe-IT database through the application's own models.

| Component | Version | Licence | GAMP category |
| --- | --- | --- | --- |
| Snipe-IT image | v8.8.3 (tag + digest) | AGPL-3.0 | 4 (configured product) |
| MariaDB image | 11.4.13 (tag + digest) | GPL-2.0 | 1 |
| NS8 core, Traefik | cluster | GPL-3.0 | 1 |
| Module code (this repository) | — | GPL-3.0 | 5 (custom code) |

## Implementation per requirement

| URS | Implementation | Kind |
| --- | --- | --- |
| U-01 | Official image unchanged; entrypoint `/startup.sh` migrates the database at every start. | configuration |
| U-02 | NS8 module layout: `create-module`, `configure-module`, `get-configuration`, `restore-module`, `clone-module`, `update-module.d`, Vue UI (en, de). | custom |
| U-03 | `05validate` refuses the first configuration without a super user. `85setup` creates the user and the settings row like `SetupController::postSaveFirstAdmin`; then `Setting::setupCompleted()` is true and `/setup` redirects (`CheckForSetup` middleware). The Traefik route is set afterwards (`90route`). | custom |
| U-04 | Image pinned by digest; Ubuntu package `php8.3-common`/`libapache2-mod-php8.3` 8.3.6-0ubuntu0.24.04.13 carries the fix (package changelog). The weekly auto-release refuses an upstream image with an older package. | configuration + CI |
| U-05 | `pypkg/ldapsettings.py` (shared with other tebbiworld modules) stores the source; `pypkg/snipeitconfig.py` derives the Snipe-IT LDAP columns; `ns8-snipeit.php ldap` saves them like `SettingsController::postLdapSettings` (bind password `Crypt::encrypt`). Group: `memberOf` with LDAP_MATCHING_RULE_IN_CHAIN in `ldap_filter`. Fail closed: if the directory cannot be prepared the directory login is switched off. | custom |
| U-06 | `ldap_pw_sync = 0`; secrets in `state/passwords.env` (0600), passed to containers by name (`--env NAME`), on stdin to the PHP helper. | custom |
| U-07 | `module-dump-state` (mariadb-dump, user `snipeit`; refuses an installed instance without users or settings, the test of `Setting::setupCompleted()`), `state-include.conf` (dump, passwords.env, `snipeit-data`), `state-exclude.conf` (Snipe-IT's own backups), `restore-module/40restore_database` (initdb), `06copyenv`/`50traefik` linked into `clone-module`. | custom |
| U-08 | `bin/discover-smarthost` → `state/smarthost.env`; `snipeitconfig.mail_env()` maps it to Laravel `MAIL_*`; without smarthost `MAIL_MAILER=log`. | custom |
| U-09 | `APP_TRUSTED_PROXIES=10.0.2.100` (address from which the pod receives the published port), `APP_TRUSTED_HEADERS=HEADER_X_FORWARDED_TRAEFIK` (`config/trustedproxy.php`). | configuration |
| U-10 | `/supervisord.conf` without the `run_schedule` loop; `snipeit-scheduler.timer` runs `artisan schedule:run` every minute. | custom |
| U-11 | `snipeit-ldap-sync.timer` daily, `snipeit:ldap-sync --summary` (without `--summary` 8.8.3 exits 1 although it succeeds). | custom |
| U-13 | `timezone` → `APP_TIMEZONE` (`config/app.php`). Names from `etc/timezones`, the zones PHP in the image accepts (`tools/gen-timezones.sh`, `pypkg/timezones.py`). Laravel writes date-time values as wall clock of that zone (`config/database.php` sets no connection time zone), and several datetime columns hold calendar days as midnight (expected check-in, maintenances, audit dates; migrations of 8.8.3): no conversion. On an installed instance `05validate` requires `timezone_change_confirmed`; the UI warns and asks for it. | custom |
| U-14 | `first_name_attribute` → `ldap_fname_field`: login attribute or `givenname`. Snipe-IT maps one attribute per field without fallback (`Ldap::attributeMap`, `applyLdapAttributesToUser`) and requires `first_name` (`User::$rules`): with `givenname` a user without it cannot be created at the first login, an existing one gets an empty first name at the next login (`saveQuietly`), the import skips it. A fallback per user is not possible without patching Snipe-IT. | configuration |

Out of scope: SAML/OAuth login, Microsoft Graph mail, S3 storage, Redis.

## Implementation plan

1. Module skeleton, images, units, secrets (U-01, U-02, U-06) — done.
2. Installation without web installer (U-03), REST API keys — done.
3. Directory login and import (U-05, U-11) — done.
4. Proxy, mail, scheduler (U-08 – U-10) — done.
5. Backup, restore, clone, update (U-07) — done.
6. Tests (Robot Framework, QEMU CI), auto-release with PHP check (U-04) — done.
7. Documentation, SBOM — done. Release after review by the maintainer.
8. 1.1.0: time zone setting (U-13), first name attribute (U-14), backup of an
   emptied database refused (U-07), update test from the newest release.
