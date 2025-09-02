# Evvie Time Tracker — Known Bugs and Risky Areas

This document captures functional bugs, inconsistencies, and risks identified across the backend (Flask + SQLite), services, database schema/migrations, and frontend JS.

## Critical Bugs

- None currently.

## Functional Inconsistencies

- None currently.

## Validation and UX Defects

- None currently.

## Security Issues

- XSS risk in frontend due to direct `innerHTML` with unsanitized content.
  - Impact: Server-originated strings (error messages, names) are injected into DOM via template literals (e.g., import results). If these reflect user-uploaded CSV content, they could execute scripts in the browser.
  - Locations: 
    - `static/js/import-export.js` (renders `errors`/`warnings` via `innerHTML`)
    - Other views often use `innerHTML` with API data (employees/children tables, overlaps, etc.).
  - Fix: Escape content or use textContent when inserting user-controlled strings. Consider a small escapement utility.

- Path traversal in upload filename is unmitigated but currently not written to disk.
  - Impact: Filenames like `../../../etc/passwd` are accepted and echoed in UI; if later persisted, this becomes dangerous.
  - Fix: Sanitize filenames server-side; do not use untrusted filename in any filesystem path; escape in UI.

- No size/length limits on user-provided strings (names, codes, etc.).
  - Impact: Potential performance/memory strain and UX issues. Tests expect rejection or controlled behavior.
  - Fix: Add reasonable length caps and return 400 on excessive input.

## Portability Issues

- Non-portable `strftime` flags (`%-m/%-d`) used for human-readable names/messages.
  - Impact: Fails on Windows’ strftime implementation (and some locales).
  - Locations: 
    - `PayrollService.create_bulk_exclusions()` (`services/payroll_service.py`)
    - Similar patterns may exist in `ShiftService.auto_generate_shifts` messages.
  - Fix: Use `%m/%d` and strip leading zeros manually.

## Data Integrity and Migration Risks

- Destructive payroll period configuration.
  - Impact: `configure_periods` deletes all rows from `payroll_periods` before regeneration. If invoked unexpectedly, history is lost.
  - Fix: Add confirmation/state check, or soft-delete/backup strategy.

- Hour limit migration divides values by 2.
  - Impact: Migration from `max_hours_per_period` to `max_hours_per_week` halves `max` and `alert_threshold`. This assumes a 2-week period; it’s correct only if the old period was exactly 14 days.
  - Fix: Document explicitly; otherwise consider a safer, opt-in migration.

## Logic Edge Cases

- Midnight end time normalization in CSV import.
  - Impact: `12:00 AM` becomes `23:59:59` same day. If the source semantics assume next‑day midnight, imported duration is undercounted by almost 24h or mismatched to expectations.
  - Fix: Treat `12:00 AM` as end of day for same day is documented, but consider a config toggle or detection of cross‑midnight shifts (if business rules allow).

- PDF week grouping is relative to requested `start_date`, not the actual payroll period anchor.
  - Impact: PDF export groups into “Week 1/2” based on the arbitrary `start_date` parameter, which may not align with payroll periods.
  - Location: `ExportService.generate_pdf_report()`
  - Fix: Align to payroll periods (via `PayrollService`) or label as “First/Second half of range”.

- Overlaps endpoint loads all shifts without filters.
  - Impact: Potential performance issue on large datasets (full table scan + O(n^2) pair checks per employee/child/date).
  - Fix: Require date filters, or do overlap detection in SQL with window functions and pagination.

## Minor/Operational Issues

- `get_shifts` route does not cast `employee_id`/`child_id` query params to int.
  - Impact: Type inconsistency (strings bound as params) works in SQLite but is untidy and may hide validation errors.
  - Fix: Convert query params to integers when provided; return 400 on invalid types.

- SECRET key file writing in working directory.
  - Impact: `Config.get_or_create_secret_key()` writes `secret.key` to CWD. In read‑only environments this fails; leaking/committing the key is also possible.
  - Fix: Allow override via env, and guard writes in non‑writable environments.

## File/Code References (Quick Index)

- DB schema and migrations: `database.py`
- Shift business rules: `services/shift_service.py`
- Payroll services: `services/payroll_service.py`
- Import logic: `services/import_service.py`; routes: `routes/imports.py`
- Export logic: `services/export_service.py`; routes: `routes/exports.py` and `routes/payroll.py`
- Budgets: `services/budget_service.py`; routes: `routes/budget.py`
- Frontend injection risk hotspots: `static/js/**/*.js`, especially `import-export.js`

## Suggested Fixes Summary (Actionable)

- Remove invalid TIME CHECK; adjust or add proper DB constraints only if enforceable.
- Fix exclusions overlap SQL with a single standard interval condition and correct params.
- Create manual budgets when report-derived period exists (don’t update `id=None`).
- Add `replaced` to import CSV response payload.
- Standardize exports to include/exclude imported shifts consistently.
- Unify overlap detection logic by reusing service code in the overlaps route.
- Normalize CSV headers; improve error messages.
- Validate `HH:MM:SS` times; standardize JSON Content-Type checks.
- Escape/encode user-controlled strings in the frontend when using `innerHTML`.
- Replace non-portable `strftime` directives; strip leading zeros manually.
- Add length limits for names/codes; return 400 on excessive input.
- Consider guardrails for destructive payroll config and document hour-limit migration assumptions.

---
If you want, I can submit targeted patches for the highest-impact items (exclusions query, import response `replaced`, time validation, and the invalid CHECK constraint) in a small PR.
