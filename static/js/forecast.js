/* Forecast management functions */

App.prototype.loadForecast = async function() {
    // Initialize tab switching
    this.setupForecastTabs();
    
    // Load initial tab data
    await this.loadAvailableHours();
    
    // Setup event listeners
    document.getElementById('refresh-forecast').addEventListener('click', () => this.loadAvailableHours());
    document.getElementById('analyze-patterns').addEventListener('click', () => this.analyzePatterns());
    document.getElementById('generate-projection').addEventListener('click', () => this.generateProjection());
    
    // Populate child dropdowns
    this.populateForecastChildDropdowns();
    
    // Set default dates for forecast
    this.setDefaultForecastDates();
};

App.prototype.setupForecastTabs = function() {
    const tabs = document.querySelectorAll('#forecast-view .tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', async (e) => {
            // Update active states
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('#forecast-view .tab-content').forEach(c => c.classList.remove('active'));
            
            e.target.classList.add('active');
            const tabName = e.target.dataset.tab;
            document.getElementById(`${tabName}-tab`).classList.add('active');
            
            // Load tab data if needed
            if (tabName === 'available-hours') {
                await this.loadAvailableHours();
            }
        });
    });
};

App.prototype.setDefaultForecastDates = async function() {
    try {
        const currentPeriod = await this.api('/api/payroll/periods/current');
        if (currentPeriod) {
            document.getElementById('forecast-start').value = currentPeriod.start_date;
            document.getElementById('forecast-end').value = currentPeriod.end_date;
        }
    } catch (error) {
        console.error('Failed to set default dates:', error);
    }
};

App.prototype.populateForecastChildDropdowns = function() {
    const activeChildren = this.children.filter(c => c.active);
    const childOptions = '<option value="">All Children</option>' +
        activeChildren.map(child => 
            `<option value="${child.id}">${child.name}</option>`
        ).join('');
    
    document.getElementById('pattern-child').innerHTML = childOptions;
    document.getElementById('projection-child').innerHTML = childOptions;
};


App.prototype.formatHoursWithCommas = function(hours) {
    // Truncate (round down) and add commas
    if (hours === null || hours === undefined) return '0';
    const truncated = Math.floor(hours);
    return truncated.toLocaleString('en-US');
};

App.prototype.formatDailyAverage = function(hours) {
    // Keep one decimal place for daily averages
    if (hours === null || hours === undefined) return '0.0';
    return hours.toFixed(1);
};

