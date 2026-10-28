#
# Copyright (C) 2026 tebbi
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Time zones Snipe-IT may use (APP_TIMEZONE): the IANA names of the node,
read from /usr/share/zoneinfo.

The copies under posix/ and right/ (leap seconds) and the pseudo zones
"localtime" and "Factory" are left out: they are no place a user picks.
"""

import re
import zoneinfo

DEFAULT = "UTC"
# Same as the pattern of configure-module/validate-input.json. The names go
# into SQL string literals of actions/configure-module/08timezone: no quotes,
# no backslashes, no spaces.
NAME = re.compile(r"[A-Za-z0-9_+-]+(/[A-Za-z0-9_+-]+)*")
_EXCLUDED_PREFIXES = ("posix/", "right/")
_EXCLUDED = {"localtime", "Factory"}


def available():
    """Sorted list of the time zone names of the node."""
    return sorted(name for name in zoneinfo.available_timezones()
                  if NAME.fullmatch(name)
                  and name not in _EXCLUDED
                  and not name.startswith(_EXCLUDED_PREFIXES))


def is_valid(name):
    return bool(name) and name in available()
