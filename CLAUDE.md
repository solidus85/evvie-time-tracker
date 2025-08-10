# Evvie Time Tracker - Development Notes

## Important Rules
- Commit all changes to the git repository only when explicitly requested by user
- Keep files under 400 lines total
- Do not create scripts or md files without explicit direction or permission

## Project Overview
Local time management system for tracking employee hours working with children, with biweekly payroll periods (Thursday-Wednesday).

## Technology Stack
- Backend: Python Flask with SQLite database
- Frontend: HTML/JavaScript with calendar view
- No authentication (local-only)
- Central timezone preference

## Recent Work Completed (Latest Session)

### Exclusions Page Improvements - Time Field Support
1. **Database Changes**:
   - Added `start_time` and `end_time` columns to `exclusion_periods` table (TIME type, nullable)
   - Created migration in `database.py` to add these columns to existing databases
   
2. **Frontend Updates**:
   - Modified `exclusions.js` to display times alongside dates in table
   - Updated exclusion form to include optional time input fields
   - Added time formatting using existing `formatTime()` method
   
3. **Backend API Updates**:
   - Updated POST `/api/payroll/exclusions` to accept time fields
   - Added PUT `/api/payroll/exclusions/<id>` endpoint for updates
   - Modified `PayrollService.create_exclusion_period()` to handle times
   - Added `PayrollService.update_exclusion_period()` method
   
4. **Visual Improvements**:
   - Created new `exclusions.css` with styled containers and better spacing
   - Updated HTML structure with header section and table wrapper
   - Changed table headers to "Start Date/Time" and "End Date/Time"
   - Added hover effects and improved visual hierarchy

### Previous Completed Work
- File modularization (all files <400 lines)
- Exclusions moved from Settings to dedicated nav section
- Weekly hour limits (converted from per-period)
- Batch CSV import capability
- Standardized button styling
- Improved CSV warning formatting

## Database Schema
- `exclusion_periods`: id, name, start_date, end_date, start_time, end_time, reason, active, created_at
- `hour_limits`: Uses `max_hours_per_week` (not per period)
- All dates in ISO format (YYYY-MM-DD)
- Times in HH:MM:SS format

## File Organization
- **CSS Modules** (9 files): base, layout, components, calendar, tables, summary, import, config, exclusions
- **JS Modules** (9 files): app, dashboard, exclusions, employees, children, shifts, import-export, forms, config
- All imported via main style.css and index.html

## Key Business Rules
1. Payroll periods: biweekly Thursday-Wednesday
2. CSV imports are source of truth
3. Exclusion periods block manual entry (now with optional time ranges)
4. Hour limits per week within payroll periods
5. No overlapping shifts for same employee
6. Central timezone for all displays

## Next Potential Tasks
- Test exclusion functionality with time fields
- Add validation for time-based exclusions in shift creation
- Visual indicators on calendar for active exclusions
- Enhanced payroll reporting
- Data backup/restore features

## Testing Notes
- Server: `python app.py`
- Always test after changes before marking complete
- Check for database migration issues on first run