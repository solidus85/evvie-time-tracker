/* Overlaps management module */

class OverlapsManager {
    constructor() {
        this.overlaps = [];
        this.currentPage = 1;
        this.pageSize = 10;
        this.totalOverlaps = 0;
    }

    async init() {
        this.setupEventListeners();
        await this.loadOverlaps();
    }

    setupEventListeners() {
        document.getElementById('overlaps-prev-page').addEventListener('click', () => this.previousPage());
        document.getElementById('overlaps-next-page').addEventListener('click', () => this.nextPage());
        document.getElementById('overlaps-page-size').addEventListener('change', (e) => {
            this.pageSize = e.target.value === 'all' ? 'all' : parseInt(e.target.value);
            this.currentPage = 1;
            this.renderOverlaps();
        });
    }

    async loadOverlaps() {
        try {
            const response = await fetch('/api/shifts/overlaps');
            if (response.ok) {
                this.overlaps = await response.json();
                this.totalOverlaps = this.overlaps.length;
                this.renderOverlaps();
            } else {
                console.error('Failed to load overlaps');
                this.showError('Failed to load overlapping shifts');
            }
        } catch (error) {
            console.error('Error loading overlaps:', error);
            this.showError('Error loading overlapping shifts');
        }
    }

    renderOverlaps() {
        const tbody = document.getElementById('overlaps-tbody');
        
        if (this.overlaps.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="no-data">No overlapping shifts found</td></tr>';
            this.updatePaginationControls();
            return;
        }

        // Calculate pagination
        const startIndex = this.pageSize === 'all' ? 0 : (this.currentPage - 1) * this.pageSize;
        const endIndex = this.pageSize === 'all' ? this.overlaps.length : Math.min(startIndex + this.pageSize, this.overlaps.length);
        const paginatedOverlaps = this.overlaps.slice(startIndex, endIndex);

        tbody.innerHTML = '';
        paginatedOverlaps.forEach(overlap => {
            const row = this.createOverlapRow(overlap);
            tbody.appendChild(row);
        });

        this.updatePaginationControls();
    }

    createOverlapRow(overlap) {
        const row = document.createElement('tr');
        
        // Determine the type badge and conflict description
        const typeBadge = overlap.overlap_type === 'employee' 
            ? '<span class="badge badge-employee">Employee</span>'
            : '<span class="badge badge-child">Child</span>';
            
        const conflictDesc = overlap.overlap_type === 'employee'
            ? `${overlap.employee_name}`
            : `${overlap.child_name}`;
            
        const shift1Desc = `${this.formatTime(overlap.shift1_start)} - ${this.formatTime(overlap.shift1_end)}<br>
                           <small>${overlap.shift1_employee} / ${overlap.shift1_child}</small>`;
                           
        const shift2Desc = `${this.formatTime(overlap.shift2_start)} - ${this.formatTime(overlap.shift2_end)}<br>
                           <small>${overlap.shift2_employee} / ${overlap.shift2_child}</small>`;
        
        row.innerHTML = `
            <td>${this.formatDate(overlap.date)}</td>
            <td>${typeBadge}</td>
            <td><strong>${conflictDesc}</strong></td>
            <td>${shift1Desc}</td>
            <td>${shift2Desc}</td>
            <td class="overlap-duration">${this.calculateOverlapDuration(overlap)} hrs</td>
            <td>
                <button class="btn-small btn-danger" onclick="overlapsManager.resolveOverlap(${overlap.shift1_id}, ${overlap.shift2_id}, '${overlap.overlap_type}')">
                    Resolve
                </button>
            </td>
        `;
        return row;
    }

    calculateOverlapDuration(overlap) {
        const start1 = new Date(`${overlap.date} ${overlap.shift1_start}`);
        const end1 = new Date(`${overlap.date} ${overlap.shift1_end}`);
        const start2 = new Date(`${overlap.date} ${overlap.shift2_start}`);
        const end2 = new Date(`${overlap.date} ${overlap.shift2_end}`);

        const overlapStart = new Date(Math.max(start1, start2));
        const overlapEnd = new Date(Math.min(end1, end2));
        
        const duration = (overlapEnd - overlapStart) / (1000 * 60 * 60);
        return duration.toFixed(2);
    }

    async resolveOverlap(shift1Id, shift2Id, overlapType) {
        const typeText = overlapType === 'employee' 
            ? 'employee is scheduled for overlapping times'
            : 'child has multiple employees scheduled at the same time';
            
        if (!confirm(`This ${typeText}. How would you like to resolve this conflict?`)) {
            return;
        }

        // Show resolution options
        const resolution = prompt('How would you like to resolve this overlap?\n1 - Delete first shift\n2 - Delete second shift\n3 - Adjust times manually');
        
        if (resolution === '1') {
            await this.deleteShift(shift1Id);
        } else if (resolution === '2') {
            await this.deleteShift(shift2Id);
        } else if (resolution === '3') {
            alert('Please edit the shifts from the Dashboard view');
        }
        
        await this.loadOverlaps();
    }

    async deleteShift(shiftId) {
        try {
            const response = await fetch(`/api/shifts/${shiftId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Failed to delete shift');
            }

            this.showSuccess('Shift deleted successfully');
        } catch (error) {
            console.error('Error deleting shift:', error);
            this.showError('Failed to delete shift');
        }
    }

    updatePaginationControls() {
        const prevBtn = document.getElementById('overlaps-prev-page');
        const nextBtn = document.getElementById('overlaps-next-page');
        const pageInfo = document.getElementById('overlaps-page-info');

        if (this.pageSize === 'all') {
            prevBtn.disabled = true;
            nextBtn.disabled = true;
            pageInfo.textContent = `All ${this.totalOverlaps} overlaps`;
        } else {
            const totalPages = Math.ceil(this.totalOverlaps / this.pageSize);
            prevBtn.disabled = this.currentPage <= 1;
            nextBtn.disabled = this.currentPage >= totalPages;
            pageInfo.textContent = `Page ${this.currentPage} of ${totalPages}`;
        }
    }

    previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.renderOverlaps();
        }
    }

    nextPage() {
        const totalPages = Math.ceil(this.totalOverlaps / this.pageSize);
        if (this.currentPage < totalPages) {
            this.currentPage++;
            this.renderOverlaps();
        }
    }

    formatDate(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleDateString();
    }

    formatTime(timeStr) {
        if (!timeStr) return '';
        const [hours, minutes] = timeStr.split(':');
        const hour = parseInt(hours);
        const ampm = hour >= 12 ? 'PM' : 'AM';
        const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
        return `${displayHour}:${minutes} ${ampm}`;
    }

    showSuccess(message) {
        // You can implement a toast notification here
        console.log('Success:', message);
    }

    showError(message) {
        // You can implement a toast notification here
        console.error('Error:', message);
    }
}

// Add loadOverlaps method to App prototype
App.prototype.loadOverlaps = async function() {
    if (!window.overlapsManager) {
        window.overlapsManager = new OverlapsManager();
        await window.overlapsManager.init();
    } else {
        await window.overlapsManager.loadOverlaps();
    }
};