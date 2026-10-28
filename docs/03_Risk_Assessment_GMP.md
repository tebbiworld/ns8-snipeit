# Risk assessment and GMP fitness — ns8-snipeit

Version 0.2, 2026-10-28 (time zone, backup check). Draft for review and approval by the quality unit of
a user; **not** a statement that the system is validated or compliant.
Binding frame: EU/PIC/S GMP Annex 11 (2011). Placeholders: ❰…❱.

## 1. Classification

- GMP relevance: decided by the user. Snipe-IT becomes GMP-relevant when it
  holds GMP records, e.g. the equipment list with calibration or maintenance
  status that a release or a deviation relies on. Used as a plain IT
  inventory it is not GMP-relevant (reduced method: URS, gap analysis,
  installation record, access rules, change log).
- Use cases: B (procurement of open source) and C (installation); D
  (operation) at the user.
- GAMP categories: Snipe-IT 4 (configured product), MariaDB/NS8 1, module
  code 5 (custom: installation, directory login, backup).

## 2. Gap analysis (configuration of this module, Snipe-IT 8.8.3)

Evidence: T = own test on a NS8 test node 2026-10-23, S = source code of
8.8.3 in the image, R = README of this module. "not evidenced" = not checked.

| Requirement (Annex 11) | As is | Evidence | Measure |
| --- | --- | --- | --- |
| Audit trail of GMP-relevant changes (9) | Activity log (`action_logs`) records who, what, when, old and new value per field, source (gui/api) and client IP for create/update/check-out/check-in/audit. No mandatory reason for change (notes are optional). | T (asset rename: old/new name and note logged with user, time, IP) | SOP: reason in the note field; review of the activity report at a defined interval |
| Audit trail cannot be changed or switched off by users (9) | No UI function to edit or disable it. "Purge deleted records" removes the logs of purged items; disabled unless `ALLOW_DATA_PURGE=true`, which the module does not set. Database administrators (cluster admins) can change data directly. | S (`config/app.php` allow_purge, `Purge.php`) | restrict cluster administration; periodic review |
| Personal accounts, roles (12) | Personal local or directory accounts; permission groups; directory users start without permissions. | T, S | SOP for granting rights; no shared accounts |
| Password rules, lockout | Minimum length 12 for the first super user, Snipe-IT password rules configurable; login throttling (`LOGIN_MAX_ATTEMPTS` 5 / 60 s) per client IP — real IP behind Traefik. Directory accounts: rules of the directory. | T (real client IP recorded), S (`config/auth.php`) | configure password rules / 2FA in Snipe-IT |
| Inactivity logout (12) | Session ends after 120 idle minutes (module default; image default 200 h). | R | adjust if the SOP requires less |
| Two-factor authentication | Available in Snipe-IT (TOTP), optional. | not evidenced | decide per risk |
| Data integrity / ALCOA+ (4, 5) | Attributable (user per change), contemporaneous (server time UTC/node zone), original in the database, enduring through backup. Electronic signatures: acceptance signatures on check-out exist but are not Part 11 / Annex 11 §14 e-signatures. | T (attribution); signatures not evidenced | do not use as e-signature for GMP decisions |
| Accuracy checks (6) | Field validation by Snipe-IT; no plausibility checks for calibration values; custom fields can carry formats. | not evidenced | define custom fields with formats; manual review |
| Calibration/maintenance management | Maintenances per asset (type, start/end, cost, notes), audit due dates, expected check-in; no calibration plans with tolerances, measurement results, out-of-tolerance handling or locking of overdue equipment. | not evidenced (manual) | keep calibration certificates and OOT handling in the QMS; Snipe-IT as register |
| Backup and restore (7.2) | Daily NS8 backup with database dump and files; restore tested into a new instance (users, assets, directory login, API token). Since 1.1.0 a backup of an installed instance whose database has no users or settings fails, so an emptied database does not push good snapshots out of the retention. | T | test restore periodically; monitor failed backups |
| Change and configuration management (10) | Module and Snipe-IT versions pinned; weekly upstream check, release after 42 days; updates applied through the NS8 cluster update. | R | change control before updating a GMP instance (release notes, regression test) |
| Time (9) | Container time = node time (NTP of the node). Users cannot change it. Display zone set by the cluster administrator (`timezone`), stored times are wall clock of that zone and are not converted: after a change the audit trail shows old entries shifted by the difference of the zones. On an installed instance the change needs an explicit confirmation. | T (CI: change refused without confirmation, stored time unchanged, PHP accepts the zone) | set the zone before productive use; a later change only under change control, with a backup before and the change recorded (old/new zone, date) |
| Archiving, retention (17) | Data stays in the database; exports CSV/PDF reports. No retention locking. | not evidenced | define retention in SOP |
| Supplier (3) | Open source by Grokability, Inc., public issue tracker, security advisories on GitHub; module maintained by its author without service contract. | not evidenced | assess project health; no SLA |

## 3. Result

Snipe-IT fits as an **equipment and asset register** with a usable audit
trail and access control. For a GMP use it lacks a mandatory reason for
change, compliant electronic signatures, a calibration workflow with
tolerances and out-of-tolerance handling, and protection of the audit trail
against database administrators. These gaps need SOPs and organisational
controls, or a dedicated calibration system for GMP-critical instruments.
Validation scope for a GMP use: IQ (versions, configuration, backup),
OQ of the configured functions with high risk (access, audit trail,
check-out, maintenance records, backup/restore), periodic review —
❰to be planned by the user's quality unit❱.
