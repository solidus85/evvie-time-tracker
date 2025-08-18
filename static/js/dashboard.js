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
    
    // Fetch shifts for selected child, all shifts for overlap detection, and exclusions
    const [childShifts, allShifts, exclusions] = await Promise.all([
        this.api(`/api/shifts?start_date=${this.currentPeriod.start_date}&end_date=${this.currentPeriod.end_date}&child_id=${this.selectedChildId}`),
        this.api(`/api/shifts?start_date=${this.currentPeriod.start_date}&end_date=${this.currentPeriod.end_date}`),
        this.api(`/api/payroll/exclusions/for-period?start_date=${this.currentPeriod.start_date}&end_date=${this.currentPeriod.end_date}`)
    ]);
    
    // Store exclusions for use in calendar rendering and shift creation
    this.currentExclusions = exclusions;
    
    this.renderCalendar(this.currentPeriod, childShifts);
    this.renderExclusionsSummary(exclusions);
    
    // Calculate summary from filtered shifts
    this.renderChildSummaryFromShifts(childShifts, this.selectedChildId);
    
    // Detect and display overlapping shifts
    this.detectAndDisplayOverlaps(allShifts);
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
        
        // Always show add button
        const addBtn = document.createElement('button');
        addBtn.className = 'day-add-btn';
        addBtn.textContent = '+';
        addBtn.onclick = () => this.showShiftForm(dateStr);
        dayDiv.appendChild(addBtn);
        
        // Display exclusions for this date
        const dayExclusions = this.getExclusionsForDate(dateStr);
        dayExclusions.forEach(exclusion => {
            const exclusionDiv = document.createElement('div');
            exclusionDiv.className = 'exclusion-entry';
            
            let label = 'Exclusion';
            if (exclusion.employee_name) {
                label = exclusion.employee_name;
            } else if (exclusion.child_name) {
                label = exclusion.child_name;
            }
            
            // Show time range based on what times are available
            let timeRange = 'All day';
            if (exclusion.start_time && exclusion.end_time) {
                // Both times specified - show range
                timeRange = `${this.formatTime(exclusion.start_time)}-${this.formatTime(exclusion.end_time)}`;
            } else if (exclusion.start_time && !exclusion.end_time) {
                // Only start time - exclusion starts at this time and goes to end of day
                timeRange = `From ${this.formatTime(exclusion.start_time)}`;
            } else if (!exclusion.start_time && exclusion.end_time) {
                // Only end time - exclusion is from start of day until this time
                timeRange = `Until ${this.formatTime(exclusion.end_time)}`;
            }
            
            exclusionDiv.innerHTML = `
                <div class="exclusion-label">${label}</div>
                <div class="exclusion-name">${timeRange}</div>
            `;
            exclusionDiv.title = `Exclusion: ${exclusion.name}${exclusion.reason ? ' - ' + exclusion.reason : ''}`;
            dayDiv.appendChild(exclusionDiv);
        });
        
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

App.prototype.getExclusionsForDate = function(dateStr) {
    if (!this.currentExclusions || this.currentExclusions.length === 0) return [];
    
    // Filter and adjust exclusions that apply to this date
    return this.currentExclusions
        .filter(exclusion => {
            // Check if date falls within exclusion period
            if (dateStr >= exclusion.start_date && dateStr <= exclusion.end_date) {
                // If it's a child-specific exclusion, only show if it matches the selected child
                if (exclusion.child_id) {
                    return exclusion.child_id === this.selectedChildId;
                }
                // Show employee-specific and general exclusions
                return true;
            }
            return false;
        })
        .map(exclusion => {
            // Create a copy to avoid modifying the original
            const adjustedExclusion = {...exclusion};
            
            // Determine if this is the first day, last day, or a middle day
            const isFirstDay = dateStr === exclusion.start_date;
            const isLastDay = dateStr === exclusion.end_date;
            
            if (isFirstDay && isLastDay) {
                // Single day exclusion - keep original times
                // Already has correct start_time and end_time
            } else if (isFirstDay) {
                // First day - use start_time, but end at midnight (shown as "All day" if no end_time)
                adjustedExclusion.end_time = null;
            } else if (isLastDay) {
                // Last day - start at midnight (shown as "All day" if no start_time), use end_time
                adjustedExclusion.start_time = null;
            } else {
                // Middle day - full day exclusion
                adjustedExclusion.start_time = null;
                adjustedExclusion.end_time = null;
            }
            
            return adjustedExclusion;
        });
};

App.prototype.renderExclusionsSummary = function(exclusions) {
    // Remove the exclusions summary section as exclusions are now shown in the calendar
    // This function can be left empty or removed entirely
};

