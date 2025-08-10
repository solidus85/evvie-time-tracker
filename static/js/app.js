class App {
    constructor() {
        this.currentView = 'dashboard';
        this.currentPeriod = null;
        this.periods = [];
        this.employees = [];
        this.children = [];
        this.selectedChildId = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.showView('dashboard');
    }

    setupEventListeners() {
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const viewName = e.target.id.replace('btn-', '');
                this.showView(viewName);
            });
        });

        document.getElementById('prev-period').addEventListener('click', () => this.navigatePeriod(1));
        document.getElementById('next-period').addEventListener('click', () => this.navigatePeriod(-1));
        
        document.getElementById('add-employee').addEventListener('click', () => this.showEmployeeForm());
        document.getElementById('add-child').addEventListener('click', () => this.showChildForm());
        document.getElementById('add-hour-limit').addEventListener('click', () => this.showHourLimitForm());
        document.getElementById('add-exclusion').addEventListener('click', () => this.showExclusionForm());
        
        document.getElementById('validate-csv').addEventListener('click', () => this.validateCSV());
        document.getElementById('import-csv').addEventListener('click', () => this.importCSV());
        
        document.getElementById('export-pdf').addEventListener('click', () => this.exportData('pdf'));
        document.getElementById('export-csv').addEventListener('click', () => this.exportData('csv'));
        document.getElementById('export-json').addEventListener('click', () => this.exportData('json'));
        
        document.getElementById('configure-periods').addEventListener('click', () => this.configurePeriods());
        
        document.getElementById('child-filter').addEventListener('change', (e) => {
            this.selectedChildId = e.target.value ? parseInt(e.target.value) : null;
            this.loadDashboard();
        });
        
        document.querySelector('.close').addEventListener('click', () => this.closeModal());
    }

    async loadInitialData() {
        try {
            const [employees, children, periods] = await Promise.all([
                this.api('/api/employees'),
                this.api('/api/children'),
                this.api('/api/payroll/periods')
            ]);
            
            this.employees = employees;
            this.children = children;
            this.periods = periods;
            
            // Set default selected child to first in list
            if (this.children.length > 0 && !this.selectedChildId) {
                this.selectedChildId = this.children[0].id;
            }
            
            this.populateChildDropdown();
            
            if (this.currentView === 'dashboard') {
                await this.loadCurrentPeriod();
            }
        } catch (error) {
            this.showToast('Failed to load initial data', 'error');
        }
    }

    async loadCurrentPeriod() {
        try {
            const period = await this.api('/api/payroll/periods/current');
            this.currentPeriod = period;
            await this.loadDashboard();
        } catch (error) {
            document.getElementById('period-label').textContent = 'No periods configured';
            document.getElementById('calendar-grid').innerHTML = '<p>Please configure payroll periods in Settings</p>';
        }
    }

    async loadDashboard() {
        if (!this.currentPeriod || !this.selectedChildId) return;
        
        document.getElementById('period-label').textContent = 
            `${this.formatDate(this.currentPeriod.start_date)} - ${this.formatDate(this.currentPeriod.end_date)}`;
        
        const shifts = await this.api(`/api/shifts?start_date=${this.currentPeriod.start_date}&end_date=${this.currentPeriod.end_date}&child_id=${this.selectedChildId}`);
        this.renderCalendar(this.currentPeriod, shifts);
        
        // Calculate summary from filtered shifts
        this.renderChildSummaryFromShifts(shifts, this.selectedChildId);
    }
    
    populateChildDropdown() {
        const dropdown = document.getElementById('child-filter');
        if (!dropdown) return;
        
        dropdown.innerHTML = this.children
            .filter(c => c.active)
            .map(child => `<option value="${child.id}" ${child.id === this.selectedChildId ? 'selected' : ''}>${child.name}</option>`)
            .join('');
    }

    renderCalendar(period, shifts) {
        const grid = document.getElementById('calendar-grid');
        grid.innerHTML = '';
        
        const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        days.forEach(day => {
            const header = document.createElement('div');
            header.className = 'calendar-header';
            header.textContent = day;
            grid.appendChild(header);
        });
        
        const startDate = new Date(period.start_date + 'T00:00:00');
        const endDate = new Date(period.end_date + 'T00:00:00');
        
        const firstDayOfWeek = startDate.getDay();
        for (let i = 0; i < firstDayOfWeek; i++) {
            const empty = document.createElement('div');
            empty.className = 'calendar-day';
            grid.appendChild(empty);
        }
        
        const currentDate = new Date(startDate);
        while (currentDate <= endDate) {
            const dayDiv = document.createElement('div');
            dayDiv.className = 'calendar-day';
            if (currentDate.getDay() === 0 || currentDate.getDay() === 6) {
                dayDiv.classList.add('weekend');
            }
            
            const dateStr = currentDate.toISOString().split('T')[0];
            const dayShifts = shifts.filter(s => s.date === dateStr)
                .sort((a, b) => a.start_time.localeCompare(b.start_time));
            
            const dayNumber = document.createElement('div');
            dayNumber.className = 'day-number';
            dayNumber.textContent = currentDate.getDate();
            dayDiv.appendChild(dayNumber);
            
            const addBtn = document.createElement('button');
            addBtn.className = 'day-add-btn';
            addBtn.textContent = '+';
            addBtn.onclick = () => this.showShiftForm(dateStr);
            dayDiv.appendChild(addBtn);
            
            dayShifts.forEach(shift => {
                const shiftDiv = document.createElement('div');
                shiftDiv.className = 'shift-entry';
                if (shift.is_imported) shiftDiv.classList.add('imported');
                if (shift.service_code && shift.service_code.toLowerCase().includes('paid parent of minor')) {
                    shiftDiv.classList.add('parent-paid');
                }
                
                const startTime = this.formatTime(shift.start_time);
                const endTime = this.formatTime(shift.end_time);
                const hours = this.calculateShiftHours(shift.start_time, shift.end_time);
                
                shiftDiv.innerHTML = `
                    <div class="shift-time">${startTime}-${endTime} (${hours}h)</div>
                    <div class="shift-employee">${shift.employee_name}</div>
                `;
                shiftDiv.onclick = () => this.showShiftDetails(shift);
                dayDiv.appendChild(shiftDiv);
            });
            
            grid.appendChild(dayDiv);
            currentDate.setDate(currentDate.getDate() + 1);
        }
    }

    renderSummary(summary) {
        const summaryDiv = document.getElementById('period-summary');
        summaryDiv.innerHTML = `
            <h3>Period Summary</h3>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="label">Total Shifts</div>
                    <div class="value">${summary.total_shifts}</div>
                </div>
                <div class="summary-item">
                    <div class="label">Total Hours</div>
                    <div class="value">${summary.total_hours}</div>
                </div>
                <div class="summary-item">
                    <div class="label">Imported</div>
                    <div class="value">${summary.imported_shifts}</div>
                </div>
                <div class="summary-item">
                    <div class="label">Manual</div>
                    <div class="value">${summary.manual_shifts}</div>
                </div>
            </div>
        `;
    }
    
    renderChildSummaryFromShifts(shifts, childId) {
        const selectedChild = this.children.find(c => c.id === childId);
        const childName = selectedChild ? selectedChild.name : 'Unknown';
        
        // Calculate week boundary (7 days after period start)
        const periodStart = new Date(this.currentPeriod.start_date + 'T00:00:00');
        const weekBoundary = new Date(periodStart);
        weekBoundary.setDate(weekBoundary.getDate() + 7);
        const weekBoundaryStr = weekBoundary.toISOString().split('T')[0];
        
        // Calculate employee hours by week
        const employeeWeeklyHours = {};
        let totalHours = 0;
        
        shifts.forEach(shift => {
            const hours = this.calculateShiftHours(shift.start_time, shift.end_time);
            const hoursNum = this.parseHours(hours);
            const isWeek1 = shift.date < weekBoundaryStr;
            
            if (!employeeWeeklyHours[shift.employee_name]) {
                employeeWeeklyHours[shift.employee_name] = {
                    week1: 0,
                    week2: 0,
                    total: 0
                };
            }
            
            if (isWeek1) {
                employeeWeeklyHours[shift.employee_name].week1 += hoursNum;
            } else {
                employeeWeeklyHours[shift.employee_name].week2 += hoursNum;
            }
            employeeWeeklyHours[shift.employee_name].total += hoursNum;
            totalHours += hoursNum;
        });
        
        // Convert to array and sort
        const employeeBreakdown = Object.entries(employeeWeeklyHours)
            .map(([name, hours]) => ({
                name,
                week1: hours.week1.toFixed(2),
                week2: hours.week2.toFixed(2),
                total: hours.total.toFixed(2)
            }))
            .sort((a, b) => a.name.localeCompare(b.name));
        
        const summaryDiv = document.getElementById('period-summary');
        summaryDiv.innerHTML = `
            <h3>Period Summary for ${childName}</h3>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="label">Total Hours (All Employees)</div>
                    <div class="value">${totalHours.toFixed(2)}</div>
                </div>
            </div>
            <h4 style="margin-top: 20px; margin-bottom: 10px;">Employee Breakdown (Thursday-Wednesday weeks)</h4>
            <div class="employee-weekly-breakdown">
                ${employeeBreakdown.map(emp => `
                    <div class="employee-section">
                        <div class="employee-name">${emp.name}</div>
                        <div class="weekly-hours">
                            <div class="week-row">
                                <span class="week-label">Week 1:</span>
                                <span class="week-value ${parseFloat(emp.week1) > 40 ? 'hours-warning' : ''}">${emp.week1} hrs${parseFloat(emp.week1) > 40 ? ' ⚠️' : ''}</span>
                            </div>
                            <div class="week-row">
                                <span class="week-label">Week 2:</span>
                                <span class="week-value ${parseFloat(emp.week2) > 40 ? 'hours-warning' : ''}">${emp.week2} hrs${parseFloat(emp.week2) > 40 ? ' ⚠️' : ''}</span>
                            </div>
                            <div class="week-row total-row">
                                <span class="week-label">Total:</span>
                                <span class="week-value">${emp.total} hrs</span>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    parseHours(hoursStr) {
        // Convert hour string (e.g., "8", "8.5", "8:45") to decimal
        if (hoursStr.includes(':')) {
            const [hours, minutes] = hoursStr.split(':').map(Number);
            return hours + minutes / 60;
        }
        return parseFloat(hoursStr);
    }
    
    renderChildSummary(summary, childId) {
        const selectedChild = this.children.find(c => c.id === childId);
        const childName = selectedChild ? selectedChild.name : 'Unknown';
        
        // Find child total hours
        let childHours = 0;
        for (const key in summary.child_hours) {
            if (key.startsWith(`${childId}_`)) {
                childHours = summary.child_hours[key];
                break;
            }
        }
        
        // Build employee hours breakdown for this child
        const employeeBreakdown = [];
        for (const key in summary.employee_hours) {
            const [empId, empName] = key.split('_');
            const hours = summary.employee_hours[key];
            
            // We need to check if this employee worked with this child
            // Since we're filtering by child, all hours shown are for this child
            if (hours > 0) {
                employeeBreakdown.push({
                    name: empName || 'Unknown',
                    hours: hours
                });
            }
        }
        
        // Sort employees by name
        employeeBreakdown.sort((a, b) => a.name.localeCompare(b.name));
        
        const summaryDiv = document.getElementById('period-summary');
        summaryDiv.innerHTML = `
            <h3>Period Summary for ${childName}</h3>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="label">Total Hours</div>
                    <div class="value">${childHours || 0}</div>
                </div>
                ${employeeBreakdown.map(emp => `
                    <div class="summary-item">
                        <div class="label">${emp.name}</div>
                        <div class="value">${emp.hours} hrs</div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    showView(viewName) {
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        
        document.getElementById(`${viewName}-view`).classList.add('active');
        document.getElementById(`btn-${viewName}`).classList.add('active');
        
        this.currentView = viewName;
        
        if (viewName === 'dashboard') this.loadDashboard();
        else if (viewName === 'employees') this.loadEmployees();
        else if (viewName === 'children') this.loadChildren();
        else if (viewName === 'config') this.loadConfig();
    }

    async loadEmployees() {
        const employees = await this.api('/api/employees');
        const tbody = document.querySelector('#employees-table tbody');
        tbody.innerHTML = employees.map(emp => `
            <tr>
                <td>${emp.friendly_name}</td>
                <td>${emp.system_name}</td>
                <td>${emp.active ? 'Active' : 'Inactive'}</td>
                <td>
                    <button onclick="app.editEmployee(${emp.id})" class="btn-primary">Edit</button>
                    <button onclick="app.deleteEmployee(${emp.id})" class="btn-secondary">Delete</button>
                </td>
            </tr>
        `).join('');
    }

    async loadChildren() {
        const children = await this.api('/api/children');
        const tbody = document.querySelector('#children-table tbody');
        tbody.innerHTML = children.map(child => `
            <tr>
                <td>${child.name}</td>
                <td>${child.code}</td>
                <td>${child.active ? 'Active' : 'Inactive'}</td>
                <td>
                    <button onclick="app.editChild(${child.id})" class="btn-primary">Edit</button>
                    <button onclick="app.deleteChild(${child.id})" class="btn-secondary">Delete</button>
                </td>
            </tr>
        `).join('');
    }

    async loadConfig() {
        const [hourLimits, exclusions] = await Promise.all([
            this.api('/api/config/hour-limits'),
            this.api('/api/payroll/exclusions')
        ]);
        
        document.querySelector('#hour-limits-table tbody').innerHTML = hourLimits.map(limit => `
            <tr>
                <td>${limit.employee_name}</td>
                <td>${limit.child_name}</td>
                <td>${limit.max_hours_per_week}</td>
                <td>${limit.alert_threshold || 'N/A'}</td>
                <td>
                    <button onclick="app.editHourLimit(${limit.id})" class="btn-primary">Edit</button>
                    <button onclick="app.deleteHourLimit(${limit.id})" class="btn-secondary">Delete</button>
                </td>
            </tr>
        `).join('');
        
        document.querySelector('#exclusions-table tbody').innerHTML = exclusions.map(exc => `
            <tr>
                <td>${exc.name}</td>
                <td>${exc.start_date}</td>
                <td>${exc.end_date}</td>
                <td>${exc.reason || ''}</td>
                <td><button onclick="app.deleteExclusion(${exc.id})">Delete</button></td>
            </tr>
        `).join('');
    }

    navigatePeriod(direction) {
        const currentIndex = this.periods.findIndex(p => p.id === this.currentPeriod.id);
        const newIndex = currentIndex + direction;
        
        if (newIndex >= 0 && newIndex < this.periods.length) {
            this.currentPeriod = this.periods[newIndex];
            this.loadDashboard();
        }
    }

    async api(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'API request failed');
        }
        
        return response.json();
    }

    showToast(message, type = 'success') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = `toast show ${type}`;
        setTimeout(() => toast.classList.remove('show'), 3000);
    }

    showModal(content) {
        document.getElementById('modal-body').innerHTML = content;
        document.getElementById('modal').classList.add('show');
    }

    closeModal() {
        document.getElementById('modal').classList.remove('show');
    }

    formatDate(dateStr) {
        return new Date(dateStr + 'T00:00:00').toLocaleDateString();
    }

    formatTime(timeStr) {
        const [hours, minutes] = timeStr.split(':');
        const h = parseInt(hours);
        const ampm = h >= 12 ? 'PM' : 'AM';
        const h12 = h % 12 || 12;
        return `${h12}:${minutes}${ampm}`;
    }
    
    calculateShiftHours(startTimeStr, endTimeStr) {
        // Handle special case of 23:59:59 (end of day)
        if (endTimeStr === '23:59:59') {
            endTimeStr = '24:00:00';
        }
        
        const [startHours, startMinutes, startSeconds] = startTimeStr.split(':').map(Number);
        const [endHours, endMinutes, endSeconds] = endTimeStr.split(':').map(Number);
        
        const startTotalMinutes = startHours * 60 + startMinutes + startSeconds / 60;
        let endTotalMinutes = endHours * 60 + endMinutes + endSeconds / 60;
        
        // Handle case where end time appears before start time (shouldn't happen with our validation)
        if (endTotalMinutes < startTotalMinutes) {
            endTotalMinutes += 24 * 60; // Add 24 hours
        }
        
        const totalMinutes = endTotalMinutes - startTotalMinutes;
        const hours = Math.floor(totalMinutes / 60);
        const minutes = Math.round(totalMinutes % 60);
        
        if (minutes === 0) {
            return hours.toString();
        } else if (minutes === 30) {
            return `${hours}.5`;
        } else {
            return `${hours}:${minutes.toString().padStart(2, '0')}`;
        }
    }
}

const app = new App();