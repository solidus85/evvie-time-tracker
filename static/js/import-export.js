/* Import and export functionality */

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

            // Prominent toast if header schema changed
            if (Array.isArray(result.warnings)) {
                const headerWarn = result.warnings.find(w => w.startsWith('CSV header schema changed'));
                if (headerWarn) this.showToast(headerWarn, 'warning');
            }
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

            // Prominent toast if header schema changed
            if (Array.isArray(result.warnings)) {
                const headerWarn = result.warnings.find(w => w.startsWith('CSV header schema changed'));
                if (headerWarn) this.showToast(headerWarn, 'warning');
            }
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
                <p><strong>Replaced:</strong> ${result.replaced || 0}</p>
                <p><strong>Duplicates:</strong> ${result.duplicates}</p>
                ${result.errors && result.errors.length > 0 ? `
                    <h4>Errors:</h4>
                    <div class="import-messages">
                        ${result.errors.map(e => `<div class="import-message error">${e}</div>`).join('')}
                    </div>
                ` : ''}
                ${result.warnings && result.warnings.length > 0 ? `
                    <h4>Warnings:</h4>
                    <div class="import-messages">
                        ${result.warnings.map(w => `<div class="import-message warning">${w}</div>`).join('')}
                    </div>
                ` : ''}
            `;
            
            const message = result.replaced > 0 
                ? `Imported ${result.imported} shifts and replaced ${result.replaced} manual entries`
                : `Imported ${result.imported} shifts successfully`;
            this.showToast(message);

            // Prominent toast if header schema changed
            if (Array.isArray(result.warnings)) {
                const headerWarn = result.warnings.find(w => w.startsWith('CSV header schema changed'));
                if (headerWarn) this.showToast(headerWarn, 'warning');
            }
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

            // Prominent toast if header schema changed
            if (Array.isArray(result.warnings)) {
                const headerWarn = result.warnings.find(w => w.startsWith('CSV header schema changed'));
                if (headerWarn) this.showToast(headerWarn, 'warning');
            }
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

// Reset stored CSV header baseline
document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('reset-csv-headers');
    if (btn) {
        btn.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/import/reset-headers', { method: 'POST' });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || 'Failed to reset header baseline');
                if (typeof app !== 'undefined' && app.showToast) {
                    app.showToast(data.message || 'CSV header baseline reset');
                }
            } catch (e) {
                if (typeof app !== 'undefined' && app.showToast) {
                    app.showToast(e.message || 'Failed to reset header baseline', 'error');
                }
            }
        });
    }
});

App.prototype.exportData = async function(format) {
    const startDate = document.getElementById('export-start').value;
    const endDate = document.getElementById('export-end').value;
    
    if (!startDate || !endDate) {
        this.showToast('Please select date range', 'error');
        return;
    }
    
    try {
        const includeImported = document.getElementById('export-include-imported')?.checked ?? true;
        if (format === 'json') {
            // JSON export - get data and create download
            const data = await this.api('/api/export/json', {
                method: 'POST',
                body: JSON.stringify({ start_date: startDate, end_date: endDate, include_imported: includeImported })
            });
            
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `timesheet_${startDate}_${endDate}.json`;
            a.click();
            URL.revokeObjectURL(url);
        } else {
            // PDF and CSV export - fetch binary data
            const response = await fetch(`/api/export/${format}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ start_date: startDate, end_date: endDate, include_imported: includeImported })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Export failed');
            }
            
            // Get the blob from response
            const blob = await response.blob();
            
            // Create download link
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `timesheet_${startDate}_${endDate}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            this.showToast(`${format.toUpperCase()} exported successfully`);
        }
    } catch (error) {
        console.error('Export error:', error);
        this.showToast(error.message || `Failed to export ${format.toUpperCase()}`, 'error');
    }
};
