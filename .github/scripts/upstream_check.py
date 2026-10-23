#!/usr/bin/env python3
"""Compare the pinned upstream references with the newest available ones.

Environment:
  UPSTREAM_SETS    JSON list of image sets checked independently, e.g.
                   [{"name": "MariaDB", "images": ["docker.io/library/mariadb"],
                     "tag_regex": "^(?P<ver>11\\.4\\.\\d+)$"}]
                   "images": references without tag/digest; the first one is
                   queried, all of a set are pinned to the same tag.
                   "tag_regex": anchored regex a version tag must match; the
                   named group `ver` holds the part whose numbers are
                   compared. Empty = digest mode: the image is pinned by
                   digest and compared with the digest of its `latest` tag.
  UPSTREAM_IMAGES, TAG_REGEX, UPSTREAM_NAME
                   one set, when UPSTREAM_SETS is not given (older modules)
  PIN_FILES        files holding the pinned references (default build-images.sh)
A reference pinned as <image>:<tag>@sha256:<digest> stays pinned that way: the
bump writes the new tag together with the digest it has now.

Writes to $GITHUB_OUTPUT: newer (any set), current and newest (one line each,
"<name> <version>" per set), summary ("<name> <old> → <new>" per changed set),
first_ref (newest reference of the first image of the first set) and
.upstream_bump.sh with the sed commands that perform the bumps.
"""
import json
import os
import re
import subprocess
import sys

pin_files = os.environ.get("PIN_FILES", "build-images.sh").split()


def skopeo(*args):
    return json.loads(subprocess.run(["skopeo", *args], capture_output=True, text=True, check=True).stdout)


def pinned(image):
    for f in pin_files:
        for line in open(f):
            if line.lstrip().startswith("#"):
                continue  # comments may mention the image with a placeholder tag
            m = re.search(rf'{re.escape(image)}([:@][A-Za-z0-9_.:-]+(?:@sha256:[0-9a-f]{{64}})?)', line)
            if m:
                return m.group(1)
    print("pinned reference not found for", image, "in", pin_files, file=sys.stderr)
    sys.exit(1)


def check_set(images, pattern):
    """Return (current, newest, newer, bumps, newest_ref) for one image set."""
    if not pattern:  # digest mode
        bumps = []
        for img in images:
            cur = pinned(img)
            info = skopeo("inspect", f"docker://{img}:latest")
            bumps.append((img, cur, "@" + info["Digest"]))
        newer = any(c != n for _, c, n in bumps)
        current = bumps[0][1].lstrip("@")[7:19]
        newest = bumps[0][2].lstrip("@")[7:19]
        return current, newest, newer, bumps, images[0] + bumps[0][2]
    regex = re.compile(pattern)

    def numeric(tag):
        return [int(x) for x in re.findall(r"\d+", regex.match(tag).group("ver"))]

    tags = [t for t in skopeo("list-tags", f"docker://{images[0]}")["Tags"] if regex.match(t)]
    if not tags:
        print("no version tags found for", images[0], file=sys.stderr)
        sys.exit(1)
    newest_tag = max(tags, key=numeric)
    current_tag = pinned(images[0]).lstrip(":").split("@")[0]
    newer = regex.match(current_tag) is not None and numeric(newest_tag) > numeric(current_tag)
    bumps = []
    for img in images:
        cur = pinned(img)
        new = cur
        if newer:
            new = ":" + newest_tag
            if "@sha256:" in cur:
                new += "@" + skopeo("inspect", f"docker://{img}:{newest_tag}")["Digest"]
        bumps.append((img, cur, new))
    return current_tag, newest_tag, newer, bumps, f"{images[0]}:{newest_tag}"


if os.environ.get("UPSTREAM_SETS"):
    sets = json.loads(os.environ["UPSTREAM_SETS"])
else:
    sets = [{"name": os.environ.get("UPSTREAM_NAME", "upstream"),
             "images": os.environ["UPSTREAM_IMAGES"].split(),
             "tag_regex": os.environ.get("TAG_REGEX", "")}]

any_newer = False
current_parts, newest_parts, summary_parts, first_ref = [], [], [], ""
with open(".upstream_bump.sh", "w") as fp:
    fp.write("set -e\n")
    for i, s in enumerate(sets):
        current, newest, newer, bumps, newest_ref = check_set(s["images"], s.get("tag_regex", ""))
        if i == 0:
            first_ref = newest_ref
        print(f"{s['name']}: current={current} newest={newest} newer={newer}")
        current_parts.append(f"{s['name']} {current}")
        newest_parts.append(f"{s['name']} {newest}")
        if newer:
            any_newer = True
            summary_parts.append(f"{s['name']} {current} → {newest}")
            for img, cur, new in bumps:
                for f in pin_files:
                    fp.write(f"sed -i 's|{img}{cur}|{img}{new}|g' '{f}'\n")

with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as fp:
    fp.write(f"current={', '.join(current_parts)}\n")
    fp.write(f"newest={', '.join(newest_parts)}\n")
    fp.write(f"summary={', '.join(summary_parts)}\n")
    fp.write(f"first_ref={first_ref}\n")
    fp.write(f"newer={'true' if any_newer else 'false'}\n")
