#!/bin/bash

#
# Copyright (C) 2026 tebbi
# SPDX-License-Identifier: GPL-3.0-or-later
#

set -e

images=()
repobase="${REPOBASE:-ghcr.io/tebbiworld}"
reponame="snipeit"

# Official Snipe-IT image (grokability), pinned by tag and digest. The image
# is Ubuntu based and ships the PHP of Ubuntu: Ubuntu backports security fixes
# without changing the upstream version, so PHP_VERSION stays 8.3.6. What
# counts is the package version: 8.3.6-0ubuntu0.24.04.13 (or later) carries
# the fix for CVE-2026-109618/109619 ("PHP2Shell"), see the package changelog
# (/usr/share/doc/php8.3-cli/changelog.Debian.gz). .github/workflows/auto-release.yml
# checks it before a new upstream release is pinned.
# Exposed to the units as ${SNIPE_IT_IMAGE} through org.nethserver.images.
snipeit_image="docker.io/snipe/snipe-it:v8.8.3@sha256:eb6d78c1bdae46d15177b149fcc14d7cd795d9f6c17e53dc4d87e04da9653218"
# MariaDB LTS (${MARIADB_IMAGE})
mariadb_image="docker.io/library/mariadb:11.4.13@sha256:250e1609e93c0e6aecf64bfbab2d84d5e89d2481540fe77447ff6c855c3b1873"

container=$(buildah from scratch)

if ! buildah containers --format "{{.ContainerName}}" | grep -q nodebuilder-snipeit; then
    echo "Pulling NodeJS runtime..."
    buildah from --name nodebuilder-snipeit -v "${PWD}:/usr/src:Z" docker.io/library/node:24.16.0-slim
fi

echo "Build static UI files with node..."
buildah run \
    --workingdir=/usr/src/ui \
    --env="NODE_OPTIONS=--openssl-legacy-provider" \
    nodebuilder-snipeit \
    sh -c "yarn install --frozen-lockfile && yarn build"

buildah add "${container}" imageroot /imageroot
buildah add "${container}" ui/dist /ui
# One TCP port for the web server behind Traefik (routeadm). The directory
# login of a cluster user domain goes through the node's ldapproxy
# (cluster:accountconsumer).
buildah config --entrypoint=/ \
    --label="org.nethserver.authorizations=traefik@node:routeadm cluster:accountconsumer" \
    --label="org.nethserver.tcp-ports-demand=1" \
    --label="org.nethserver.rootfull=0" \
    --label="org.nethserver.images=${snipeit_image} ${mariadb_image}" \
    --label="org.nethserver.min-core=3.22.0" \
    "${container}"
buildah commit "${container}" "${repobase}/${reponame}"

images+=("${repobase}/${reponame}")

if [[ -n "${CI}" ]]; then
    printf "images=%s\n" "${images[*],,}" >> "${GITHUB_OUTPUT}"
else
    printf "Publish the images with:\n\n"
    for image in "${images[@],,}"; do printf "  buildah push %s docker://%s:%s\n" "${image}" "${image}" "${IMAGETAG:-latest}" ; done
    printf "\n"
fi