App.prototype.detectAndDisplayOverlaps = function(allShifts) {
    const overlaps = [];
    
    // Group shifts by employee and by child
    const shiftsByEmployee = {};
    const shiftsByChild = {};
    
    allShifts.forEach(shift => {
        // Group by employee
        if (!shiftsByEmployee[shift.employee_id]) {
            shiftsByEmployee[shift.employee_id] = [];
        }
        shiftsByEmployee[shift.employee_id].push(shift);
        
        // Group by child
        if (!shiftsByChild[shift.child_id]) {
            shiftsByChild[shift.child_id] = [];
        }
        shiftsByChild[shift.child_id].push(shift);
    });
    
    // Check for employee overlaps (same employee, different children, overlapping times)
    Object.entries(shiftsByEmployee).forEach(([employeeId, shifts]) => {
        for (let i = 0; i < shifts.length - 1; i++) {
            for (let j = i + 1; j < shifts.length; j++) {
                const shift1 = shifts[i];
                const shift2 = shifts[j];
                
                // Skip if same child
                if (shift1.child_id === shift2.child_id) continue;
                
                // Check if dates and times overlap
                if (shift1.date === shift2.date) {
                    const overlap = this.calculateTimeOverlap(shift1, shift2);
                    if (overlap) {
                        overlaps.push({
                            type: 'employee',
                            employee_name: shift1.employee_name,
                            shift1: shift1,
                            shift2: shift2,
                            overlap_duration: overlap
                        });
                    }
                }
            }
        }
    });
    
    // Check for child overlaps (same child, different employees, overlapping times)
    Object.entries(shiftsByChild).forEach(([childId, shifts]) => {
        for (let i = 0; i < shifts.length - 1; i++) {
            for (let j = i + 1; j < shifts.length; j++) {
                const shift1 = shifts[i];
                const shift2 = shifts[j];
                
                // Skip if same employee
                if (shift1.employee_id === shift2.employee_id) continue;
                
                // Check if dates and times overlap
                if (shift1.date === shift2.date) {
                    const overlap = this.calculateTimeOverlap(shift1, shift2);
                    if (overlap) {
                        overlaps.push({
                            type: 'child',
                            child_name: shift1.child_name,
                            shift1: shift1,
                            shift2: shift2,
                            overlap_duration: overlap
                        });
                    }
                }
            }
        }
    });
    
    // Display the overlaps
    this.renderOverlaps(overlaps);
};

App.prototype.calculateTimeOverlap = function(shift1, shift2) {
    // Convert times to minutes for easier calculation
    const start1 = this.timeToMinutes(shift1.start_time);
    const end1 = this.timeToMinutes(shift1.end_time);
    const start2 = this.timeToMinutes(shift2.start_time);
    const end2 = this.timeToMinutes(shift2.end_time);
    
    // Calculate overlap
    const overlapStart = Math.max(start1, start2);
    const overlapEnd = Math.min(end1, end2);
    
    if (overlapStart < overlapEnd) {
        const overlapMinutes = overlapEnd - overlapStart;
        return this.minutesToDuration(overlapMinutes);
    }
    
    return null;
};

App.prototype.timeToMinutes = function(timeStr) {
    const [hours, minutes] = timeStr.split(':').map(Number);
    return hours * 60 + minutes;
};

App.prototype.minutesToDuration = function(minutes) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}:${mins.toString().padStart(2, '0')}`;
};

App.prototype.renderOverlaps = function(overlaps) {
    const container = document.getElementById('overlap-detection');
    
    if (overlaps.length === 0) {
        container.innerHTML = '';
        return;
    }
    
    // Sort overlaps by date and then by type
    overlaps.sort((a, b) => {
        if (a.shift1.date !== b.shift1.date) {
            return a.shift1.date.localeCompare(b.shift1.date);
        }
        return a.type.localeCompare(b.type);
    });
    
    container.innerHTML = `
        <div class="overlap-header">
            <h3>⚠️ Overlapping Shifts Detected</h3>
            <p class="overlap-description">The following shifts have time conflicts that need attention:</p>
        </div>
        <div class="overlap-list">
            ${overlaps.map(overlap => {
                if (overlap.type === 'employee') {
                    return `
                        <div class="overlap-item employee-overlap">
                            <div class="overlap-type">Employee Conflict</div>
                            <div class="overlap-details">
                                <strong>${overlap.employee_name}</strong> is scheduled for multiple children on ${this.formatDate(overlap.shift1.date)}:
                                <div class="shift-comparison">
                                    <div class="shift-detail">
                                        • ${overlap.shift1.child_name}: ${this.formatTime(overlap.shift1.start_time)} - ${this.formatTime(overlap.shift1.end_time)}
                                    </div>
                                    <div class="shift-detail">
                                        • ${overlap.shift2.child_name}: ${this.formatTime(overlap.shift2.start_time)} - ${this.formatTime(overlap.shift2.end_time)}
                                    </div>
                                </div>
                                <div class="overlap-duration">
                                    <strong>Overlap duration:</strong> ${overlap.overlap_duration}
                                </div>
                            </div>
                        </div>
                    `;
                } else {
                    return `
                        <div class="overlap-item child-overlap">
                            <div class="overlap-type">Child Conflict</div>
                            <div class="overlap-details">
                                <strong>${overlap.child_name}</strong> has multiple employees scheduled on ${this.formatDate(overlap.shift1.date)}:
                                <div class="shift-comparison">
                                    <div class="shift-detail">
                                        • ${overlap.shift1.employee_name}: ${this.formatTime(overlap.shift1.start_time)} - ${this.formatTime(overlap.shift1.end_time)}
                                    </div>
                                    <div class="shift-detail">
                                        • ${overlap.shift2.employee_name}: ${this.formatTime(overlap.shift2.start_time)} - ${this.formatTime(overlap.shift2.end_time)}
                                    </div>
                                </div>
                                <div class="overlap-duration">
                                    <strong>Overlap duration:</strong> ${overlap.overlap_duration}
                                </div>
                            </div>
                        </div>
                    `;
                }
            }).join('')}
        </div>
    `;
};