App.prototype.showHourLimitForm = async function() {
    await this.loadInitialData();
    const content = `
        <h2>Add Hour Limit</h2>
        <form id="hour-limit-form">
            <div class="form-group">
                <label>Employee</label>
                <select name="employee_id" required>
                    <option value="">Select Employee</option>
                    ${this.employees.filter(e => e.active).map(e => 
                        `<option value="${e.id}">${e.friendly_name}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group">
                <label>Child</label>
                <select name="child_id" required>
                    <option value="">Select Child</option>
                    ${this.children.filter(c => c.active).map(c => 
                        `<option value="${c.id}">${c.name}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group">
                <label>Max Hours per Week</label>
                <input type="number" name="max_hours_per_week" step="0.5" required>
            </div>
            <div class="form-group">
                <label>Alert Threshold (optional)</label>
                <input type="number" name="alert_threshold" step="0.5">
            </div>
            <button type="submit" class="btn-primary">Save</button>
        </form>
    `;
    this.showModal(content);
    
    document.getElementById('hour-limit-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = {
            employee_id: parseInt(formData.get('employee_id')),
            child_id: parseInt(formData.get('child_id')),
            max_hours_per_week: parseFloat(formData.get('max_hours_per_week')),
            alert_threshold: formData.get('alert_threshold') ? parseFloat(formData.get('alert_threshold')) : null
        };
        
        try {
            await this.api('/api/config/hour-limits', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            this.showToast('Hour limit created successfully');
            this.closeModal();
            this.loadConfig();
        } catch (error) {
            this.showToast(error.message, 'error');
        }
    });
};

App.prototype.showExclusionForm = function() {
    const content = `
        <h2>Add Exclusion Period</h2>
        <form id="exclusion-form">
            <div class="form-group">
                <label>Name</label>
                <input type="text" name="name" required>
            </div>
            <div class="form-group">
                <label>Start Date</label>
                <input type="date" name="start_date" required>
            </div>
            <div class="form-group">
                <label>End Date</label>
                <input type="date" name="end_date" required>
            </div>
            <div class="form-group">
                <label>Reason (optional)</label>
                <textarea name="reason"></textarea>
            </div>
            <button type="submit" class="btn-primary">Save</button>
        </form>
    `;
    this.showModal(content);
    
    document.getElementById('exclusion-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = {
            name: formData.get('name'),
            start_date: formData.get('start_date'),
            end_date: formData.get('end_date'),
            reason: formData.get('reason') || null
        };
        
        try {
            await this.api('/api/payroll/exclusions', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            this.showToast('Exclusion period created successfully');
            this.closeModal();
            this.loadConfig();
        } catch (error) {
            this.showToast(error.message, 'error');
        }
    });
};

App.prototype.configurePeriods = async function() {
    const anchorDate = document.getElementById('anchor-date').value;
    if (!anchorDate) {
        this.showToast('Please select an anchor date', 'error');
        return;
    }
    
    if (!confirm('This will reconfigure all payroll periods. Continue?')) {
        return;
    }
    
    try {
        await this.api('/api/payroll/periods/configure', {
            method: 'POST',
            body: JSON.stringify({ anchor_date: anchorDate })
        });
        this.showToast('Payroll periods configured successfully');
        await this.loadInitialData();
        if (this.currentView === 'dashboard') {
            await this.loadCurrentPeriod();
        }
    } catch (error) {
        this.showToast(error.message, 'error');
    }
};

App.prototype.deleteEmployee = async function(id) {
    if (!confirm('Are you sure you want to deactivate this employee?')) return;
    
    try {
        await this.api(`/api/employees/${id}`, { method: 'DELETE' });
        this.showToast('Employee deactivated');
        this.loadEmployees();
    } catch (error) {
        this.showToast(error.message, 'error');
    }
};

App.prototype.deleteChild = async function(id) {
    if (!confirm('Are you sure you want to deactivate this child?')) return;
    
    try {
        await this.api(`/api/children/${id}`, { method: 'DELETE' });
        this.showToast('Child deactivated');
        this.loadChildren();
    } catch (error) {
        this.showToast(error.message, 'error');
    }
};

App.prototype.deleteShift = async function(id) {
    if (!confirm('Are you sure you want to delete this shift?')) return;
    
    try {
        await this.api(`/api/shifts/${id}`, { method: 'DELETE' });
        this.showToast('Shift deleted');
        this.closeModal();
        this.loadDashboard();
    } catch (error) {
        this.showToast(error.message, 'error');
    }
};

App.prototype.deleteHourLimit = async function(id) {
    if (!confirm('Are you sure you want to remove this hour limit?')) return;
    
    try {
        await this.api(`/api/config/hour-limits/${id}`, { method: 'DELETE' });
        this.showToast('Hour limit removed');
        this.loadConfig();
    } catch (error) {
        this.showToast(error.message, 'error');
    }
};

App.prototype.deleteExclusion = async function(id) {
    if (!confirm('Are you sure you want to remove this exclusion period?')) return;
    
    try {
        await this.api(`/api/payroll/exclusions/${id}`, { method: 'DELETE' });
        this.showToast('Exclusion period removed');
        this.loadConfig();
    } catch (error) {
        this.showToast(error.message, 'error');
    }
};

App.prototype.editEmployee = async function(id) {
    const employee = this.employees.find(e => e.id === id);
    if (employee) this.showEmployeeForm(employee);
};

App.prototype.editChild = async function(id) {
    const child = this.children.find(c => c.id === id);
    if (child) this.showChildForm(child);
};

App.prototype.editShift = async function(id) {
    try {
        const shift = await this.api(`/api/shifts/${id}`);
        const content = `
            <h2>Edit Shift</h2>
            <form id="edit-shift-form">
                <div class="form-group">
                    <label>Date</label>
                    <input type="date" name="date" value="${shift.date}" required>
                </div>
                <div class="form-group">
                    <label>Start Time</label>
                    <input type="time" name="start_time" value="${shift.start_time.substring(0, 5)}" required>
                </div>
                <div class="form-group">
                    <label>End Time</label>
                    <input type="time" name="end_time" value="${shift.end_time.substring(0, 5)}" required>
                </div>
                <div class="form-group">
                    <label>Service Code</label>
                    <input type="text" name="service_code" value="${shift.service_code || ''}">
                </div>
                <div class="form-group">
                    <label>Status</label>
                    <input type="text" name="status" value="${shift.status || ''}">
                </div>
                <button type="submit" class="btn-primary">Update Shift</button>
            </form>
        `;
        this.showModal(content);
        
        document.getElementById('edit-shift-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = {
                date: formData.get('date'),
                start_time: formData.get('start_time') + ':00',
                end_time: formData.get('end_time') + ':00',
                service_code: formData.get('service_code'),
                status: formData.get('status')
            };
            
            try {
                const result = await this.api(`/api/shifts/${id}`, {
                    method: 'PUT',
                    body: JSON.stringify(data)
                });
                
                if (result.warnings && result.warnings.length > 0) {
                    this.showToast(result.warnings.join(', '), 'warning');
                } else {
                    this.showToast('Shift updated successfully');
                }
                this.closeModal();
                this.loadDashboard();
            } catch (error) {
                this.showToast(error.message, 'error');
            }
        });
    } catch (error) {
        this.showToast(error.message, 'error');
    }
};