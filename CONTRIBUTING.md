# Contributing

1. Create a focused branch.
2. Keep UI changes consistent with GNOME/libadwaita conventions.
3. Run `make lint test` before opening a pull request.
4. Do not add network telemetry or upload audio without an explicit opt-in design and a privacy review.
5. Add new user-facing strings to the RU/EN maps in `app/src/wayvoice/i18n.py` and all eight JSON catalogues in `app/src/wayvoice/locales/`. Preserve format parameters such as `{version}`; the translation tests check key and parameter coverage.

For larger changes, open an issue first so architecture and UX can be discussed before implementation.
