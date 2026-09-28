# CPBL result sync

Ballpark Memories updates completed 2026 CPBL games without AI.

- Primary: CPBL advanced-stat game page, keyed by the existing Game ID (for example `2026-A-343`).
- Attendance: CPBL official single-game news page when an attendance figure is explicitly published.
- Missing fields are left missing; the sync never guesses values.
- GitHub Actions runs daily at 23:20 Taiwan time and can also be run manually.
- The app only displays official fields that exist in `data/results-2026.json`.

This is intentionally conservative: if CPBL changes its HTML or a field cannot be parsed reliably, that field is skipped rather than inferred.
