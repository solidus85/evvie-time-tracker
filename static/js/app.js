/* Main application logic and initialization */

class App {
    constructor() {
        this.currentView = 'dashboard';
        this.currentPeriod = null;
        this.employees = [];
        this.children = [];
        this.selectedChildId = null;
    }

    async init() {
        this.setupEventListeners();
        await this.loadInitialData();
        this.showView('dashboard');
    }

    setupEventListeners() {
        // Navigation buttons
        document.getElementById('btn-dashboard').addEventListener('click', () => this.showView('dashboard'));
        document.getElementById('btn-exclusions').addEventListener('click', () => this.showView('exclusions'));
        document.getElementById('btn-employees').addEventListener('click', () => this.showView('employees'));
        document.getElementById('btn-children').addEventListener('click', () => this.showView('children'));
        document.getElementById('btn-budget').addEventListener('click', () => this.showView('budget'));
        document.getElementById('btn-forecast').addEventListener('click', () => this.showView('forecast'));
        document.getElementById('btn-import').addEventListener('click', () => this.showView('import'));
        document.getElementById('btn-export').addEventListener('click', () => this.showView('export'));
        document.getElementById('btn-config').addEventListener('click', () => this.showView('config'));
        
        // Dashboard controls
        document.getElementById('prev-period').addEventListener('click', () => this.navigatePeriod(-1));
        document.getElementById('next-period').addEventListener('click', () => this.navigatePeriod(1));
        
        // Forms
        document.getElementById('add-employee').addEventListener('click', () => this.showEmployeeForm());
        document.getElementById('add-child').addEventListener('click', () => this.showChildForm());
        document.getElementById('add-hour-limit').addEventListener('click', () => this.showHourLimitForm());
        document.getElementById('add-exclusion').addEventListener('click', () => this.showExclusionForm());
        document.getElementById('bulk-add-exclusions').addEventListener('click', () => this.showBulkExclusionForm());
        
        // Import/Export
        document.getElementById('validate-csv').addEventListener('click', () => this.validateCSV());
        document.getElementById('import-csv').addEventListener('click', () => this.importCSV());
        document.getElementById('export-pdf').addEventListener('click', () => this.exportData('pdf'));
        document.getElementById('export-csv').addEventListener('click', () => this.exportData('csv'));
        document.getElementById('export-json').addEventListener('click', () => this.exportData('json'));
        
        // Config
        document.getElementById('configure-periods').addEventListener('click', () => this.configurePeriods());
        
        // Modal close
        document.querySelector('.close').addEventListener('click', () => this.closeModal());
        
        // Child filter dropdown
        document.getElementById('child-filter').addEventListener('change', (e) => {
            this.selectedChildId = parseInt(e.target.value);
            this.loadDashboard();
        });
    }

    async loadInitialData() {
        try {
            const [employees, children] = await Promise.all([
                this.api('/api/employees'),
                this.api('/api/children')
            ]);
            
            this.employees = employees;
            this.children = children;
            
            // Set default selected child if not set
            if (!this.selectedChildId && this.children.length > 0) {
                const activeChildren = this.children.filter(c => c.active);
                if (activeChildren.length > 0) {
                    this.selectedChildId = activeChildren[0].id;
                }
            }
            
            this.populateChildDropdown();
            
            if (this.currentView === 'dashboard') {
                await this.loadCurrentPeriod();
            }
        } catch (error) {
            console.error('Failed to load initial data:', error);
        }
    }

    async navigatePeriod(direction) {
        if (!this.currentPeriod) return;
        
        try {
            const period = await this.api(`/api/payroll/periods/navigate?period_id=${this.currentPeriod.id}&direction=${direction}`);
            this.currentPeriod = period;
            await this.loadDashboard();
        } catch (error) {
            this.showToast('No more periods in that direction', 'error');
        }
    }

