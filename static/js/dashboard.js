/* Dashboard and calendar functionality */

App.prototype.loadCurrentPeriod = async function() {
    try {
        const period = await this.api('/api/payroll/periods/current');
        this.currentPeriod = period;
        await this.loadDashboard();
    } catch (error) {
        document.getElementById('period-label').textContent = 'No periods configured';
        document.getElementById('calendar-grid').innerHTML = '<p>Please configure payroll periods in Settings</p>';
    }
};

App.prototype.loadDashboard = async function() {
    if (!this.currentPeriod || !this.selectedChildId) return;
    
    document.getElementById('period-label').textContent = 
        `${this.formatDate(this.currentPeriod.start_date)} - ${this.formatDate(this.currentPeriod.end_date)}`;
    
    const shifts = await this.api(`/api/shifts?start_date=${this.currentPeriod.start_date}&end_date=${this.currentPeriod.end_date}&child_id=${this.selectedChildId}`);
    this.renderCalendar(this.currentPeriod, shifts);
    
    // Calculate summary from filtered shifts
    this.renderChildSummaryFromShifts(shifts, this.selectedChildId);
};

App.prototype.populateChildDropdown = function() {
    const dropdown = document.getElementById('child-filter');
    if (!dropdown) return;
    
    dropdown.innerHTML = this.children
        .filter(c => c.active)
        .map(child => `<option value="${child.id}" ${child.id === this.selectedChildId ? 'selected' : ''}>${child.name}</option>`)
        .join('');
};

App.prototype.renderCalendar = function(period, shifts) {
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
};

App.prototype.renderSummary = function(summary) {
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
};

App.prototype.renderChildSummaryFromShifts = function(shifts, childId) {
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
};

App.prototype.parseHours = function(hoursStr) {
    // Convert hour string (e.g., "8", "8.5", "8:45") to decimal
    if (hoursStr.includes(':')) {
        const [hours, minutes] = hoursStr.split(':').map(Number);
        return hours + minutes / 60;
    }
    return parseFloat(hoursStr);
};