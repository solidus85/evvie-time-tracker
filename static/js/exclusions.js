/* Exclusion periods management */

App.prototype.loadExclusions = async function() {
    const exclusions = await this.api('/api/payroll/exclusions');
    
    document.querySelector('#exclusions-table tbody').innerHTML = exclusions.map(exc => `
        <tr>
            <td>${exc.name}</td>
            <td>${exc.start_date}</td>
            <td>${exc.end_date}</td>
            <td>${exc.reason || 'N/A'}</td>
            <td>
                <button onclick="app.editExclusion(${exc.id})" class="btn-primary">Edit</button>
                <button onclick="app.deleteExclusion(${exc.id})" class="btn-secondary">Delete</button>
            </td>
        </tr>
    `).join('');
};

App.prototype.showExclusionForm = function(exclusion = null) {
    const content = `
        <h2>${exclusion ? 'Edit' : 'Add'} Exclusion Period</h2>
        <form id="exclusion-form">
            <div class="form-group">
                <label>Name</label>
                <input type="text" name="name" value="${exclusion?.name || ''}" required>
            </div>
            <div class="form-group">
                <label>Start Date</label>
                <input type="date" name="start_date" value="${exclusion?.start_date || ''}" required>
            </div>
            <div class="form-group">
                <label>End Date</label>
                <input type="date" name="end_date" value="${exclusion?.end_date || ''}" required>
            </div>
            <div class="form-group">
                <label>Reason (optional)</label>
                <input type="text" name="reason" value="${exclusion?.reason || ''}">
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