# Development log — ns8-snipeit

Entries are not deleted; corrections are added as new entries.

## 0.1.0 (unreleased) — 2026-10-23

Goal: first version of the module (work packages 1–7 of the implementation
plan).

Decisions:
- Official image `snipe/snipe-it` instead of an own build: Ubuntu's PHP
  8.3.6-0ubuntu0.24.04.13 already carries the PHP2Shell fix (package
  changelog), an own image would add maintenance without benefit.
- First super user through a PHP helper using the Snipe-IT models instead of
  `snipeit:create-admin`: that command takes the password on the command
  line and does not create the settings row, so the installer would stay
  open.
- Scheduler as systemd timer instead of the loop in supervisord: visible in
  the journal and stopped with the module.
- Directory login stored in the Snipe-IT database at every start (fail
  closed), because a user domain's bind password can change.

Deviations and findings during development (tested on a NS8 test node):
- `systemctl restart snipeit.service` returns before the containers pulled
  in by `Requires=` are up: `80start_services` names all three units.
- `passport:keys` fails when keys exist; Snipe-IT creates the personal access
  client only in its web installer (`passport:install`): new helper command
  `passport` creates both when missing.
- Snipe-IT trusts forwarded headers only with `APP_TRUSTED_HEADERS`; with
  `HEADER_X_FORWARDED_TRAEFIK` the real client IP is logged, a spoofed
  `X-Forwarded-For` is ignored.
- `snipeit:ldap-sync` without `--summary` exits 1 after a successful run
  (8.8.3).
- The dump is created with mode 0600; restore makes it readable for the mysql
  user of the throwaway container.
- Review (secure-coding): the group lookup did not verify the LDAP
  certificate (ldap3 default); now it follows `ldap_tls_verify`.

Tests (manual, test node): fresh install, installer closed (`/setup` → 302),
super user login, validation without super user, PHP package version,
scheduler runs, directory login with user domain and group (member in,
non-member and wrong password out, local super user still in), custom LDAP
server with and without certificate check, switch back and off (bind
password and Snipe-IT LDAP password removed), directory import, REST API
asset creation, real client IP (spoofed header ignored), backup → removal →
restore into a new instance (users, asset, directory login, old API token),
clone-module (move), update-module, secrets only in passwords.env (0600).
Automated: `tests/` on QEMU in the CI.

SBOM: `docs/sbom/` (Snipe-IT image 463 packages, MariaDB image 154).