App.prototype.loadAvailableHours = async function() {
    const startDate = document.getElementById('forecast-start').value;
    const endDate = document.getElementById('forecast-end').value;
    
    if (!startDate || !endDate) {
        document.getElementById('available-hours-cards').innerHTML = 
            '<p>Please select a date range</p>';
        return;
    }
    
    try {
        // Get available hours for all children
        const result = await this.api('/api/forecast/available-hours/batch', {
            method: 'POST',
            body: JSON.stringify({
                period_start: startDate,
                period_end: endDate
            })
        });
        
        const cardsContainer = document.getElementById('available-hours-cards');
        
        if (!result.children || result.children.length === 0) {
            cardsContainer.innerHTML = '<p>No budget data available for this period</p>';
            return;
        }
        
        cardsContainer.innerHTML = `
            <div class="forecast-summary">
                <h3>Available Hours Summary</h3>
                <p>Period: ${this.formatDate(startDate)} to ${this.formatDate(endDate)}</p>
            </div>
            <div class="hours-grid">
                ${result.children.map(child => {
                    const utilizationClass = child.utilization_percent > 90 ? 'high' : 
                                           child.utilization_percent > 70 ? 'medium' : 'low';
                    
                    return `
                        <div class="hours-card ${utilizationClass}">
                            <h4>${child.child_name}</h4>
                            ${child.budget_hours === 0 ? `
                                <div style="font-size: 12px; color: #e74c3c; background: #ffe4e4; padding: 8px; margin: 10px 0; border-radius: 4px; text-align: center;">
                                    No spending report data available
                                </div>
                            ` : ''}
                            <div class="hours-metrics">
                                ${child.budget_period_start && child.budget_hours > 0 ? `
                                <div class="metric-row" style="font-size: 12px; color: #666; border-bottom: 2px solid #ddd; margin-bottom: 5px;">
                                    <span style="display: block; text-align: center; width: 100%;">
                                        Budget Period: ${this.formatDateWithYear(child.budget_period_start)} - ${this.formatDateWithYear(child.budget_period_end)}
                                    </span>
                                </div>
                                ` : ''}
                                <div class="metric-row">
                                    <span class="label">Budget:</span>
                                    <span class="value">${this.formatHoursWithCommas(child.budget_hours)} hrs</span>
                                </div>
                                <div class="metric-row">
                                    <span class="label">Used:</span>
                                    <span class="value">${this.formatHoursWithCommas(child.used_hours)} hrs</span>
                                </div>
                                <div class="metric-row">
                                    <span class="label">Available:</span>
                                    <span class="value ${child.available_hours < 0 ? 'negative' : ''}">
                                        ${this.formatHoursWithCommas(child.available_hours)} hrs
                                    </span>
                                </div>
                                <div class="metric-row">
                                    <span class="label">Payroll Days Remaining:</span>
                                    <span class="value">${child.days_remaining}</span>
                                </div>
                                <div class="metric-row">
                                    <span class="label">Daily Available:</span>
                                    <span class="value">${this.formatDailyAverage(child.average_daily_available)} hrs/day</span>
                                </div>
                                <div class="metric-row">
                                    <span class="label">Weekly Available:</span>
                                    <span class="value">${this.formatHoursWithCommas(child.weekly_available || 0)} hrs/week</span>
                                </div>
                                <div class="metric-row">
                                    <span class="label">Week Remaining:</span>
                                    <span class="value ${child.weekly_remaining < 5 ? 'negative' : ''}">
                                        ${this.formatHoursWithCommas(child.weekly_remaining || 0)} hrs
                                    </span>
                                </div>
                            </div>
                            <div class="utilization-bar">
                                <div class="utilization-fill" style="width: ${Math.min(child.utilization_percent || 0, 100)}%"></div>
                                <span class="utilization-text">${(child.utilization_percent || 0).toFixed(1)}%</span>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    } catch (error) {
        document.getElementById('available-hours-cards').innerHTML = 
            '<p>Failed to load available hours</p>';
        console.error('Available hours error:', error);
    }
};

App.prototype.analyzePatterns = async function() {
    const childId = document.getElementById('pattern-child').value;
    const lookbackDays = document.getElementById('lookback-days').value;
    
    if (!childId) {
        this.showToast('Please select a child', 'error');
        return;
    }
    
    try {
        const patterns = await this.api(
            `/api/forecast/patterns?child_id=${childId}&lookback_days=${lookbackDays}`
        );
        
        const display = document.getElementById('patterns-display');
        
        if (!patterns.weekly_patterns || patterns.weekly_patterns.length === 0) {
            display.innerHTML = '<p>No historical data available for analysis</p>';
            return;
        }
        
        display.innerHTML = `
            <div class="patterns-results">
                <h3>Historical Analysis</h3>
                <p>Analysis Period: Last ${patterns.analysis_period} days</p>
                <p>Total Hours Analyzed: ${patterns.total_hours_analyzed.toFixed(2)}</p>
                <p>Weekly Average: ${patterns.weekly_average_hours.toFixed(2)} hours</p>
                
                <h4 style="margin-top: 30px;">Weekly Pattern</h4>
                <div class="weekly-pattern">
                    ${patterns.weekly_patterns.map(day => `
                        <div class="day-pattern">
                            <span class="day-name">${day.day_of_week}</span>
                            <span class="day-stats">
                                ${day.shift_count} shifts, 
                                ${day.avg_hours ? day.avg_hours.toFixed(2) : '0'} hrs avg
                            </span>
                        </div>
                    `).join('')}
                </div>
                
                <h4>Employee Distribution</h4>
                <div class="employee-distribution">
                    ${patterns.employee_distribution.map(emp => {
                        const percentage = (emp.total_hours / patterns.total_hours_analyzed * 100).toFixed(1);
                        return `
                            <div class="employee-stat">
                                <span class="emp-name">${emp.friendly_name}</span>
                                <div class="emp-bar">
                                    <div class="emp-fill" style="width: ${percentage}%"></div>
                                </div>
                                <span class="emp-hours">${emp.total_hours.toFixed(2)} hrs (${percentage}%)</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    } catch (error) {
        this.showToast('Failed to analyze patterns', 'error');
        console.error('Pattern analysis error:', error);
    }
};

