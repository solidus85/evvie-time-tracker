/* Budget management functions */

App.prototype.loadBudget = async function() {
    // Initialize tab switching
    this.setupBudgetTabs();
    
    // Load initial tab data
    await this.loadChildBudgets();
    
    // Setup event listeners for budget actions
    document.getElementById('add-budget').addEventListener('click', () => this.showBudgetForm());
    document.getElementById('import-budgets').addEventListener('click', () => {
        document.getElementById('budget-csv-file').click();
    });
    document.getElementById('budget-csv-file').addEventListener('change', (e) => this.importBudgetCSV(e));
    document.getElementById('add-rate').addEventListener('click', () => this.showRateForm());
    document.getElementById('add-allocation').addEventListener('click', () => this.showAllocationForm());
    
    // Load periods for allocation dropdown
    await this.loadAllocationPeriods();
};

App.prototype.setupBudgetTabs = function() {
    const tabs = document.querySelectorAll('#budget-view .tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', async (e) => {
            // Update active states
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('#budget-view .tab-content').forEach(c => c.classList.remove('active'));
            
            e.target.classList.add('active');
            const tabName = e.target.dataset.tab;
            document.getElementById(`${tabName}-tab`).classList.add('active');
            
            // Load tab data
            if (tabName === 'child-budgets') {
                await this.loadChildBudgets();
            } else if (tabName === 'employee-rates') {
                await this.loadEmployeeRates();
            } else if (tabName === 'allocations') {
                await this.loadAllocations();
            } else if (tabName === 'utilization') {
                await this.loadUtilization();
            } else if (tabName === 'reports') {
                await this.loadBudgetReports();
                this.setupReportListeners();
            }
        });
    });
};

