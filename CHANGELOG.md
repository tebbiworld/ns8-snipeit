# Changelog

## 1.1.0 – unreleased

- Time zone setting (issue #3): choose the zone of Snipe-IT in the module
  settings, from the zones Snipe-IT's PHP accepts. Stored times are not
  converted: on an installed instance a change needs a confirmation.
- First name of directory users from the login name (default) or from
  `givenName` (only for directories where every user has one).
- A backup of an installed instance with an emptied database fails instead
  of replacing good snapshots.
- CI: the update test starts from the newest release.

## 1.0.0 – 2026-10-23

- First version: Snipe-IT 8.8.3 (PHP package 8.3.6-0ubuntu0.24.04.13 with
  the PHP2Shell fix) and MariaDB 11.4.13, pinned by digest.
- Installation without the web installer, login with a user domain or an
  LDAP server (optional group), daily directory import, smarthost mail, real
  client IP, scheduler timer, backup/restore with SQL dump, clone-module.
