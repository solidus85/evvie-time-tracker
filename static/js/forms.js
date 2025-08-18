/* Entity form functions for employees and children */

App.prototype.showEmployeeForm = function(employee = null) {
    const content = `
        <h2>${employee ? 'Edit' : 'Add'} Employee</h2>
        <form id="employee-form">
            <div class="form-group">
                <label>Friendly Name</label>
                <input type="text" name="friendly_name" value="${employee?.friendly_name || ''}" required>
            </div>
            <div class="form-group">
                <label>System Name</label>
                <input type="text" name="system_name" value="${employee?.system_name || ''}" required>
            </div>
            <div class="form-group">
                <label>Active</label>
                <input type="checkbox" name="active" ${employee?.active !== false ? 'checked' : ''}>
            </div>
            <div class="form-group">
                <label>Hidden</label>
                <input type="checkbox" name="hidden" ${employee?.hidden === true ? 'checked' : ''}>
            </div>
            <button type="submit" class="btn-primary">Save</button>
        </form>
    `;
    this.showModal(content);
    
    document.getElementById('employee-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = {
            friendly_name: formData.get('friendly_name'),
            system_name: formData.get('system_name'),
            active: formData.get('active') === 'on',
            hidden: formData.get('hidden') === 'on'
        };
        
        try {
            if (employee) {
                await this.api(`/api/employees/${employee.id}`, {
                    method: 'PUT',
                    body: JSON.stringify(data)
                });
            } else {
                await this.api('/api/employees', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
            }
            this.showToast('Employee saved successfully');
            this.closeModal();
            this.loadEmployees();
        } catch (error) {
            this.showToast(error.message, 'error');
        }
    });
};

App.prototype.showChildForm = function(child = null) {
    const content = `
        <h2>${child ? 'Edit' : 'Add'} Child</h2>
        <form id="child-form">
            <div class="form-group">
                <label>Name</label>
                <input type="text" name="name" value="${child?.name || ''}" required>
            </div>
            <div class="form-group">
                <label>Code</label>
                <input type="text" name="code" value="${child?.code || ''}" required>
            </div>
            <div class="form-group">
                <label>Active</label>
                <input type="checkbox" name="active" ${child?.active !== false ? 'checked' : ''}>
            </div>
            <button type="submit" class="btn-primary">Save</button>
        </form>
    `;
    this.showModal(content);
    
    document.getElementById('child-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = {
            name: formData.get('name'),
            code: formData.get('code'),
            active: formData.get('active') === 'on'
        };
        
        try {
            if (child) {
                await this.api(`/api/children/${child.id}`, {
                    method: 'PUT',
                    body: JSON.stringify(data)
                });
            } else {
                await this.api('/api/children', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
            }
            this.showToast('Child saved successfully');
            this.closeModal();
            this.loadChildren();
        } catch (error) {
            this.showToast(error.message, 'error');
        }
    });
};