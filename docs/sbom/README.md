# Software bill of materials

CycloneDX 1.7 JSON of the runtime images, generated with syft v1.54.1 and
reduced to packages (file entries removed):

| File | Image | Packages |
| --- | --- | --- |
| `snipe-it.cdx.json` | `docker.io/snipe/snipe-it:v8.8.3@sha256:eb6d78c1…3218` | 463 |
| `mariadb.cdx.json` | `docker.io/library/mariadb:11.4.13@sha256:250e1609…1873` | 154 |

Main components:

| Component | Version | Licence |
| --- | --- | --- |
| Snipe-IT | 8.8.3 | AGPL-3.0 |
| Laravel framework | 12.69.3 | MIT |
| Laravel Passport | 12.4.3 | MIT |
| PHP (Ubuntu packages php8.3-*, libapache2-mod-php8.3) | 8.3.6-0ubuntu0.24.04.13 | PHP-3.01 |
| Apache httpd | 2.4.58-1ubuntu8.17 | Apache-2.0 |
| OpenSSL | 3.0.13-0ubuntu3.16 | Apache-2.0 |
| Ubuntu base | 24.04 | various |
| MariaDB server | 11.4.13 | GPL-2.0 |
| Module code and UI (this repository) | — | GPL-3.0-or-later; UI dependencies pinned in `ui/yarn.lock` |

Regenerate after an image change:

```bash
podman run --rm -v "$PWD/docs/sbom:/out:z" docker.io/anchore/syft:v1.54.1 \
  registry:<image@digest> -q -o cyclonedx-json=/out/<name>.cdx.json
```
