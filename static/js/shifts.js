/* Shift management functions */

App.prototype.showShiftForm = async function(date) {
    await this.loadInitialData();
    
    const content = `
        <h2>Add Shift</h2>
        <form id="shift-form">
            <div class="form-group">
                <label>Date</label>
                <input type="date" name="date" value="${date}" required>
            </div>
            <div class="form-group">
                <label>Employee</label>
                <select name="employee_id" required>
                    <option value="">Select Employee</option>
                    ${this.employees.filter(e => e.active && !e.hidden).map(e => 
                        `<option value="${e.id}">${e.friendly_name}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group">
                <label>Child</label>
                <select name="child_id" required>
                    <option value="">Select Child</option>
                    ${this.children.filter(c => c.active).map(c => 
                        `<option value="${c.id}" ${c.id === this.selectedChildId ? 'selected' : ''}>${c.name}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group">
                <label>Start Time</label>
                <input type="time" name="start_time" required>
            </div>
            <div class="form-group">
                <label>End Time</label>
                <input type="time" name="end_time" required>
            </div>
            <div class="form-group">
                <label>Service Code</label>
                <input type="text" name="service_code">
            </div>
            <button type="submit" class="btn-primary">Save Shift</button>
        </form>
    `;
    this.showModal(content);
    
    document.getElementById('shift-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData);
        data.start_time = data.start_time + ':00';
        data.end_time = data.end_time + ':00';
        
        try {
            const result = await this.api('/api/shifts', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            
            if (result.warnings && result.warnings.length > 0) {
                this.showToast(result.warnings.join(', '), 'warning');
            } else {
                this.showToast('Shift created successfully');
            }
            this.closeModal();
            this.loadDashboard();
        } catch (error) {
            // Check if it's a structured error response
            if (error.response && error.response.status === 409) {
                // Conflict error - show the detailed message
                const errorData = error.response.data || error.response;
                const message = errorData.message || errorData.error || 'Schedule conflict detected';
                this.showToast(message, 'error');
            } else {
                // Generic error
                this.showToast(error.message || 'Failed to create shift', 'error');
            }
        }
    });
};

App.prototype.showShiftDetails = async function(shift) {
    const hours = this.calculateShiftHours(shift.start_time, shift.end_time);
    const content = `
        <div class="modal-header">
            <h2>Shift Details</h2>
        </div>
        <div class="detail-container">
            <div class="detail-section">
                <div class="detail-row">
                    <span class="detail-label">Date</span>
                    <span class="detail-value">${this.formatDate(shift.date)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Employee</span>
                    <span class="detail-value">${shift.employee_name}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Child</span>
                    <span class="detail-value">${shift.child_name}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Time</span>
                    <span class="detail-value">${this.formatTime(shift.start_time)} - ${this.formatTime(shift.end_time)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Duration</span>
                    <span class="detail-value">${hours} hours</span>
                </div>
                ${shift.service_code ? `
                <div class="detail-row">
                    <span class="detail-label">Service Code</span>
                    <span class="detail-value">${shift.service_code}</span>
                </div>
                ` : ''}
            </div>
            <div class="detail-section detail-meta">
                <div class="detail-row">
                    <span class="detail-label">Status</span>
                    <span class="detail-value status-${shift.status}">${shift.status}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Source</span>
                    <span class="detail-value">${shift.is_imported ? '📥 Imported (Read-only)' : '✏️ Manual Entry'}</span>
                </div>
            </div>
        </div>
        ${!shift.is_imported ? `
            <div class="modal-actions">
                <button onclick="app.editShift(${shift.id})" class="btn-primary">Edit Shift</button>
                <button onclick="app.deleteShift(${shift.id})" class="btn-secondary">Delete Shift</button>
            </div>
        ` : ''}
    `;
    this.showModal(content);
};