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
            this.showToast(error.message, 'error');
        }
    });
};

App.prototype.showShiftDetails = async function(shift) {
    const content = `
        <h2>Shift Details</h2>
        <p><strong>Date:</strong> ${this.formatDate(shift.date)}</p>
        <p><strong>Employee:</strong> ${shift.employee_name}</p>
        <p><strong>Child:</strong> ${shift.child_name}</p>
        <p><strong>Time:</strong> ${this.formatTime(shift.start_time)} - ${this.formatTime(shift.end_time)}</p>
        <p><strong>Service Code:</strong> ${shift.service_code || 'N/A'}</p>
        <p><strong>Status:</strong> ${shift.status}</p>
        <p><strong>Source:</strong> ${shift.is_imported ? 'Imported (Read-only)' : 'Manual Entry'}</p>
        ${!shift.is_imported ? `
            <button onclick="app.editShift(${shift.id})" class="btn-primary">Edit</button>
            <button onclick="app.deleteShift(${shift.id})" class="btn-secondary">Delete</button>
        ` : ''}
    `;
    this.showModal(content);
};