#
# Copyright (C) 2026 tebbi
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Time zones Snipe-IT may use (APP_TIMEZONE).

The list is etc/timezones, made by tools/gen-timezones.sh from the Snipe-IT
image: the zones its PHP accepts. The node's own list is not used: it has
legacy names (US/Eastern, Asia/Calcutta) that PHP in the image refuses,
which would leave Snipe-IT in UTC without a word.
"""

import os

DEFAULT = "UTC"
LIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "etc", "timezones")


def available():
    """Sorted list of the time zone names Snipe-IT accepts."""
    with open(LIST_FILE) as fp:
        return [line.strip() for line in fp if line.strip()]


def is_valid(name):
    return bool(name) and name in available()
