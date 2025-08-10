/* Budget Reports management functions */

App.prototype.loadBudget = async function() {
    // Load budget reports immediately
    await this.loadBudgetReports();
    
    // Setup event listeners for report actions
    this.setupReportListeners();
};

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
                    <td>${this.formatCurrency(report.total_budgeted)}</td>
                    <td>${this.formatCurrency(report.total_spent)}</td>
                    <td>${(report.utilization_percent || 0).toFixed(1)}%</td>
                    <td>
                        <button onclick="app.viewReportDetails(${report.id})" class="btn-primary">View</button>
                        <button onclick="app.deleteBudgetReport(${report.id})" class="btn-secondary">Delete</button>
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
                <p><strong>Total Budget:</strong> ${this.formatCurrency(data.budget_summary.total_budgeted)}</p>
                <p><strong>Total Spent:</strong> ${this.formatCurrency(data.budget_summary.total_spent)}</p>
                <p><strong>Remaining:</strong> ${this.formatCurrency(data.budget_summary.remaining_balance)}</p>
                <p><strong>Utilization:</strong> ${(data.budget_summary.utilization_percentage || 0).toFixed(1)}%</p>
            </div>
        `;
        
        // Add staffing summary if available
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