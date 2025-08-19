/* Exclusion periods management */

// Initialize pagination state
App.prototype.initExclusionsPagination = function() {
    if (!this.exclusionsPagination) {
        this.exclusionsPagination = {
            currentPage: 1,
            itemsPerPage: 10,
            totalItems: 0,
            allExclusions: []
        };
    }
};

App.prototype.loadExclusions = async function() {
    this.initExclusionsPagination();
    const exclusions = await this.api('/api/payroll/exclusions');
    
    // Get current payroll period for filtering
    let currentPeriodEnd = null;
    try {
        const currentPeriod = await this.api('/api/payroll/periods/current');
        if (currentPeriod && currentPeriod.end_date) {
            currentPeriodEnd = currentPeriod.end_date;
        }
    } catch (error) {
        console.error('Could not fetch current period:', error);
    }
    
    // Store all exclusions and apply filter if checkbox is checked
    this.exclusionsPagination.allExclusionsUnfiltered = exclusions;
    this.exclusionsPagination.currentPeriodEnd = currentPeriodEnd;
    this.applyExclusionsFilter();
    
    // Setup checkbox listener if not already done
    const checkbox = document.getElementById('filter-future-exclusions');
    if (checkbox && !checkbox.hasListener) {
        checkbox.hasListener = true;
        checkbox.addEventListener('change', () => {
            this.applyExclusionsFilter();
        });
    }
    
    this.renderExclusionsTable();
};

App.prototype.applyExclusionsFilter = function() {
    const checkbox = document.getElementById('filter-future-exclusions');
    const { allExclusionsUnfiltered, currentPeriodEnd } = this.exclusionsPagination;
    
    let filteredExclusions = allExclusionsUnfiltered;
    
    if (checkbox && checkbox.checked && currentPeriodEnd) {
        // Filter out exclusions that start after the current period end
        filteredExclusions = allExclusionsUnfiltered.filter(exc => {
            return exc.start_date <= currentPeriodEnd;
        });
    }
    
    this.exclusionsPagination.allExclusions = filteredExclusions;
    this.exclusionsPagination.totalItems = filteredExclusions.length;
    
    // Reset to page 1 if current page is out of bounds
    const totalPages = Math.ceil(filteredExclusions.length / this.exclusionsPagination.itemsPerPage);
    if (this.exclusionsPagination.currentPage > totalPages) {
        this.exclusionsPagination.currentPage = 1;
    }
};

App.prototype.renderExclusionsTable = function() {
    const { currentPage, itemsPerPage, allExclusions, totalItems } = this.exclusionsPagination;
    
    // Calculate pagination bounds
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, totalItems);
    const paginatedExclusions = allExclusions.slice(startIndex, endIndex);
    const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;
    
    // Render table rows
    document.querySelector('#exclusions-table tbody').innerHTML = paginatedExclusions.map(exc => {
        const startDateTime = exc.start_time ? `${exc.start_date} ${this.formatTime(exc.start_time)}` : exc.start_date;
        const endDateTime = exc.end_time ? `${exc.end_date} ${this.formatTime(exc.end_time)}` : exc.end_date;
        
        let targetInfo = 'General';
        if (exc.employee_name) {
            targetInfo = `Employee: ${exc.employee_name}`;
        } else if (exc.child_name) {
            targetInfo = `Child: ${exc.child_name}`;
        }
        
        return `
        <tr>
            <td>${exc.name}</td>
            <td>${targetInfo}</td>
            <td>${startDateTime}</td>
            <td>${endDateTime}</td>
            <td>${exc.reason || 'N/A'}</td>
            <td>
                <button onclick="app.editExclusion(${exc.id})" class="btn-primary">Edit</button>
                <button onclick="app.deleteExclusion(${exc.id})" class="btn-secondary">Delete</button>
            </td>
        </tr>
    `}).join('');
    
    // Render pagination controls
    this.renderExclusionsPagination(totalPages, startIndex, endIndex);
};

