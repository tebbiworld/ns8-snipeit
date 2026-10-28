# User requirements (URS) — ns8-snipeit

Status: draft derived from the module request (community thread "App request
– Snipe-IT (IT asset management)") and the maintainer's order; to be
confirmed by the requester ❰confirmation pending❱.
Version 0.3, 2026-10-28 (U-13, U-14 added for 1.1.0; U-13 reworded after review).

| ID | Requirement | Must/Should |
| --- | --- | --- |
| U-01 | Track IT assets, licenses, accessories, consumables and components on NethServer 8 with Snipe-IT. | Must |
| U-02 | Install and update from the NS8 Software Center like other modules; settings from the NS8 UI and `api-cli`. | Must |
| U-03 | No unauthenticated access: the Snipe-IT web installer must never be reachable from the network. | Must |
| U-04 | Run a PHP release that is not affected by CVE-2026-109618/109619 ("PHP2Shell"); keep it patched. | Must |
| U-05 | Login with a user domain of the cluster or an LDAP server of its own, optionally limited to a group; local accounts keep working. | Must |
| U-06 | Directory passwords are not stored in Snipe-IT; secrets are not stored in the NS8 module environment (Redis). | Must |
| U-07 | Backup and restore through the NS8 backup, including the database; clone/move to another node. | Must |
| U-08 | Mails (alerts, acceptance requests) through the cluster smarthost. | Should |
| U-09 | Real client addresses in logs and login throttling behind the proxy. | Should |
| U-10 | Scheduled Snipe-IT tasks run and are visible to the administrator. | Should |
| U-11 | Directory users can be imported before their first login. | Should |
| U-12 | Assessment of the fitness of Snipe-IT for equipment records in a GMP environment (see 03). | Should |
| U-13 | The time zone of Snipe-IT can be chosen in the module settings (issue #3); a later change must not shift stored times unnoticed. | Should |
| U-14 | Directory users get a meaningful first name, also when the directory has `givenName`. | Should |
