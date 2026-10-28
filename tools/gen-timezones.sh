#!/bin/bash

#
# Copyright (C) 2026 tebbi
# SPDX-License-Identifier: GPL-3.0-or-later
#

# Write imageroot/etc/timezones: the time zones Snipe-IT may use
# (APP_TIMEZONE). A zone must be a file of the tzdata of the Snipe-IT image
# and be accepted by its PHP (date_default_timezone_set). The image is Ubuntu
# without tzdata-legacy: names like US/Eastern are not in the list, PHP would
# refuse them and Snipe-IT would run in UTC. Run it again when
# build-images.sh pins a new Snipe-IT image.
#
# Usage: tools/gen-timezones.sh   (from the repository root, needs podman)

set -euo pipefail

snipeit_image=$(sed -n 's/^snipeit_image="\(.*\)"$/\1/p' build-images.sh)

podman run --rm -i --entrypoint /bin/sh "${snipeit_image}" -c '
    cd /usr/share/zoneinfo && find . \( -type f -o -type l \) | sed "s|^\./||" \
    | grep -E "^[A-Za-z0-9_+-]+(/[A-Za-z0-9_+-]+)*$" \
    | grep -vE "^(posix|right)/|^(localtime|Factory|posixrules|leapseconds|tzdata\.zi|zone\.tab|zone1970\.tab|iso3166\.tab|SECURITY)$" \
    | LC_ALL=C sort -u \
    | php -r "
        while ((\$zone = fgets(STDIN)) !== false) {
            \$zone = trim(\$zone);
            if (@date_default_timezone_set(\$zone)) { echo \$zone, PHP_EOL; }
        }"' > imageroot/etc/timezones
wc -l imageroot/etc/timezones
