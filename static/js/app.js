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
        
        // Filter summary to only show selected child's data
        const summary = await this.api(`/api/payroll/periods/${this.currentPeriod.id}/summary`);
        this.renderChildSummary(summary, this.selectedChildId);
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
            const dayShifts = shifts.filter(s => s.date === dateStr);
            
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
                
                const startTime = this.formatTime(shift.start_time);
                const endTime = this.formatTime(shift.end_time);
                shiftDiv.textContent = `${startTime}-${endTime} ${shift.employee_name}/${shift.child_name}`;
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
    
    renderChildSummary(summary, childId) {
        const selectedChild = this.children.find(c => c.id === childId);
        const childName = selectedChild ? selectedChild.name : 'Unknown';
        
        // Count shifts for selected child from the full summary
        let childShifts = 0;
        let childHours = 0;
        
        // Find child hours in the summary
        for (const key in summary.child_hours) {
            if (key.startsWith(`${childId}_`)) {
                childHours = summary.child_hours[key];
                break;
            }
        }
        
        const summaryDiv = document.getElementById('period-summary');
        summaryDiv.innerHTML = `
            <h3>Period Summary for ${childName}</h3>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="label">Total Hours</div>
                    <div class="value">${childHours || 0}</div>
                </div>
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
                    <button onclick="app.editEmployee(${emp.id})">Edit</button>
                    <button onclick="app.deleteEmployee(${emp.id})">Delete</button>
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
                    <button onclick="app.editChild(${child.id})">Edit</button>
                    <button onclick="app.deleteChild(${child.id})">Delete</button>
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
                <td>${limit.max_hours_per_period}</td>
                <td>${limit.alert_threshold || 'N/A'}</td>
                <td><button onclick="app.deleteHourLimit(${limit.id})">Delete</button></td>
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
}

const app = new App();