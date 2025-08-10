# Evvie Time Tracker - Development Notes

## Important Rules
- Commit all changes to the git repository only when explicitly requested by user
- Keep files under 400 lines total
- Do not create scripts or md files without explicit direction or permission

## Project Overview
Local time management system for tracking employee hours working with children, with biweekly payroll periods (Thursday-Wednesday). Now expanding to include budget tracking and hour forecasting capabilities.

## Technology Stack
- Backend: Python Flask with SQLite database
- Frontend: HTML/JavaScript with calendar view
- No authentication (local-only)
- Central timezone preference

## Recent Work Completed (Current Session - 2025-08-10)

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

### Major Enhancements Completed
1. **XOR Exclusions System**:
   - Exclusions now specific to employee OR child (not both)
   - Added time ranges to exclusions
   - Bulk exclusion entry for recurring patterns
   - Exclusions show as calendar entries (not blocking)

2. **Pagination System**:
   - Added to exclusions page (10/25/50/All items)
   - Client-side pagination with controls
   - Page size selector and navigation buttons

3. **Export Improvements**:
   - Only exports manual shifts (not imported)
   - Fixed hours to 2 decimal places
   - PDF grouped by employee, child, and week
   - Left-aligned tables with proper formatting
   - Fixed 415 error with proper JSON requests

4. **Import Enhancement**:
   - CSV imports now replace matching manual shifts
   - Tracks replaced count in import summary
   - Imported shifts are source of truth

5. **Bug Fixes**:
   - Fixed payroll period navigation (added missing endpoint)
   - Fixed shift conflict handling (409 status, type conversions)
   - Fixed hour limit comparisons (floating-point precision)
   - Default export dates to current period
   - Pre-select child in shift form from dashboard

### Budget & Forecasting Expansion (Scaffolding Complete)

1. **Database Layer**:
   - Added tables: `child_budgets`, `employee_rates`, `budget_allocations`
   - Added `hourly_rate` column to employees table
   - Safe migrations for all changes

2. **Service Layer**:
   - `BudgetService`: Manages budgets, rates, allocations, CSV import
   - `ForecastService`: Projections, patterns, availability, recommendations

3. **API Layer**:
   - `/api/budget/*`: Budget CRUD, rates, allocations, utilization
   - `/api/forecast/*`: Available hours, patterns, projections, recommendations
   - Registered in app.py

4. **Frontend Todo List Created** (11 tasks):
   - High Priority: Navigation, budget management, import, utilization
   - Medium: Rates, available hours, styling
   - All following existing UI patterns

## Database Schema
### Core Tables
- `employees`: id, friendly_name, system_name, hourly_rate, active
- `children`: id, name, code, active
- `shifts`: id, employee_id, child_id, date, start_time, end_time, is_imported, status
- `payroll_periods`: id, start_date, end_date
- `exclusion_periods`: id, name, start_date, end_date, start_time, end_time, employee_id, child_id, reason, active
- `hour_limits`: id, employee_id, child_id, max_hours_per_week, alert_threshold

### New Budget Tables
- `child_budgets`: id, child_id, period_start, period_end, budget_amount, budget_hours, notes
- `employee_rates`: id, employee_id, hourly_rate, effective_date, end_date, notes
- `budget_allocations`: id, child_id, employee_id, period_id, allocated_hours, notes

### Conventions
- All dates in ISO format (YYYY-MM-DD)
- Times in HH:MM:SS format
- XOR constraint on exclusions (employee OR child, not both)

## File Organization
- **CSS Modules** (9+ files): base, layout, components, calendar, tables, summary, import, config, exclusions, (budget, forecast pending)
- **JS Modules** (9+ files): app, dashboard, exclusions, employees, children, shifts, import-export, forms, config, (budget, forecast pending)
- **Python Services**: shift_service, payroll_service, employee_service, child_service, import_service, export_service, config_service, budget_service, forecast_service
- **Routes**: employees, children, shifts, payroll, imports, exports, config, budget, forecast
- All imported via main style.css and index.html

## Key Business Rules
1. Payroll periods: biweekly Thursday-Wednesday
2. CSV imports are source of truth (replace matching manual shifts)
3. Exclusion periods show as calendar entries (employee XOR child specific)
4. Hour limits per week within payroll periods
5. No overlapping shifts for same employee
6. Central timezone for all displays
7. Only manual shifts are exported (not imported ones)
8. Budget tracking by child with hour and dollar amounts
9. Employee rates with effective date ranges
10. Forecast based on historical patterns

## Current State & Next Steps
### Backend Complete:
- All budget/forecast services and routes implemented
- Database migrations in place
- API endpoints tested and working
- No breaking changes to existing functionality

### Frontend Pending (11 tasks in todo):
1. Add Budget & Forecast navigation items
2. Create budget.js and forecast.js modules
3. Child Budget Management interface
4. Budget Import functionality
5. Employee Rates Management
6. Budget Utilization Dashboard
7. Available Hours display
8. CSS modules for styling

### Session Status:
- Last commit: "Major enhancements to time tracking functionality"
- App running without errors
- Ready for frontend implementation

## Testing Notes
- Server: `python app.py`
- Always test after changes before marking complete
- Check for database migration issues on first run