App.prototype.renderExclusionsPagination = function(totalPages, startIndex, endIndex) {
    const { currentPage, itemsPerPage, totalItems } = this.exclusionsPagination;
    
    let paginationHTML = `
        <div class="pagination-container">
            <div class="pagination-info">
                Showing ${totalItems > 0 ? startIndex + 1 : 0}-${endIndex} of ${totalItems} exclusions
            </div>
            <div class="pagination-controls">
                <select class="page-size-selector" onchange="app.changeExclusionsPageSize(this.value)">
                    <option value="10" ${itemsPerPage === 10 ? 'selected' : ''}>10 per page</option>
                    <option value="25" ${itemsPerPage === 25 ? 'selected' : ''}>25 per page</option>
                    <option value="50" ${itemsPerPage === 50 ? 'selected' : ''}>50 per page</option>
                    <option value="${totalItems}" ${itemsPerPage === totalItems ? 'selected' : ''}>All</option>
                </select>
                <button class="pagination-btn" onclick="app.goToExclusionsPage(1)" ${currentPage === 1 ? 'disabled' : ''}>
                    ⟨⟨
                </button>
                <button class="pagination-btn" onclick="app.goToExclusionsPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
                    ⟨
                </button>
    `;
    
    // Add page numbers
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        paginationHTML += `
            <button class="pagination-btn ${i === currentPage ? 'active' : ''}" 
                    onclick="app.goToExclusionsPage(${i})">
                ${i}
            </button>
        `;
    }
    
    paginationHTML += `
                <button class="pagination-btn" onclick="app.goToExclusionsPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
                    ⟩
                </button>
                <button class="pagination-btn" onclick="app.goToExclusionsPage(${totalPages})" ${currentPage === totalPages ? 'disabled' : ''}>
                    ⟩⟩
                </button>
            </div>
        </div>
    `;
    
    // Check if pagination container exists, if not create it
    let paginationContainer = document.getElementById('exclusions-pagination');
    if (!paginationContainer) {
        paginationContainer = document.createElement('div');
        paginationContainer.id = 'exclusions-pagination';
        document.querySelector('.exclusions-table-wrapper').appendChild(paginationContainer);
    }
    
    paginationContainer.innerHTML = paginationHTML;
};

App.prototype.goToExclusionsPage = function(page) {
    this.exclusionsPagination.currentPage = page;
    this.renderExclusionsTable();
};

App.prototype.changeExclusionsPageSize = function(size) {
    this.exclusionsPagination.itemsPerPage = parseInt(size);
    this.exclusionsPagination.currentPage = 1; // Reset to first page
    this.renderExclusionsTable();
};

