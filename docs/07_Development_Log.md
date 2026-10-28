# Development log — ns8-snipeit

Entries are not deleted; corrections are added as new entries.

## 1.1.0 (unreleased) — 2026-10-28, review fixes

Independent review on PR #4 (comment 6463049226, changes required):
- R2/R3 (the conversion moved calendar days kept as midnight to the
  neighbouring day; `CONVERT_TZ` leaves values outside 1970–2038 unchanged)
  correct the earlier decision. Decision (maintainer, 2026-10-28): no
  conversion. The zone is free before the installation; afterwards a
  change needs `timezone_change_confirmed` and shifts the stored times
  (warning in the UI, documented). `08timezone` removed. Rejected:
  conversion of a reviewed list of moment columns (Snipe-IT does not mark
  which columns are moments; more risk and tests than the rare change is
  worth).
- R1: the zone list is `etc/timezones`, made from the Snipe-IT image by
  `tools/gen-timezones.sh` (496 zones PHP accepts), not the node list with
  legacy names. The default from the node falls back to UTC if Snipe-IT does
  not know the node zone. The current zone of an instance stays accepted.
- R4: documentation and UI text of `givenname` corrected (no first login
  and empty first name at the next login for users without `givenName`).
- Hints: H1–H3, H6–H8 obsolete without conversion; H4 `NsComboBox`, the
  saved zone stays selectable; H5 the backup test checks the error message;
  H9 open (manual UI check).

## 1.1.0 (unreleased) — 2026-10-28

Goal: issue #3 (time zone) and the two open hints of 1.0.0 (work package 8).

- Issue #3 (Mohannad33): the time zone came from the node at installation
  and could not be changed. New optional `timezone`, validated against
  `/usr/share/zoneinfo`.
- Decision (maintainer, 2026-10-28): convert the stored times on a change
  instead of only warning. Reason: Laravel stores wall clock of
  `APP_TIMEZONE` without a connection time zone (`config/database.php`
  8.8.3), so old entries, the activity log among them, would show a wrong
  moment. Rejected: warning only (falsifies the audit trail display),
  change only before installation (does not solve the issue).
- Decision (maintainer, 2026-10-28): first name attribute selectable
  (`login` default, `givenname`). Snipe-IT maps one attribute per field
  without fallback and refuses users without first name in the import
  (`Ldap::applyLdapAttributesToUser`, `User::$rules`, `LdapSync` 8.8.3); a
  per-user fallback would need a patch of Snipe-IT. Rejected: always
  `givenName` (NS8 users have none), documentation only.
- Backup: `module-dump-state` refuses an installed instance whose database
  has no users or settings (same test as `Setting::setupCompleted()`).
- CI: `update_from: update-baseline` removed; the update test starts from
  the newest release (1.0.0).

Tests: QEMU CI run 40644348967 (8fee06a) green: install and update from
1.0.0 on Rocky 9 and Debian 13, including the new cases (unknown and
SQL-like time zone refused, conversion to Pacific/Kiritimati and back,
first name default and givenName, backup of the emptied database refused).
The MariaDB image has its time zone tables loaded (probe passed).
ghcr version update-baseline deleted after the green run (maintainer OK).
Manual UI check of the Settings page: ❰pending❱.

## 0.1.0 (unreleased) — 2026-10-23, review fixes

Independent review on PR #1 (changes required), fixed one commit per finding:
B1 backup/restore without database and route before setup, B2 control
characters in text fields (environment injection), B3 AD domain of the
fallback bind, B4 group lookup over StartTLS, B5 bind password kept after
switching the directory login off, B6 negative tests, B7 Renovate. Hints:
LDAP status in get-configuration and the UI, no SQL bindings in the journal,
only the MariaDB passwords for the restore container; the other hints are
documented as limits in the README.

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
