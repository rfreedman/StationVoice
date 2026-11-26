# User roles

StationVoice uses local username/password accounts. An Admin assigns each user’s role in **Admin → Users**, or via the CLI:

```bash
python -m app users create USERNAME --role editor
```

Valid `--role` values: `admin`, `editor`, `readonly` (default).

## Roles

| Capability | Admin | Editor | Read-Only |
|---|---|---|---|
| Sign in, Home, Help, Phonemes view | yes | yes | yes |
| Speak preview and Newsline preview | yes | yes | yes |
| Create, edit, delete announcements | yes | yes | no |
| Create, edit, delete schedules | yes | yes | no |
| Trigger now (when enabled) | yes | yes | no |
| Settings (baseline shuffle, slot window) | yes | yes | no |
| Phoneme dictionary edits | yes | yes | no |
| Newsline check / dismiss | yes | yes | no |
| Admin section (Users, Environment, Branding) | yes | no | no |

## Admin section

Only **Admin** users see the Admin nav and can call Admin APIs:

- **Users** — create accounts, change roles and passwords, delete users
- **Environment** — runtime config history, email-alert toggle, application restart
- **Branding** — logo and favicon upload and display size

Editors and Read-Only users are redirected away from `#/admin/*` routes.

## First setup and last Admin

The first account created on a fresh install is always **Admin**. The store refuses to demote or delete the last remaining Admin so the station is never locked out of user management.