App.prototype.showExclusionForm = async function(exclusion = null) {
    await this.loadInitialData();
    
    const exclusionType = exclusion?.employee_id ? 'employee' : (exclusion?.child_id ? 'child' : 'general');
    
    const content = `
        <h2>${exclusion ? 'Edit' : 'Add'} Exclusion Period</h2>
        <form id="exclusion-form">
            <div class="form-group">
                <label>Name</label>
                <input type="text" name="name" value="${exclusion?.name || ''}" required>
            </div>
            <div class="form-group">
                <label>Exclusion Type</label>
                <select name="exclusion_type" id="exclusion-type" required>
                    <option value="general" ${exclusionType === 'general' ? 'selected' : ''}>General (All)</option>
                    <option value="employee" ${exclusionType === 'employee' ? 'selected' : ''}>Specific Employee</option>
                    <option value="child" ${exclusionType === 'child' ? 'selected' : ''}>Specific Child</option>
                </select>
            </div>
            <div class="form-group" id="employee-select" style="display: ${exclusionType === 'employee' ? 'block' : 'none'}">
                <label>Employee</label>
                <select name="employee_id">
                    <option value="">Select Employee</option>
                    ${this.employees.filter(e => e.active && !e.hidden).map(e => 
                        `<option value="${e.id}" ${exclusion?.employee_id === e.id ? 'selected' : ''}>${e.friendly_name}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group" id="child-select" style="display: ${exclusionType === 'child' ? 'block' : 'none'}">
                <label>Child</label>
                <select name="child_id">
                    <option value="">Select Child</option>
                    ${this.children.filter(c => c.active).map(c => 
                        `<option value="${c.id}" ${exclusion?.child_id === c.id ? 'selected' : ''}>${c.name}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group">
                <label>Start Date</label>
                <input type="date" name="start_date" value="${exclusion?.start_date || ''}" required>
            </div>
            <div class="form-group">
                <label>Start Time (optional)</label>
                <input type="time" name="start_time" value="${exclusion?.start_time ? exclusion.start_time.substring(0, 5) : ''}">
            </div>
            <div class="form-group">
                <label>End Date</label>
                <input type="date" name="end_date" value="${exclusion?.end_date || ''}" required>
            </div>
            <div class="form-group">
                <label>End Time (optional)</label>
                <input type="time" name="end_time" value="${exclusion?.end_time ? exclusion.end_time.substring(0, 5) : ''}">
            </div>
            <div class="form-group">
                <label>Reason (optional)</label>
                <input type="text" name="reason" value="${exclusion?.reason || ''}">
            </div>
            <button type="submit" class="btn-primary">Save</button>
        </form>
    `;
    this.showModal(content);
    
    // Add event listener for exclusion type change
    document.getElementById('exclusion-type').addEventListener('change', (e) => {
        const type = e.target.value;
        document.getElementById('employee-select').style.display = type === 'employee' ? 'block' : 'none';
        document.getElementById('child-select').style.display = type === 'child' ? 'block' : 'none';
    });
    
    document.getElementById('exclusion-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const exclusionType = formData.get('exclusion_type');
        
        const data = {
            name: formData.get('name'),
            start_date: formData.get('start_date'),
            end_date: formData.get('end_date'),
            start_time: formData.get('start_time') ? formData.get('start_time') + ':00' : null,
            end_time: formData.get('end_time') ? formData.get('end_time') + ':00' : null,
            reason: formData.get('reason') || null
        };
        
        // Add employee_id or child_id based on type
        if (exclusionType === 'employee') {
            data.employee_id = formData.get('employee_id') || null;
        } else if (exclusionType === 'child') {
            data.child_id = formData.get('child_id') || null;
        }
        
        try {
            if (exclusion) {
                await this.api(`/api/payroll/exclusions/${exclusion.id}`, {
                    method: 'PUT',
                    body: JSON.stringify(data)
                });
                this.showToast('Exclusion period updated successfully');
            } else {
                await this.api('/api/payroll/exclusions', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
                this.showToast('Exclusion period created successfully');
            }
            this.closeModal();
            this.loadExclusions();
        } catch (error) {
            this.showToast(error.message, 'error');
        }
    });
};

App.prototype.editExclusion = async function(id) {
    try {
        const exclusions = await this.api('/api/payroll/exclusions');
        const exclusion = exclusions.find(e => e.id === id);
        
        if (!exclusion) {
            this.showToast('Exclusion period not found', 'error');
            return;
        }
        
        this.showExclusionForm(exclusion);
    } catch (error) {
        this.showToast(error.message, 'error');
    }
};

App.prototype.deleteExclusion = async function(id) {
    if (!confirm('Are you sure you want to remove this exclusion period?')) return;
    
    try {
        await this.api(`/api/payroll/exclusions/${id}`, { method: 'DELETE' });
        this.showToast('Exclusion period removed');
        this.loadExclusions();
    } catch (error) {
        this.showToast(error.message, 'error');
    }
};

App.prototype.showBulkExclusionForm = async function() {
    await this.loadInitialData();
    
    const content = `
        <h2>Bulk Add Exclusions</h2>
        <p style="color: #666; margin-bottom: 15px;">Create multiple exclusion periods based on a recurring pattern (e.g., school hours M-F)</p>
        <form id="bulk-exclusion-form">
            <div class="form-group">
                <label>Name Pattern</label>
                <input type="text" name="name_pattern" placeholder="e.g., School Hours" required>
                <small style="color: #666;">Will be appended with date (e.g., "School Hours - Mon 1/15")</small>
            </div>
            
            <div class="form-group">
                <label>Exclusion Type</label>
                <select name="exclusion_type" id="bulk-exclusion-type" required>
                    <option value="general">General (All)</option>
                    <option value="employee">Specific Employee</option>
                    <option value="child">Specific Child</option>
                </select>
            </div>
            
            <div class="form-group" id="bulk-employee-select" style="display: none">
                <label>Employee</label>
                <select name="employee_id">
                    <option value="">Select Employee</option>
                    ${this.employees.filter(e => e.active && !e.hidden).map(e => 
                        `<option value="${e.id}">${e.friendly_name}</option>`
                    ).join('')}
                </select>
            </div>
            
            <div class="form-group" id="bulk-child-select" style="display: none">
                <label>Child</label>
                <select name="child_id">
                    <option value="">Select Child</option>
                    ${this.children.filter(c => c.active).map(c => 
                        `<option value="${c.id}">${c.name}</option>`
                    ).join('')}
                </select>
            </div>
            
            <div class="form-group">
                <label>Date Range (optional)</label>
                <div style="display: flex; gap: 10px;">
                    <input type="date" name="start_date" style="flex: 1">
                    <span style="padding: 8px;">to</span>
                    <input type="date" name="end_date" style="flex: 1">
                </div>
                <small style="color: #666;">Leave blank to apply to all future payroll periods</small>
            </div>
            
            <div class="form-group">
                <label>Days of Week</label>
                <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                    <label style="display: flex; align-items: center;">
                        <input type="checkbox" name="days_of_week" value="1" style="margin-right: 5px;"> Mon
                    </label>
                    <label style="display: flex; align-items: center;">
                        <input type="checkbox" name="days_of_week" value="2" style="margin-right: 5px;"> Tue
                    </label>
                    <label style="display: flex; align-items: center;">
                        <input type="checkbox" name="days_of_week" value="3" style="margin-right: 5px;"> Wed
                    </label>
                    <label style="display: flex; align-items: center;">
                        <input type="checkbox" name="days_of_week" value="4" style="margin-right: 5px;"> Thu
                    </label>
                    <label style="display: flex; align-items: center;">
                        <input type="checkbox" name="days_of_week" value="5" style="margin-right: 5px;"> Fri
                    </label>
                    <label style="display: flex; align-items: center;">
                        <input type="checkbox" name="days_of_week" value="6" style="margin-right: 5px;"> Sat
                    </label>
                    <label style="display: flex; align-items: center;">
                        <input type="checkbox" name="days_of_week" value="0" style="margin-right: 5px;"> Sun
                    </label>
                </div>
            </div>
            
            <div class="form-group">
                <label>Week Selection</label>
                <select name="weeks" required>
                    <option value="both">Both weeks</option>
                    <option value="week1">Week 1 only</option>
                    <option value="week2">Week 2 only</option>
                </select>
                <small style="color: #666;">Payroll periods have 2 weeks (Thu-Wed)</small>
            </div>
            
            <div class="form-group">
                <label>Time Range (optional)</label>
                <div style="display: flex; gap: 10px;">
                    <input type="time" name="start_time" style="flex: 1">
                    <span style="padding: 8px;">to</span>
                    <input type="time" name="end_time" style="flex: 1">
                </div>
                <small style="color: #666;">Leave blank for all day</small>
            </div>
            
            <div class="form-group">
                <label>Reason (optional)</label>
                <input type="text" name="reason" placeholder="e.g., Regular school hours">
            </div>
            
            <div id="bulk-preview" style="display: none; margin-top: 20px;">
                <h4 style="margin-bottom: 10px;">Preview of dates to be excluded:</h4>
                <div id="preview-dates" style="max-height: 200px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 4px; background: #f9f9f9;"></div>
            </div>
            
            <div style="display: flex; gap: 10px; margin-top: 20px;">
                <button type="button" id="preview-bulk" class="btn-secondary">Preview Dates</button>
                <button type="submit" class="btn-primary">Create Exclusions</button>
            </div>
        </form>
    `;
    
    this.showModal(content);
    
    // Add event listener for exclusion type change
    document.getElementById('bulk-exclusion-type').addEventListener('change', (e) => {
        const type = e.target.value;
        document.getElementById('bulk-employee-select').style.display = type === 'employee' ? 'block' : 'none';
        document.getElementById('bulk-child-select').style.display = type === 'child' ? 'block' : 'none';
    });
    
    // Add preview button handler
    document.getElementById('preview-bulk').addEventListener('click', () => {
        this.previewBulkExclusions();
    });
    
    // Add form submission handler
    document.getElementById('bulk-exclusion-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await this.submitBulkExclusions(e.target);
    });
};

App.prototype.previewBulkExclusions = async function() {
    const form = document.getElementById('bulk-exclusion-form');
    const formData = new FormData(form);
    
    // Get selected days of week
    const daysOfWeek = [];
    form.querySelectorAll('input[name="days_of_week"]:checked').forEach(cb => {
        daysOfWeek.push(parseInt(cb.value));
    });
    
    if (daysOfWeek.length === 0) {
        this.showToast('Please select at least one day of the week', 'error');
        return;
    }
    
    const data = {
        start_date: formData.get('start_date') || null,
        end_date: formData.get('end_date') || null,
        days_of_week: daysOfWeek,
        weeks: formData.get('weeks')
    };
    
    try {
        const dates = await this.api('/api/payroll/exclusions/preview', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        const previewDiv = document.getElementById('preview-dates');
        if (dates.length === 0) {
            previewDiv.innerHTML = '<p>No matching dates found in the selected range.</p>';
        } else {
            const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
            previewDiv.innerHTML = `
                <p><strong>${dates.length} dates will be excluded:</strong></p>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    ${dates.map(d => {
                        const date = new Date(d.date + 'T00:00:00');
                        const dayName = dayNames[date.getDay()];
                        return `<li>${dayName} ${this.formatDate(d.date)} (Week ${d.week})</li>`;
                    }).join('')}
                </ul>
            `;
        }
        
        document.getElementById('bulk-preview').style.display = 'block';
    } catch (error) {
        this.showToast(error.message, 'error');
    }
};

App.prototype.submitBulkExclusions = async function(form) {
    const formData = new FormData(form);
    
    // Get selected days of week
    const daysOfWeek = [];
    form.querySelectorAll('input[name="days_of_week"]:checked').forEach(cb => {
        daysOfWeek.push(parseInt(cb.value));
    });
    
    if (daysOfWeek.length === 0) {
        this.showToast('Please select at least one day of the week', 'error');
        return;
    }
    
    const exclusionType = formData.get('exclusion_type');
    const data = {
        name_pattern: formData.get('name_pattern'),
        start_date: formData.get('start_date') || null,
        end_date: formData.get('end_date') || null,
        days_of_week: daysOfWeek,
        weeks: formData.get('weeks'),
        start_time: formData.get('start_time') ? formData.get('start_time') + ':00' : null,
        end_time: formData.get('end_time') ? formData.get('end_time') + ':00' : null,
        reason: formData.get('reason') || null
    };
    
    // Add employee_id or child_id based on type
    if (exclusionType === 'employee') {
        data.employee_id = formData.get('employee_id') || null;
    } else if (exclusionType === 'child') {
        data.child_id = formData.get('child_id') || null;
    }
    
    try {
        const result = await this.api('/api/payroll/exclusions/bulk', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        this.showToast(`Successfully created ${result.count} exclusion periods`);
        this.closeModal();
        this.loadExclusions();
    } catch (error) {
        this.showToast(error.message, 'error');
    }
};