    showView(viewName) {
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        
        document.getElementById(`${viewName}-view`).classList.add('active');
        document.getElementById(`btn-${viewName}`).classList.add('active');
        
        this.currentView = viewName;
        
        if (viewName === 'dashboard') this.loadDashboard();
        else if (viewName === 'exclusions') this.loadExclusions();
        else if (viewName === 'employees') this.loadEmployees();
        else if (viewName === 'children') this.loadChildren();
        else if (viewName === 'budget') this.loadBudget();
        else if (viewName === 'forecast') this.loadForecast();
        else if (viewName === 'export') this.loadExportView();
        else if (viewName === 'config') this.loadConfig();
    }

    loadExportView() {
        // Set date fields to current period if available
        if (this.currentPeriod) {
            const startInput = document.getElementById('export-start');
            const endInput = document.getElementById('export-end');
            
            if (startInput) {
                startInput.value = this.currentPeriod.start_date;
            }
            if (endInput) {
                endInput.value = this.currentPeriod.end_date;
            }
        }
    }

    async loadConfig() {
        const hourLimits = await this.api('/api/config/hour-limits');
        
        document.querySelector('#hour-limits-table tbody').innerHTML = hourLimits.map(limit => `
            <tr>
                <td>${limit.employee_name}</td>
                <td>${limit.child_name}</td>
                <td>${limit.max_hours_per_week}</td>
                <td>${limit.alert_threshold || 'N/A'}</td>
                <td>
                    <button onclick="app.editHourLimit(${limit.id})" class="btn-primary">Edit</button>
                    <button onclick="app.deleteHourLimit(${limit.id})" class="btn-secondary">Delete</button>
                </td>
            </tr>
        `).join('');
    }

    async api(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        const response = await fetch(url, { ...defaultOptions, ...options });
        const data = await response.json();
        
        if (!response.ok) {
            // Create an error with the full response data
            const error = new Error(data.message || data.error || 'Request failed');
            error.response = {
                status: response.status,
                data: data
            };
            throw error;
        }
        
        return data;
    }

    showModal(content) {
        document.getElementById('modal-body').innerHTML = content;
        document.getElementById('modal').classList.add('show');
    }

    closeModal() {
        document.getElementById('modal').classList.remove('show');
    }

    showToast(message, type = 'success') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = `toast show ${type}`;
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    formatDate(dateStr) {
        const date = new Date(dateStr + 'T00:00:00');
        return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    }
    
    formatDateWithYear(dateStr) {
        const date = new Date(dateStr + 'T00:00:00');
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric',
            year: 'numeric'
        });
    }

    formatTime(timeStr) {
        const [hours, minutes] = timeStr.split(':');
        const hour = parseInt(hours);
        const ampm = hour >= 12 ? 'PM' : 'AM';
        const displayHour = hour % 12 || 12;
        return `${displayHour}:${minutes} ${ampm}`;
    }
    
    formatDateTimeShort(dateStr, timeStr = null) {
        const date = new Date(dateStr + 'T00:00:00');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        let result = `${month}/${day}`;
        
        if (timeStr) {
            const [hours, minutes] = timeStr.split(':');
            const hour = parseInt(hours);
            const ampm = hour >= 12 ? 'pm' : 'am';
            const displayHour = hour % 12 || 12;
            result += ` ${String(displayHour).padStart(2, '0')}:${minutes} ${ampm}`;
        }
        
        return result;
    }

    calculateShiftHours(startTime, endTime) {
        const [startHours, startMinutes] = startTime.split(':').map(Number);
        const [endHours, endMinutes] = endTime.split(':').map(Number);
        
        const startTotalMinutes = startHours * 60 + startMinutes;
        const endTotalMinutes = endHours * 60 + endMinutes;
        
        const diffMinutes = endTotalMinutes - startTotalMinutes;
        const hours = Math.floor(diffMinutes / 60);
        const minutes = diffMinutes % 60;
        
        if (minutes === 0) {
            return `${hours}`;
        } else {
            return `${hours}:${minutes.toString().padStart(2, '0')}`;
        }
    }
    
    formatCurrency(amount) {
        // Format number as currency with commas
        if (amount === null || amount === undefined) {
            return '$0.00';
        }
        const num = parseFloat(amount);
        if (isNaN(num)) {
            return '$0.00';
        }
        return '$' + num.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }
}

// Initialize app
const app = new App();
document.addEventListener('DOMContentLoaded', () => app.init());