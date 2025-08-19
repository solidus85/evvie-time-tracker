/* Budget Management functions with tabs */

App.prototype.loadBudget = async function() {
    // Initialize tab switching
    this.setupBudgetTabs();
    
    // Load initial tab data (PDF reports)
    await this.loadBudgetReports();
    
    // Setup all event listeners
    this.setupReportListeners();
    this.setupBudgetListeners();
    this.setupRateListeners();
    this.setupAllocationListeners();
    this.setupUtilizationListeners();
    
    // Populate dropdowns
    await this.populateBudgetDropdowns();
    
    // Set default dates
    this.setDefaultBudgetDates();
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
            switch(tabName) {
                case 'reports':
                    await this.loadBudgetReports();
                    break;
                case 'budgets':
                    await this.loadChildBudgets();
                    break;
                case 'rates':
                    await this.loadEmployeeRates();
                    break;
                case 'allocations':
                    await this.loadAllocations();
                    break;
                case 'utilization':
                    await this.loadUtilization();
                    break;
            }
        });
    });
};

App.prototype.setupReportListeners = function() {
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

// Child Budgets functionality
App.prototype.setupBudgetListeners = function() {
    const addBtn = document.getElementById('add-budget');
    const importBtn = document.getElementById('import-budgets');
    const fileInput = document.getElementById('budget-csv-file');
    const refreshBtn = document.getElementById('refresh-budgets');
    const form = document.getElementById('child-budget-form');
    const cancelBtn = document.getElementById('cancel-budget');
    
    addBtn?.addEventListener('click', () => this.showBudgetForm());
    importBtn?.addEventListener('click', () => fileInput.click());
    fileInput?.addEventListener('change', (e) => this.importBudgetCSV(e));
    refreshBtn?.addEventListener('click', () => this.loadChildBudgets());
    form?.addEventListener('submit', (e) => this.saveBudget(e));
    cancelBtn?.addEventListener('click', () => this.hideBudgetForm());
};

App.prototype.loadChildBudgets = async function() {
    try {
        const budgets = await this.api('/api/budget/children');
        const tbody = document.querySelector('#budgets-table tbody');
        
        if (budgets.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">No budgets configured</td></tr>';
            return;
        }
        
        tbody.innerHTML = budgets.map(budget => `
            <tr>
                <td>${budget.child_name}</td>
                <td>${this.formatDate(budget.period_start)} - ${this.formatDate(budget.period_end)}</td>
                <td>${this.formatCurrency(budget.budget_amount)}</td>
                <td>${budget.budget_hours || '-'}</td>
                <td>${budget.notes || '-'}</td>
                <td class="action-buttons">
                    <button onclick="app.editBudget(${budget.id})" class="btn-icon btn-edit" title="Edit">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                        </svg>
                    </button>
                    <button onclick="app.deleteBudget(${budget.id})" class="btn-icon btn-delete" title="Delete">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            <line x1="10" y1="11" x2="10" y2="17"></line>
                            <line x1="14" y1="11" x2="14" y2="17"></line>
                        </svg>
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        this.showToast('Failed to load budgets', 'error');
    }
};

App.prototype.showBudgetForm = function(budget = null) {
    const form = document.getElementById('budget-form');
    const formTitle = form.querySelector('h3');
    
    if (budget) {
        formTitle.textContent = 'Edit Child Budget';
        document.getElementById('budget-id').value = budget.id;
        document.getElementById('budget-child').value = budget.child_id;
        document.getElementById('budget-start').value = budget.period_start;
        document.getElementById('budget-end').value = budget.period_end;
        document.getElementById('budget-amount').value = budget.budget_amount;
        document.getElementById('budget-hours').value = budget.budget_hours || '';
        document.getElementById('budget-notes').value = budget.notes || '';
    } else {
        formTitle.textContent = 'Add Child Budget';
        document.getElementById('child-budget-form').reset();
        document.getElementById('budget-id').value = '';
    }
    
    form.style.display = 'block';
};

App.prototype.hideBudgetForm = function() {
    document.getElementById('budget-form').style.display = 'none';
};

App.prototype.saveBudget = async function(e) {
    e.preventDefault();
    
    const id = document.getElementById('budget-id').value;
    const data = {
        child_id: parseInt(document.getElementById('budget-child').value),
        period_start: document.getElementById('budget-start').value,
        period_end: document.getElementById('budget-end').value,
        budget_amount: parseFloat(document.getElementById('budget-amount').value),
        budget_hours: parseFloat(document.getElementById('budget-hours').value) || null,
        notes: document.getElementById('budget-notes').value
    };
    
    try {
        const url = id ? `/api/budget/children/${id}` : '/api/budget/children';
        const method = id ? 'PUT' : 'POST';
        
        await this.api(url, { method, body: JSON.stringify(data) });
        this.showToast('Budget saved successfully');
        this.hideBudgetForm();
        await this.loadChildBudgets();
    } catch (error) {
        this.showToast('Failed to save budget', 'error');
    }
};

App.prototype.editBudget = async function(id) {
    try {
        const budget = await this.api(`/api/budget/children/${id}`);
        this.showBudgetForm(budget);
    } catch (error) {
        this.showToast('Failed to load budget', 'error');
    }
};

App.prototype.deleteBudget = async function(id) {
    if (!confirm('Delete this budget?')) return;
    
    try {
        await this.api(`/api/budget/children/${id}`, { method: 'DELETE' });
        this.showToast('Budget deleted');
        await this.loadChildBudgets();
    } catch (error) {
        this.showToast('Failed to delete budget', 'error');
    }
};

App.prototype.importBudgetCSV = async function(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const result = await fetch('/api/budget/import', {
            method: 'POST',
            body: formData
        }).then(r => r.json());
        
        this.showToast(`Imported ${result.imported_count} budgets`);
        await this.loadChildBudgets();
    } catch (error) {
        this.showToast('Import failed', 'error');
    }
    
    e.target.value = '';
};

// Employee Rates functionality
App.prototype.setupRateListeners = function() {
    const addBtn = document.getElementById('add-rate');
    const refreshBtn = document.getElementById('refresh-rates');
    const form = document.getElementById('employee-rate-form');
    const cancelBtn = document.getElementById('cancel-rate');
    
    addBtn?.addEventListener('click', () => this.showRateForm());
    refreshBtn?.addEventListener('click', () => this.loadEmployeeRates());
    form?.addEventListener('submit', (e) => this.saveRate(e));
    cancelBtn?.addEventListener('click', () => this.hideRateForm());
};

App.prototype.loadEmployeeRates = async function() {
    try {
        const rates = await this.api('/api/budget/rates');
        const tbody = document.querySelector('#rates-table tbody');
        
        if (rates.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7">No rates configured</td></tr>';
            return;
        }
        
        tbody.innerHTML = rates.map(rate => {
            const status = !rate.end_date || new Date(rate.end_date) > new Date() ? 'Active' : 'Inactive';
            return `
                <tr>
                    <td>${rate.employee_name}</td>
                    <td>${this.formatCurrency(rate.hourly_rate)}</td>
                    <td>${this.formatDate(rate.effective_date)}</td>
                    <td>${rate.end_date ? this.formatDate(rate.end_date) : '-'}</td>
                    <td>${status}</td>
                    <td>${rate.notes || '-'}</td>
                    <td class="action-buttons">
                        <button onclick="app.editRate(${rate.id})" class="btn-icon btn-edit" title="Edit">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                            </svg>
                        </button>
                        <button onclick="app.deleteRate(${rate.id})" class="btn-icon btn-delete" title="Delete">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                <line x1="10" y1="11" x2="10" y2="17"></line>
                                <line x1="14" y1="11" x2="14" y2="17"></line>
                            </svg>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        this.showToast('Failed to load rates', 'error');
    }
};

App.prototype.showRateForm = function(rate = null) {
    const form = document.getElementById('rate-form');
    const formTitle = form.querySelector('h3');
    
    if (rate) {
        formTitle.textContent = 'Edit Employee Rate';
        document.getElementById('rate-id').value = rate.id;
        document.getElementById('rate-employee').value = rate.employee_id;
        document.getElementById('rate-amount').value = rate.hourly_rate;
        document.getElementById('rate-effective').value = rate.effective_date;
        document.getElementById('rate-end').value = rate.end_date || '';
        document.getElementById('rate-notes').value = rate.notes || '';
    } else {
        formTitle.textContent = 'Add Employee Rate';
        document.getElementById('employee-rate-form').reset();
        document.getElementById('rate-id').value = '';
    }
    
    form.style.display = 'block';
};

App.prototype.hideRateForm = function() {
    document.getElementById('rate-form').style.display = 'none';
};

App.prototype.saveRate = async function(e) {
    e.preventDefault();
    
    const id = document.getElementById('rate-id').value;
    const data = {
        employee_id: parseInt(document.getElementById('rate-employee').value),
        hourly_rate: parseFloat(document.getElementById('rate-amount').value),
        effective_date: document.getElementById('rate-effective').value,
        end_date: document.getElementById('rate-end').value || null,
        notes: document.getElementById('rate-notes').value
    };
    
    try {
        const url = id ? `/api/budget/rates/${id}` : '/api/budget/rates';
        const method = id ? 'PUT' : 'POST';
        
        await this.api(url, { method, body: JSON.stringify(data) });
        this.showToast('Rate saved successfully');
        this.hideRateForm();
        await this.loadEmployeeRates();
    } catch (error) {
        this.showToast('Failed to save rate', 'error');
    }
};

App.prototype.editRate = async function(id) {
    try {
        const rate = await this.api(`/api/budget/rates/${id}`);
        this.showRateForm(rate);
    } catch (error) {
        this.showToast('Failed to load rate', 'error');
    }
};

App.prototype.deleteRate = async function(id) {
    if (!confirm('Delete this rate?')) return;
    
    try {
        await this.api(`/api/budget/rates/${id}`, { method: 'DELETE' });
        this.showToast('Rate deleted');
        await this.loadEmployeeRates();
    } catch (error) {
        this.showToast('Failed to delete rate', 'error');
    }
};

// Allocations functionality
App.prototype.setupAllocationListeners = function() {
    const periodSelect = document.getElementById('allocation-period');
    const addBtn = document.getElementById('add-allocation');
    const refreshBtn = document.getElementById('refresh-allocations');
    const form = document.getElementById('budget-allocation-form');
    const cancelBtn = document.getElementById('cancel-allocation');
    
    periodSelect?.addEventListener('change', () => this.loadAllocations());
    addBtn?.addEventListener('click', () => this.showAllocationForm());
    refreshBtn?.addEventListener('click', () => this.loadAllocations());
    form?.addEventListener('submit', (e) => this.saveAllocation(e));
    cancelBtn?.addEventListener('click', () => this.hideAllocationForm());
};

App.prototype.loadAllocations = async function() {
    const periodId = document.getElementById('allocation-period')?.value;
    if (!periodId) return;
    
    try {
        const allocations = await this.api(`/api/budget/allocations?period_id=${periodId}`);
        const tbody = document.querySelector('#allocations-table tbody');
        
        if (allocations.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">No allocations for this period</td></tr>';
            return;
        }
        
        tbody.innerHTML = allocations.map(alloc => {
            const cost = alloc.allocated_hours * (alloc.hourly_rate || 0);
            return `
                <tr>
                    <td>${alloc.child_name}</td>
                    <td>${alloc.employee_name}</td>
                    <td>${alloc.allocated_hours}</td>
                    <td>${this.formatCurrency(cost)}</td>
                    <td>${alloc.notes || '-'}</td>
                    <td class="action-buttons">
                        <button onclick="app.editAllocation(${alloc.id})" class="btn-icon btn-edit" title="Edit">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                            </svg>
                        </button>
                        <button onclick="app.deleteAllocation(${alloc.id})" class="btn-icon btn-delete" title="Delete">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                <line x1="10" y1="11" x2="10" y2="17"></line>
                                <line x1="14" y1="11" x2="14" y2="17"></line>
                            </svg>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        this.showToast('Failed to load allocations', 'error');
    }
};

App.prototype.showAllocationForm = function(allocation = null) {
    const form = document.getElementById('allocation-form');
    const formTitle = form.querySelector('h3');
    
    if (allocation) {
        formTitle.textContent = 'Edit Budget Allocation';
        document.getElementById('allocation-id').value = allocation.id;
        document.getElementById('allocation-child').value = allocation.child_id;
        document.getElementById('allocation-employee').value = allocation.employee_id;
        document.getElementById('allocation-hours').value = allocation.allocated_hours;
        document.getElementById('allocation-notes').value = allocation.notes || '';
    } else {
        formTitle.textContent = 'Add Budget Allocation';
        document.getElementById('budget-allocation-form').reset();
        document.getElementById('allocation-id').value = '';
    }
    
    form.style.display = 'block';
};

App.prototype.hideAllocationForm = function() {
    document.getElementById('allocation-form').style.display = 'none';
};

App.prototype.saveAllocation = async function(e) {
    e.preventDefault();
    
    const id = document.getElementById('allocation-id').value;
    const periodId = document.getElementById('allocation-period').value;
    
    const data = {
        child_id: parseInt(document.getElementById('allocation-child').value),
        employee_id: parseInt(document.getElementById('allocation-employee').value),
        period_id: parseInt(periodId),
        allocated_hours: parseFloat(document.getElementById('allocation-hours').value),
        notes: document.getElementById('allocation-notes').value
    };
    
    try {
        const url = id ? `/api/budget/allocations/${id}` : '/api/budget/allocations';
        const method = id ? 'PUT' : 'POST';
        
        await this.api(url, { method, body: JSON.stringify(data) });
        this.showToast('Allocation saved successfully');
        this.hideAllocationForm();
        await this.loadAllocations();
    } catch (error) {
        this.showToast('Failed to save allocation', 'error');
    }
};

App.prototype.editAllocation = async function(id) {
    try {
        const allocation = await this.api(`/api/budget/allocations/${id}`);
        this.showAllocationForm(allocation);
    } catch (error) {
        this.showToast('Failed to load allocation', 'error');
    }
};

App.prototype.deleteAllocation = async function(id) {
    if (!confirm('Delete this allocation?')) return;
    
    try {
        await this.api(`/api/budget/allocations/${id}`, { method: 'DELETE' });
        this.showToast('Allocation deleted');
        await this.loadAllocations();
    } catch (error) {
        this.showToast('Failed to delete allocation', 'error');
    }
};

// Utilization functionality
App.prototype.setupUtilizationListeners = function() {
    const refreshBtn = document.getElementById('refresh-utilization');
    refreshBtn?.addEventListener('click', () => this.loadUtilization());
};

App.prototype.loadUtilization = async function() {
    const startDate = document.getElementById('util-start').value;
    const endDate = document.getElementById('util-end').value;
    
    if (!startDate || !endDate) {
        document.getElementById('util-summary').innerHTML = '<p>Select date range</p>';
        return;
    }
    
    try {
        const util = await this.api('/api/budget/utilization', {
            method: 'POST',
            body: JSON.stringify({ start_date: startDate, end_date: endDate })
        });
        
        // Summary section
        const summary = document.getElementById('util-summary');
        summary.innerHTML = `
            <div class="util-card">
                <h3>Overall Summary</h3>
                <p>Total Budget: ${this.formatCurrency(util.total_budget)}</p>
                <p>Total Spent: ${this.formatCurrency(util.total_spent)}</p>
                <p>Remaining: ${this.formatCurrency(util.total_remaining)}</p>
                <p>Overall Utilization: ${util.overall_utilization.toFixed(1)}%</p>
            </div>
        `;
        
        // Table
        const tbody = document.querySelector('#utilization-table tbody');
        tbody.innerHTML = util.children.map(child => {
            const status = child.utilization > 90 ? 'High' : 
                          child.utilization > 75 ? 'Medium' : 'Normal';
            return `
                <tr>
                    <td>${child.name}</td>
                    <td>${this.formatCurrency(child.budget)}</td>
                    <td>${this.formatCurrency(child.spent)}</td>
                    <td>${this.formatCurrency(child.remaining)}</td>
                    <td>${child.utilization.toFixed(1)}%</td>
                    <td>${status}</td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        this.showToast('Failed to load utilization', 'error');
    }
};

// Helper functions
App.prototype.populateBudgetDropdowns = async function() {
    // Children dropdown
    const activeChildren = this.children.filter(c => c.active);
    const childOptions = activeChildren.map(child => 
        `<option value="${child.id}">${child.name}</option>`
    ).join('');
    
    document.getElementById('budget-child').innerHTML = childOptions;
    document.getElementById('allocation-child').innerHTML = childOptions;
    
    // Employees dropdown
    const activeEmployees = this.employees.filter(e => e.active && !e.hidden);
    const employeeOptions = activeEmployees.map(emp => 
        `<option value="${emp.id}">${emp.friendly_name}</option>`
    ).join('');
    
    document.getElementById('rate-employee').innerHTML = employeeOptions;
    document.getElementById('allocation-employee').innerHTML = employeeOptions;
    
    // Payroll periods dropdown
    try {
        const periods = await this.api('/api/payroll/periods');
        const periodOptions = periods.slice(0, 10).map(period => 
            `<option value="${period.id}">${this.formatDate(period.start_date)} - ${this.formatDate(period.end_date)}</option>`
        ).join('');
        
        document.getElementById('allocation-period').innerHTML = periodOptions;
    } catch (error) {
        console.error('Failed to load periods:', error);
    }
};

App.prototype.setDefaultBudgetDates = async function() {
    try {
        const currentPeriod = await this.api('/api/payroll/periods/current');
        if (currentPeriod) {
            document.getElementById('util-start').value = currentPeriod.start_date;
            document.getElementById('util-end').value = currentPeriod.end_date;
        }
    } catch (error) {
        console.error('Failed to set default dates:', error);
    }
};

// Existing PDF report functions
App.prototype.loadBudgetReports = async function() {
    try {
        const reports = await this.api('/api/budget/reports');
        const tbody = document.querySelector('#reports-table tbody');
        
        if (reports.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7">No reports uploaded</td></tr>';
            return;
        }
        
        tbody.innerHTML = reports.map(report => {
            const periodStart = this.formatDateWithYear(report.period_start);
            const periodEnd = this.formatDateWithYear(report.period_end);
            
            return `
                <tr>
                    <td>${this.formatDate(report.report_date)}</td>
                    <td>${report.child_name || 'Unknown'}</td>
                    <td>${periodStart} - ${periodEnd}</td>
                    <td>${this.formatCurrency(report.total_budgeted)}</td>
                    <td>${this.formatCurrency(report.total_spent)}</td>
                    <td>${(report.utilization_percent || 0).toFixed(1)}%</td>
                    <td class="action-buttons">
                        <button onclick="app.viewReportDetails(${report.id})" class="btn-icon btn-view" title="View">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                                <circle cx="12" cy="12" r="3"></circle>
                            </svg>
                        </button>
                        <button onclick="app.deleteBudgetReport(${report.id})" class="btn-icon btn-delete" title="Delete">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                <line x1="10" y1="11" x2="10" y2="17"></line>
                                <line x1="14" y1="11" x2="14" y2="17"></line>
                            </svg>
                        </button>
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
                    <p>Total Budget: ${this.formatCurrency(result.summary.total_budget)}</p>
                    <p>Total Spent: ${this.formatCurrency(result.summary.total_spent)}</p>
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
                <p><strong>Period:</strong> ${this.formatDateWithYear(data.budget_summary.budget_period_start)} - ${this.formatDateWithYear(data.budget_summary.budget_period_end)}</p>
                <p><strong>Total Budget:</strong> ${this.formatCurrency(data.budget_summary.total_budgeted)}</p>
                <p><strong>Total Spent:</strong> ${this.formatCurrency(data.budget_summary.total_spent)}</p>
                <p><strong>Remaining:</strong> ${this.formatCurrency(data.budget_summary.remaining_balance)}</p>
                <p><strong>Utilization:</strong> ${(data.budget_summary.utilization_percentage || 0).toFixed(1)}%</p>
            </div>
        `;
        
        if (data.staffing_summary && Object.keys(data.staffing_summary).length > 0) {
            html += `
                <div class="report-detail-card">
                    <h4>Staffing Summary</h4>
                    <p><strong>Total Allocation:</strong> ${this.formatCurrency(data.staffing_summary.total_allocation)}</p>
                    <p><strong>Daily Usage Rate:</strong> ${this.formatCurrency(data.staffing_summary.daily_usage_rate)}/day</p>
                    <p><strong>Remaining Balance:</strong> ${this.formatCurrency(data.staffing_summary.remaining_balance)}</p>
                </div>
            `;
        }
        
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
                        <td>${this.formatCurrency(emp.total_amount)}</td>
                        <td>${this.formatCurrency(emp.average_rate)}</td>
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

App.prototype.deleteBudgetReport = async function(reportId) {
    if (!confirm('Are you sure you want to delete this budget report?')) {
        return;
    }
    
    try {
        const response = await this.api(`/api/budget/reports/${reportId}`, {
            method: 'DELETE'
        });
        
        if (response.success) {
            this.showToast('Report deleted successfully');
            await this.loadBudgetReports();
        }
    } catch (error) {
        this.showToast('Failed to delete report', 'error');
        console.error('Delete report error:', error);
    }
};