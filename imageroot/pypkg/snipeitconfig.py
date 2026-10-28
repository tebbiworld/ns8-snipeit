#
# Copyright (C) 2026 tebbi
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Settings the module manages inside Snipe-IT.

app_env() is the environment of the app container (state/snipeit.env,
written at every start by bin/snipeit-config): URL, proxy, mail and session
settings. ldap_settings() is the directory login as Snipe-IT stores it in its
settings table; bin/snipeit-sync hands it to container/ns8-snipeit.php at
every start, so a changed bind password of a user domain is applied by a
restart (event user-domain-changed).

Both carry secrets (SMTP password, LDAP bind password): they are written only
to private files outside the backup or passed on stdin, never to the module
environment.
"""

import os
import urllib.parse

import ldapsettings

# The ldapproxy of a user domain and a same-node LDAP server listen on the
# node loopback: the snipeit pod uses slirp4netns with allow_host_loopback,
# where 10.0.2.2 is the host loopback.
HOST_LOOPBACK = "10.0.2.2"
# Traefik reaches the app through the port that the pod publishes on
# 127.0.0.1; slirp4netns (port handler rootlesskit) hands those connections
# over from this address, so it is the only proxy whose X-Forwarded-* headers
# Snipe-IT trusts. The port is bound to the loopback, nothing else can use it.
POD_PROXY_ADDRESS = "10.0.2.100"
UPLOAD_LIMIT_MB = 100
SESSION_IDLE_MINUTES = 120
DEFAULT_GROUP_FILTER_AD = "(objectClass=user)(objectCategory=person)"
DEFAULT_FILTER_RFC2307 = "(objectClass=posixAccount)"


def _env(name, default=""):
    return os.environ.get(name, default)


def env_value(value):
    """A value for a podman --env-file line: one line, taken literally."""
    value = str(value)
    if "\n" in value or "\r" in value:
        raise ValueError("line breaks are not allowed in environment values")
    return value


def mail_env(smarthost):
    """MAIL_* variables from the cluster smarthost (bin/discover-smarthost)."""
    host = _env("TRAEFIK_HOST")
    sender = _env("MAIL_FROM") or ("snipeit@" + host if host else "")
    env = {"MAIL_FROM_ADDR": sender, "MAIL_FROM_NAME": "Snipe-IT",
           "MAIL_REPLYTO_ADDR": sender, "MAIL_REPLYTO_NAME": "Snipe-IT"}
    if not smarthost.get("SMTP_ENABLED"):
        # no smarthost: mails are written to the log instead of being lost
        # in a connection error
        env["MAIL_MAILER"] = "log"
        return env
    env.update({
        "MAIL_MAILER": "smtp",
        "MAIL_HOST": smarthost.get("SMTP_HOST", ""),
        "MAIL_PORT": smarthost.get("SMTP_PORT", "25"),
        "MAIL_USERNAME": smarthost.get("SMTP_USERNAME") or "null",
        "MAIL_PASSWORD": smarthost.get("SMTP_PASSWORD") or "null",
        # NS8 "tls" is TLS from the first byte (smtps), "starttls" and
        # "none" let Symfony upgrade the connection when the server offers it
        "MAIL_ENCRYPTION": "ssl" if smarthost.get("SMTP_ENCRYPTION") == "tls" else "tls",
        "MAIL_TLS_VERIFY_PEER": "1" if smarthost.get("SMTP_TLSVERIFY") else "0",
    })
    return env


def app_env(smarthost):
    """Environment of the app container."""
    host = _env("TRAEFIK_HOST")
    https_only = _env("TRAEFIK_HTTP2HTTPS", "True") == "True"
    env = {
        "APP_ENV": "production",
        "APP_DEBUG": "false",
        "APP_URL": "https://" + host if host else "http://localhost",
        "APP_TIMEZONE": _env("SNIPEIT_TIMEZONE", "UTC") or "UTC",
        "APP_TRUSTED_PROXIES": POD_PROXY_ADDRESS,
        # Snipe-IT trusts no forwarded header unless named here; Traefik
        # drops the X-Forwarded-* headers a client sends and sets its own
        "APP_TRUSTED_HEADERS": "HEADER_X_FORWARDED_TRAEFIK",
        "DB_CONNECTION": "mysql",
        "DB_HOST": "127.0.0.1",
        "DB_PORT": "3306",
        "DB_DATABASE": "snipeit",
        "DB_USERNAME": "snipeit",
        # sessions in the database: they survive a container restart and
        # are part of the dump
        "SESSION_DRIVER": "database",
        "SECURE_COOKIES": "true",
        # log out after two idle hours (default of the image: 200 hours)
        "SESSION_LIFETIME": str(SESSION_IDLE_MINUTES),
        "ENABLE_HSTS": "true" if https_only else "false",
        "LOG_CHANNEL": "stderr",
        # the weekly Snipe-IT backup must not copy the .env with APP_KEY
        "BACKUP_ENV": "false",
        "PHP_UPLOAD_LIMIT": str(UPLOAD_LIMIT_MB),
    }
    env.update(mail_env(smarthost))
    return env


def write_env_file(path, env):
    """Write a podman env file that only the module user can read."""
    lines = [f"{key}={env_value(value)}" for key, value in env.items()]
    old_umask = os.umask(0o077)
    try:
        with open(path + ".tmp", "w") as fp:
            fp.write("\n".join(lines) + "\n")
        os.chmod(path + ".tmp", 0o600)
        os.replace(path + ".tmp", path)
    finally:
        os.umask(old_umask)


def ldap_filter_escape(value):
    """RFC 4515 escaping of a value inside an LDAP filter."""
    return "".join("\\%02x" % ord(ch) if ch in "*()\\\0" else ch for ch in value)


def group_dn(conn):
    """The DN of the login group: a DN is used as is, a group name is looked
    up in the directory (Active Directory only, see 05validate)."""
    group = conn["group"]
    if not group or "=" in group:
        return group
    import ssl
    import ldap3
    # ldap3 checks no certificate unless told to: follow the TLS check setting
    # of the directory (the bind password is sent on this connection)
    tls = ldap3.Tls(validate=ssl.CERT_REQUIRED if conn["tls_verify"] else ssl.CERT_NONE)
    # get_info=NONE: by default ldap3 reads the schema right after StartTLS,
    # before the bind, which Active Directory refuses without authentication
    server = ldap3.Server(conn["host"], port=conn["port"], use_ssl=conn["tls"] == "ssl", tls=tls,
                          get_info=ldap3.NONE, connect_timeout=5)
    ldapconn = ldap3.Connection(server, user=conn["bind_dn"], password=conn["bind_password"],
                                receive_timeout=10, raise_exceptions=True)
    if conn["tls"] == "starttls":
        ldapconn.start_tls()
    ldapconn.bind()
    try:
        ldapconn.search(conn["base_dn"],
                        "(&(objectClass=group)(sAMAccountName=%s))" % ldap_filter_escape(group),
                        attributes=[])
        if not ldapconn.entries:
            raise LookupError(f"group {group} not found")
        return ldapconn.entries[0].entry_dn
    finally:
        ldapconn.unbind()


def dns_domain(base_dn):
    """The DNS name of an Active Directory domain from its base DN:
    "OU=Staff,DC=ad,DC=example,DC=org" -> "ad.example.org". Snipe-IT binds as
    <login>@<ad_domain> when its search bind fails (Ldap::findAndBindUserLdap),
    otherwise with the mail domain of the first super user."""
    import ldap3.utils.dn
    try:
        parts = ldap3.utils.dn.parse_dn(base_dn)
    except Exception:
        return ""
    return ".".join(value for attr, value, _ in parts if attr.lower() == "dc")


def ldap_settings():
    """The LDAP columns of the Snipe-IT settings table, or {"enabled": False}.

    Raises when the directory is configured but its group cannot be
    resolved: the caller turns the directory login off then (fail closed).
    """
    conn = ldapsettings.connection(active=_env("LDAP_ENABLED") == "true")
    if not conn:
        return {"enabled": False}
    ad = conn["schema"] == "ad"
    host = HOST_LOOPBACK if conn["host"] in ("127.0.0.1", "localhost", "::1") else conn["host"]
    scheme = "ldaps" if conn["tls"] == "ssl" else "ldap"
    if ad:
        # Snipe-IT lower-cases the attribute names it reads
        username_field = (conn["user_attribute"] or "sAMAccountName").lower()
        user_filter = DEFAULT_GROUP_FILTER_AD
    else:
        username_field = (conn["user_attribute"] or "uid").lower()
        user_filter = DEFAULT_FILTER_RFC2307
    if conn["group"]:
        # LDAP_MATCHING_RULE_IN_CHAIN: members of nested groups count too
        user_filter += "(memberOf:1.2.840.113556.1.4.1941:=%s)" % ldap_filter_escape(group_dn(conn))
    return {
        "enabled": True,
        # Snipe-IT wraps the filter as "(<filter>(<attribute>=<login>))"
        "server": f"{scheme}://{urllib.parse.quote(host, safe='.:-[]')}:{int(conn['port'])}",
        "start_tls": conn["tls"] == "starttls",
        "ignore_certificate": not conn["tls_verify"],
        "base_dn": conn["base_dn"],
        "bind_dn": conn["bind_dn"],
        "bind_password": conn["bind_password"],
        "filter": "&" + user_filter,
        "username_field": username_field,
        "auth_filter_query": username_field + "=",
        # Snipe-IT maps one attribute per field, without fallback, and needs
        # a first name (the import refuses a user without one). NS8 creates
        # users without givenName and with an optional displayName: the
        # login attribute is always there and is the default. givenName
        # suits directories where every user has it. The display name shown
        # by Snipe-IT is displayName, or first + last name when it is empty.
        "first_name_field": "givenname" if _env("LDAP_FIRST_NAME") == "givenname" else username_field,
        "last_name_field": "sn",
        "display_name_field": "displayname",
        "email_field": "mail",
        "is_ad": ad,
        "ad_domain": dns_domain(conn["base_dn"]) if ad else "",
    }