App.prototype.loadChildBudgets = async function() {
    try {
        const budgets = await this.api('/api/budget/children');
        const tbody = document.querySelector('#budgets-table tbody');
        
        if (budgets.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7">No budgets configured</td></tr>';
            return;
        }
        
        tbody.innerHTML = budgets.map(budget => `
            <tr>
                <td>${budget.child_name || 'Unknown'}</td>
                <td>${this.formatDate(budget.period_start)}</td>
                <td>${this.formatDate(budget.period_end)}</td>
                <td>${budget.budget_hours || 'N/A'}</td>
                <td>${budget.budget_amount ? '$' + budget.budget_amount.toFixed(2) : 'N/A'}</td>
                <td>${budget.notes || ''}</td>
                <td>
                    <button onclick="app.editBudget(${budget.id})" class="btn-primary">Edit</button>
                    <button onclick="app.deleteBudget(${budget.id})" class="btn-secondary">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        this.showToast('Failed to load budgets', 'error');
    }
};

App.prototype.loadEmployeeRates = async function() {
    try {
        const rates = await this.api('/api/budget/rates');
        const tbody = document.querySelector('#rates-table tbody');
        
        if (rates.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">No rates configured</td></tr>';
            return;
        }
        
        tbody.innerHTML = rates.map(rate => `
            <tr>
                <td>${rate.employee_name}</td>
                <td>$${rate.hourly_rate.toFixed(2)}</td>
                <td>${this.formatDate(rate.effective_date)}</td>
                <td>${rate.end_date ? this.formatDate(rate.end_date) : 'Current'}</td>
                <td>${rate.notes || ''}</td>
                <td>
                    <button onclick="app.editRate(${rate.id})" class="btn-primary">Edit</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        this.showToast('Failed to load rates', 'error');
    }
};

App.prototype.loadAllocations = async function() {
    const periodSelect = document.getElementById('allocation-period');
    const periodId = periodSelect.value;
    
    if (!periodId) {
        document.querySelector('#allocations-table tbody').innerHTML = 
            '<tr><td colspan="5">Please select a period</td></tr>';
        return;
    }
    
    try {
        const allocations = await this.api(`/api/budget/allocations?period_id=${periodId}`);
        const tbody = document.querySelector('#allocations-table tbody');
        
        if (allocations.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No allocations for this period</td></tr>';
            return;
        }
        
        tbody.innerHTML = allocations.map(alloc => `
            <tr>
                <td>${alloc.child_name}</td>
                <td>${alloc.employee_name}</td>
                <td>${alloc.allocated_hours}</td>
                <td>${alloc.notes || ''}</td>
                <td>
                    <button onclick="app.editAllocation(${alloc.id})" class="btn-primary">Edit</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        this.showToast('Failed to load allocations', 'error');
    }
};

App.prototype.loadAllocationPeriods = async function() {
    try {
        const periods = await this.api('/api/payroll/periods');
        const select = document.getElementById('allocation-period');
        
        select.innerHTML = '<option value="">Select Period</option>' +
            periods.map(period => `
                <option value="${period.id}">
                    ${this.formatDate(period.start_date)} - ${this.formatDate(period.end_date)}
                </option>
            `).join('');
        
        // Add change listener
        select.addEventListener('change', () => this.loadAllocations());
    } catch (error) {
        console.error('Failed to load periods:', error);
    }
};

App.prototype.loadUtilization = async function() {
    const dashboard = document.querySelector('.utilization-dashboard');
    
    try {
        // Get current period
        const currentPeriod = await this.api('/api/payroll/periods/current');
        if (!currentPeriod) {
            dashboard.innerHTML = '<p>No current period configured</p>';
            return;
        }
        
        // Get all children budgets for current period
        const budgets = await this.api('/api/budget/children?active_only=true');
        const utilizationData = [];
        
        for (const budget of budgets) {
            // Check if budget overlaps with current period
            if (budget.period_start <= currentPeriod.end_date && 
                budget.period_end >= currentPeriod.start_date) {
                try {
                    const utilization = await this.api(
                        `/api/budget/utilization?child_id=${budget.child_id}&period_start=${budget.period_start}&period_end=${budget.period_end}`
                    );
                    utilization.child_name = budget.child_name;
                    utilizationData.push(utilization);
                } catch (e) {
                    // Skip if no utilization data
                }
            }
        }
        
        if (utilizationData.length === 0) {
            dashboard.innerHTML = '<p>No budget utilization data available</p>';
            return;
        }
        
        dashboard.innerHTML = `
            <div class="utilization-grid">
                ${utilizationData.map(util => `
                    <div class="utilization-card">
                        <h3>${util.child_name}</h3>
                        <div class="utilization-metrics">
                            <div class="metric">
                                <span class="label">Budget Hours:</span>
                                <span class="value">${util.budget_hours || 0}</span>
                            </div>
                            <div class="metric">
                                <span class="label">Used Hours:</span>
                                <span class="value">${util.actual_hours ? util.actual_hours.toFixed(2) : '0'}</span>
                            </div>
                            <div class="metric">
                                <span class="label">Remaining:</span>
                                <span class="value ${util.hours_remaining < 0 ? 'over-budget' : ''}">
                                    ${util.hours_remaining ? util.hours_remaining.toFixed(2) : '0'}
                                </span>
                            </div>
                            <div class="metric">
                                <span class="label">Utilization:</span>
                                <span class="value">${util.utilization_percent ? util.utilization_percent.toFixed(1) : '0'}%</span>
                            </div>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill ${util.utilization_percent > 100 ? 'over' : ''}" 
                                 style="width: ${Math.min(util.utilization_percent || 0, 100)}%"></div>
                        </div>
                        ${util.budget_amount ? `
                            <div class="budget-amount">
                                <span class="label">Budget: $${util.budget_amount.toFixed(2)}</span>
                                <span class="label">Spent: $${(util.actual_cost || 0).toFixed(2)}</span>
                            </div>
                        ` : ''}
                    </div>
                `).join('')}
            </div>
        `;
    } catch (error) {
        dashboard.innerHTML = '<p>Failed to load utilization data</p>';
        console.error('Utilization error:', error);
    }
};

App.prototype.showBudgetForm = function(budgetId = null) {
    const isEdit = budgetId !== null;
    const title = isEdit ? 'Edit Budget' : 'Add Budget';
    
    let formHtml = `
        <h2>${title}</h2>
        <form id="budget-form">
            <div class="form-group">
                <label>Child:</label>
                <select name="child_id" required>
                    <option value="">Select Child</option>
                    ${this.children.filter(c => c.active).map(child => 
                        `<option value="${child.id}">${child.name}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group">
                <label>Period Start:</label>
                <input type="date" name="period_start" required>
            </div>
            <div class="form-group">
                <label>Period End:</label>
                <input type="date" name="period_end" required>
            </div>
            <div class="form-group">
                <label>Budget Hours:</label>
                <input type="number" name="budget_hours" step="0.5" min="0">
            </div>
            <div class="form-group">
                <label>Budget Amount ($):</label>
                <input type="number" name="budget_amount" step="0.01" min="0">
            </div>
            <div class="form-group">
                <label>Notes:</label>
                <textarea name="notes"></textarea>
            </div>
            <button type="submit" class="btn-primary">${isEdit ? 'Update' : 'Create'} Budget</button>
        </form>
    `;
    
    this.showModal(formHtml);
    
    document.getElementById('budget-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData);
        
        // Convert empty strings to null
        Object.keys(data).forEach(key => {
            if (data[key] === '') data[key] = null;
        });
        
        try {
            if (isEdit) {
                await this.api(`/api/budget/children/${budgetId}`, {
                    method: 'PUT',
                    body: JSON.stringify(data)
                });
                this.showToast('Budget updated successfully');
            } else {
                await this.api('/api/budget/children', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
                this.showToast('Budget created successfully');
            }
            this.closeModal();
            await this.loadChildBudgets();
        } catch (error) {
            this.showToast('Failed to save budget', 'error');
        }
    });
};

App.prototype.showRateForm = function(rateId = null) {
    const title = 'Add Employee Rate';
    
    let formHtml = `
        <h2>${title}</h2>
        <form id="rate-form">
            <div class="form-group">
                <label>Employee:</label>
                <select name="employee_id" required>
                    <option value="">Select Employee</option>
                    ${this.employees.filter(e => e.active).map(emp => 
                        `<option value="${emp.id}">${emp.friendly_name}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group">
                <label>Hourly Rate ($):</label>
                <input type="number" name="hourly_rate" step="0.01" min="0" required>
            </div>
            <div class="form-group">
                <label>Effective Date:</label>
                <input type="date" name="effective_date" required>
            </div>
            <div class="form-group">
                <label>End Date (optional):</label>
                <input type="date" name="end_date">
            </div>
            <div class="form-group">
                <label>Notes:</label>
                <textarea name="notes"></textarea>
            </div>
            <button type="submit" class="btn-primary">Create Rate</button>
        </form>
    `;
    
    this.showModal(formHtml);
    
    document.getElementById('rate-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData);
        
        // Convert empty strings to null
        Object.keys(data).forEach(key => {
            if (data[key] === '') data[key] = null;
        });
        
        try {
            await this.api('/api/budget/rates', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            this.showToast('Rate created successfully');
            this.closeModal();
            await this.loadEmployeeRates();
        } catch (error) {
            this.showToast('Failed to save rate', 'error');
        }
    });
};

App.prototype.showAllocationForm = function() {
    const periodId = document.getElementById('allocation-period').value;
    if (!periodId) {
        this.showToast('Please select a period first', 'error');
        return;
    }
    
    let formHtml = `
        <h2>Add Allocation</h2>
        <form id="allocation-form">
            <input type="hidden" name="period_id" value="${periodId}">
            <div class="form-group">
                <label>Child:</label>
                <select name="child_id" required>
                    <option value="">Select Child</option>
                    ${this.children.filter(c => c.active).map(child => 
                        `<option value="${child.id}">${child.name}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group">
                <label>Employee:</label>
                <select name="employee_id" required>
                    <option value="">Select Employee</option>
                    ${this.employees.filter(e => e.active).map(emp => 
                        `<option value="${emp.id}">${emp.friendly_name}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group">
                <label>Allocated Hours:</label>
                <input type="number" name="allocated_hours" step="0.5" min="0" required>
            </div>
            <div class="form-group">
                <label>Notes:</label>
                <textarea name="notes"></textarea>
            </div>
            <button type="submit" class="btn-primary">Create Allocation</button>
        </form>
    `;
    
    this.showModal(formHtml);
    
    document.getElementById('allocation-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData);
        
        // Convert empty strings to null
        Object.keys(data).forEach(key => {
            if (data[key] === '') data[key] = null;
        });
        
        try {
            await this.api('/api/budget/allocations', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            this.showToast('Allocation created successfully');
            this.closeModal();
            await this.loadAllocations();
        } catch (error) {
            this.showToast('Failed to save allocation', 'error');
        }
    });
};

App.prototype.importBudgetCSV = async function(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const result = await fetch('/api/budget/import', {
            method: 'POST',
            body: formData
        }).then(r => r.json());
        
        if (result.error) {
            this.showToast(result.error, 'error');
        } else {
            this.showToast(`Imported ${result.imported} budgets successfully`);
            if (result.errors && result.errors.length > 0) {
                console.error('Import errors:', result.errors);
            }
            await this.loadChildBudgets();
        }
    } catch (error) {
        this.showToast('Failed to import budgets', 'error');
    }
    
    // Reset file input
    event.target.value = '';
};

App.prototype.deleteBudget = async function(budgetId) {
    if (!confirm('Are you sure you want to delete this budget?')) return;
    
    try {
        await this.api(`/api/budget/children/${budgetId}`, { method: 'DELETE' });
        this.showToast('Budget deleted successfully');
        await this.loadChildBudgets();
    } catch (error) {
        this.showToast('Failed to delete budget', 'error');
    }
};

App.prototype.editBudget = async function(budgetId) {
    // For now, just show the form
    // Could fetch existing data first
    this.showBudgetForm(budgetId);
};

App.prototype.editRate = function(rateId) {
    // Placeholder for rate editing
    this.showToast('Rate editing not yet implemented', 'info');
};

App.prototype.editAllocation = function(allocationId) {
    // Placeholder for allocation editing
    this.showToast('Allocation editing not yet implemented', 'info');
};

// Budget Reports functions
App.prototype.setupReportListeners = function() {
    // Upload button
    const uploadBtn = document.getElementById('upload-pdf-report');
    const fileInput = document.getElementById('pdf-report-file');
    const refreshBtn = document.getElementById('refresh-reports');
    
    if (uploadBtn && !uploadBtn.hasListener) {
        uploadBtn.hasListener = true;
        uploadBtn.addEventListener('click', () => fileInput.click());
    }
    
    if (fileInput && !fileInput.hasListener) {
        fileInput.hasListener = true;
        fileInput.addEventListener('change', (e) => this.uploadPDFReport(e));
    }
    
    if (refreshBtn && !refreshBtn.hasListener) {
        refreshBtn.hasListener = true;
        refreshBtn.addEventListener('click', () => this.loadBudgetReports());
    }
};

App.prototype.loadBudgetReports = async function() {
    try {
        const reports = await this.api('/api/budget/reports');
        const tbody = document.querySelector('#reports-table tbody');
        
        if (reports.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7">No reports uploaded</td></tr>';
            return;
        }
        
        tbody.innerHTML = reports.map(report => {
            const periodStart = this.formatDate(report.period_start);
            const periodEnd = this.formatDate(report.period_end);
            
            return `
                <tr>
                    <td>${this.formatDate(report.report_date)}</td>
                    <td>${report.child_name || 'Unknown'}</td>
                    <td>${periodStart} - ${periodEnd}</td>
                    <td>$${(report.total_budgeted || 0).toFixed(2)}</td>
                    <td>$${(report.total_spent || 0).toFixed(2)}</td>
                    <td>${(report.utilization_percent || 0).toFixed(1)}%</td>
                    <td>
                        <button onclick="app.viewReportDetails(${report.id})" class="btn-primary">View</button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        this.showToast('Failed to load reports', 'error');
        console.error('Load reports error:', error);
    }
};

App.prototype.uploadPDFReport = async function(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const resultDiv = document.getElementById('report-upload-result');
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '<p>Uploading and processing PDF...</p>';
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const result = await fetch('/api/budget/upload-report', {
            method: 'POST',
            body: formData
        }).then(r => r.json());
        
        if (result.error) {
            resultDiv.innerHTML = `<p style="color: red;">Error: ${result.error}</p>`;
            this.showToast(result.error, 'error');
        } else {
            resultDiv.innerHTML = `
                <div style="padding: 10px; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px;">
                    <h4>Upload Successful!</h4>
                    <p>Client: ${result.summary.client}</p>
                    <p>Total Budget: $${result.summary.total_budget.toFixed(2)}</p>
                    <p>Total Spent: $${result.summary.total_spent.toFixed(2)}</p>
                    <p>Utilization: ${result.summary.utilization.toFixed(1)}%</p>
                </div>
            `;
            this.showToast('Report uploaded successfully');
            await this.loadBudgetReports();
        }
    } catch (error) {
        resultDiv.innerHTML = `<p style="color: red;">Failed to upload report: ${error.message}</p>`;
        this.showToast('Failed to upload report', 'error');
    }
    
    // Reset file input
    event.target.value = '';
};

App.prototype.viewReportDetails = async function(reportId) {
    try {
        const report = await this.api(`/api/budget/reports/${reportId}`);
        const detailsDiv = document.getElementById('report-details');
        
        if (!report || !report.report_data) {
            this.showToast('Report data not available', 'error');
            return;
        }
        
        const data = report.report_data;
        
        // Build detailed view HTML
        let html = `
            <h3>Report Details</h3>
            <div class="report-detail-card">
                <h4>Client Information</h4>
                <p><strong>Name:</strong> ${data.report_info.client_name || 'Unknown'}</p>
                <p><strong>PMI:</strong> ${data.report_info.pmi || 'N/A'}</p>
                <p><strong>Report Date:</strong> ${this.formatDate(data.report_info.report_date)}</p>
            </div>
            
            <div class="report-detail-card">
                <h4>Budget Summary</h4>
                <p><strong>Period:</strong> ${this.formatDate(data.budget_summary.budget_period_start)} - ${this.formatDate(data.budget_summary.budget_period_end)}</p>
                <p><strong>Total Budget:</strong> $${(data.budget_summary.total_budgeted || 0).toFixed(2)}</p>
                <p><strong>Total Spent:</strong> $${(data.budget_summary.total_spent || 0).toFixed(2)}</p>
                <p><strong>Remaining:</strong> $${(data.budget_summary.remaining_balance || 0).toFixed(2)}</p>
                <p><strong>Utilization:</strong> ${(data.budget_summary.utilization_percentage || 0).toFixed(1)}%</p>
            </div>
        `;
        
        // Add staffing summary if available
        if (data.staffing_summary && Object.keys(data.staffing_summary).length > 0) {
            html += `
                <div class="report-detail-card">
                    <h4>Staffing Summary</h4>
                    <p><strong>Total Allocation:</strong> $${(data.staffing_summary.total_allocation || 0).toFixed(2)}</p>
                    <p><strong>Daily Usage Rate:</strong> $${(data.staffing_summary.daily_usage_rate || 0).toFixed(2)}/day</p>
                    <p><strong>Remaining Balance:</strong> $${(data.staffing_summary.remaining_balance || 0).toFixed(2)}</p>
                </div>
            `;
        }
        
        // Add employee spending if available
        if (data.employee_spending_summary && Object.keys(data.employee_spending_summary).length > 0) {
            html += `
                <div class="report-detail-card">
                    <h4>Employee Spending Summary</h4>
                    <table class="detail-table">
                        <thead>
                            <tr>
                                <th>Employee</th>
                                <th>Total Hours</th>
                                <th>Total Amount</th>
                                <th>Avg Rate</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            for (const [name, emp] of Object.entries(data.employee_spending_summary)) {
                html += `
                    <tr>
                        <td>${name}</td>
                        <td>${emp.total_hours}</td>
                        <td>$${emp.total_amount.toFixed(2)}</td>
                        <td>$${(emp.average_rate || 0).toFixed(2)}</td>
                    </tr>
                `;
            }
            
            html += `
                        </tbody>
                    </table>
                </div>
            `;
        }
        
        html += '<button onclick="app.hideReportDetails()" class="btn-secondary">Close</button>';
        
        detailsDiv.innerHTML = html;
        detailsDiv.style.display = 'block';
        
        // Scroll to details
        detailsDiv.scrollIntoView({ behavior: 'smooth' });
        
    } catch (error) {
        this.showToast('Failed to load report details', 'error');
        console.error('Report details error:', error);
    }
};

App.prototype.hideReportDetails = function() {
    const detailsDiv = document.getElementById('report-details');
    detailsDiv.style.display = 'none';
};