App.prototype.generateProjection = async function() {
    const childId = document.getElementById('projection-child').value;
    const projectionDays = document.getElementById('projection-days').value;
    
    if (!childId) {
        this.showToast('Please select a child', 'error');
        return;
    }
    
    try {
        const projection = await this.api(
            `/api/forecast/projections?child_id=${childId}&projection_days=${projectionDays}`
        );
        
        const display = document.getElementById('projections-display');
        
        // Determine confidence color
        const confidenceClass = projection.confidence === 'high' ? 'confidence-high' :
                              projection.confidence === 'medium' ? 'confidence-medium' : 'confidence-low';
        
        display.innerHTML = `
            <div class="projection-results">
                <h3>Hour Projection</h3>
                <div class="projection-summary">
                    <div class="projection-metric">
                        <span class="label">Projection Period:</span>
                        <span class="value">${projection.projection_days} days</span>
                    </div>
                    <div class="projection-metric">
                        <span class="label">Projected Hours:</span>
                        <span class="value">${projection.projected_hours} hrs</span>
                    </div>
                    <div class="projection-metric">
                        <span class="label">Weekly Average:</span>
                        <span class="value">${projection.weekly_projection} hrs/week</span>
                    </div>
                    <div class="projection-metric">
                        <span class="label">Confidence:</span>
                        <span class="value ${confidenceClass}">${projection.confidence.toUpperCase()}</span>
                    </div>
                    <div class="projection-metric">
                        <span class="label">Based On:</span>
                        <span class="value">${projection.based_on}</span>
                    </div>
                </div>
                
                ${projection.budget_comparison ? `
                    <div class="budget-comparison">
                        <h4>Budget Comparison</h4>
                        <div class="comparison-metrics">
                            <div class="comparison-metric">
                                <span class="label">Current Budget:</span>
                                <span class="value">${projection.budget_comparison.current_budget.toFixed(2)} hrs</span>
                            </div>
                            <div class="comparison-metric">
                                <span class="label">Projected Need:</span>
                                <span class="value">${projection.budget_comparison.projected_need.toFixed(2)} hrs</span>
                            </div>
                            <div class="comparison-metric">
                                <span class="label">Variance:</span>
                                <span class="value ${projection.budget_comparison.variance < 0 ? 'negative' : 'positive'}">
                                    ${projection.budget_comparison.variance > 0 ? '+' : ''}${projection.budget_comparison.variance.toFixed(2)} hrs
                                </span>
                            </div>
                            <div class="comparison-metric">
                                <span class="label">Budget Sufficient:</span>
                                <span class="value ${projection.budget_comparison.sufficient ? 'positive' : 'negative'}">
                                    ${projection.budget_comparison.sufficient ? 'YES' : 'NO'}
                                </span>
                            </div>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    } catch (error) {
        this.showToast('Failed to generate projection', 'error');
        console.error('Projection error:', error);
    }
};