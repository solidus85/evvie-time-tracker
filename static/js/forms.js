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
            active: formData.get('active') === 'on'
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

App.prototype.validateCSV = async function() {
    const fileInput = document.getElementById('csv-file');
    if (!fileInput.files || fileInput.files.length === 0) {
        this.showToast('Please select at least one file', 'error');
        return;
    }
    
    const files = fileInput.files;
    const isSingleFile = files.length === 1;
    
    // Show loading indicator and disable buttons
    const loadingDiv = document.getElementById('import-loading');
    const importBtn = document.getElementById('import-csv');
    const validateBtn = document.getElementById('validate-csv');
    const resultsDiv = document.getElementById('import-results');
    
    loadingDiv.style.display = 'block';
    importBtn.disabled = true;
    validateBtn.disabled = true;
    resultsDiv.innerHTML = ''; // Clear previous results
    
    try {
        if (isSingleFile) {
            // Single file validation (backward compatible)
            const formData = new FormData();
            formData.append('file', files[0]);
            
            loadingDiv.querySelector('p').textContent = 'Validating CSV, please wait...';
            
            const response = await fetch('/api/import/validate', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            
            resultsDiv.innerHTML = `
                <h3>Validation Results</h3>
                <p><strong>File:</strong> ${files[0].name}</p>
                <p><strong>Valid:</strong> ${result.valid ? 'Yes' : 'No'}</p>
                <p><strong>Rows:</strong> ${result.rows}</p>
                ${result.errors.length > 0 ? `
                    <h4>Errors:</h4>
                    <div class="import-messages">
                        ${result.errors.map(e => `<div class="import-message error">${e}</div>`).join('')}
                    </div>
                ` : ''}
                ${result.warnings.length > 0 ? `
                    <h4>Warnings:</h4>
                    <div class="import-messages">
                        ${result.warnings.map(w => `<div class="import-message warning">${w}</div>`).join('')}
                    </div>
                ` : ''}
            `;
        } else {
            // Multiple file validation
            const formData = new FormData();
            for (let i = 0; i < files.length; i++) {
                formData.append('files', files[i]);
                loadingDiv.querySelector('p').textContent = `Validating file ${i + 1} of ${files.length}: ${files[i].name}`;
            }
            
            const response = await fetch('/api/import/batch-validate', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            
            resultsDiv.innerHTML = `
                <h3>Batch Validation Results</h3>
                <p><strong>Files:</strong> ${files.length}</p>
                <p><strong>Overall Valid:</strong> ${result.valid ? 'Yes' : 'No'}</p>
                <p><strong>Total Rows:</strong> ${result.total_rows}</p>
                
                <h4>File Summary:</h4>
                <div class="import-messages">
                    ${result.file_results.map(f => `
                        <div class="import-message ${f.valid ? 'warning' : 'error'}">
                            <strong>${f.filename}</strong>: ${f.valid ? 'Valid' : 'Invalid'} (${f.rows} rows)
                        </div>
                    `).join('')}
                </div>
                
                ${result.errors.length > 0 ? `
                    <h4>Errors:</h4>
                    <div class="import-messages">
                        ${result.errors.map(e => `<div class="import-message error">${e}</div>`).join('')}
                    </div>
                ` : ''}
                ${result.warnings.length > 0 ? `
                    <h4>Warnings:</h4>
                    <div class="import-messages">
                        ${result.warnings.map(w => `<div class="import-message warning">${w}</div>`).join('')}
                    </div>
                ` : ''}
            `;
        }
    } catch (error) {
        this.showToast('Validation failed', 'error');
    } finally {
        // Hide loading indicator and re-enable buttons
        loadingDiv.style.display = 'none';
        loadingDiv.querySelector('p').textContent = 'Import in progress, please wait...'; // Reset text
        importBtn.disabled = false;
        validateBtn.disabled = false;
    }
};

App.prototype.importCSV = async function() {
    const fileInput = document.getElementById('csv-file');
    if (!fileInput.files || fileInput.files.length === 0) {
        this.showToast('Please select at least one file', 'error');
        return;
    }
    
    const files = fileInput.files;
    const isSingleFile = files.length === 1;
    
    // Show loading indicator and disable buttons
    const loadingDiv = document.getElementById('import-loading');
    const importBtn = document.getElementById('import-csv');
    const validateBtn = document.getElementById('validate-csv');
    const resultsDiv = document.getElementById('import-results');
    
    loadingDiv.style.display = 'block';
    importBtn.disabled = true;
    validateBtn.disabled = true;
    resultsDiv.innerHTML = ''; // Clear previous results
    
    try {
        if (isSingleFile) {
            // Single file import (backward compatible)
            const formData = new FormData();
            formData.append('file', files[0]);
            
            loadingDiv.querySelector('p').textContent = 'Import in progress, please wait...';
            
            const response = await fetch('/api/import/csv', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            
            resultsDiv.innerHTML = `
                <h3>Import Results</h3>
                <p><strong>File:</strong> ${files[0].name}</p>
                <p><strong>Imported:</strong> ${result.imported}</p>
                <p><strong>Duplicates:</strong> ${result.duplicates}</p>
                ${result.errors.length > 0 ? `
                    <h4>Errors:</h4>
                    <div class="import-messages">
                        ${result.errors.map(e => `<div class="import-message error">${e}</div>`).join('')}
                    </div>
                ` : ''}
                ${result.warnings.length > 0 ? `
                    <h4>Warnings:</h4>
                    <div class="import-messages">
                        ${result.warnings.map(w => `<div class="import-message warning">${w}</div>`).join('')}
                    </div>
                ` : ''}
            `;
            
            this.showToast(`Imported ${result.imported} shifts successfully`);
        } else {
            // Multiple file import
            const formData = new FormData();
            for (let i = 0; i < files.length; i++) {
                formData.append('files', files[i]);
            }
            
            // Process files sequentially with progress updates
            loadingDiv.querySelector('p').textContent = `Processing ${files.length} files...`;
            
            const response = await fetch('/api/import/batch-csv', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            
            resultsDiv.innerHTML = `
                <h3>Batch Import Results</h3>
                <p><strong>Files Processed:</strong> ${files.length}</p>
                <p><strong>Total Imported:</strong> ${result.total_imported}</p>
                <p><strong>Total Duplicates:</strong> ${result.total_duplicates}</p>
                
                <h4>File Summary:</h4>
                <div class="import-messages">
                    ${result.file_results.map(f => `
                        <div class="import-message warning">
                            <strong>${f.filename}</strong>: Imported ${f.imported}, Duplicates ${f.duplicates}
                        </div>
                    `).join('')}
                </div>
                
                ${result.errors.length > 0 ? `
                    <h4>Errors:</h4>
                    <div class="import-messages">
                        ${result.errors.map(e => `<div class="import-message error">${e}</div>`).join('')}
                    </div>
                ` : ''}
                ${result.warnings.length > 0 ? `
                    <h4>Warnings:</h4>
                    <div class="import-messages">
                        ${result.warnings.map(w => `<div class="import-message warning">${w}</div>`).join('')}
                    </div>
                ` : ''}
            `;
            
            this.showToast(`Imported ${result.total_imported} shifts from ${files.length} files`);
        }
        
        this.loadInitialData();
    } catch (error) {
        this.showToast('Import failed', 'error');
    } finally {
        // Hide loading indicator and re-enable buttons
        loadingDiv.style.display = 'none';
        importBtn.disabled = false;
        validateBtn.disabled = false;
    }
};

App.prototype.exportData = async function(format) {
    const startDate = document.getElementById('export-start').value;
    const endDate = document.getElementById('export-end').value;
    
    if (!startDate || !endDate) {
        this.showToast('Please select date range', 'error');
        return;
    }
    
    if (format === 'json') {
        try {
            const data = await this.api('/api/export/json', {
                method: 'POST',
                body: JSON.stringify({ start_date: startDate, end_date: endDate })
            });
            
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `timesheet_${startDate}_${endDate}.json`;
            a.click();
        } catch (error) {
            this.showToast('Export failed', 'error');
        }
    } else {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/api/export/${format}`;
        form.style.display = 'none';
        
        const data = { start_date: startDate, end_date: endDate };
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'data';
        input.value = JSON.stringify(data);
        form.appendChild(input);
        
        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
    }
};