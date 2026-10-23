# User manual — ns8-snipeit

Snipe-IT has its own user documentation: https://snipe-it.readme.io/docs.
This page covers what the NS8 module changes.

- **Log in** at `https://<host>/` with your directory account (if the
  directory login is on) or with a local Snipe-IT account. A new directory
  user sees only "My assets" until a super user grants permissions.
- **Password**: directory users change their password in the directory, not
  in Snipe-IT.
- **Session**: you are logged out after two idle hours.
- **API**: personal API keys are created under your profile (if your
  permissions allow it); the REST API is at `https://<host>/api/v1/`.
- **Errors**: "These credentials do not match our records" — wrong password,
  or your account is not in the login group; after 5 failed attempts wait a
  minute.
