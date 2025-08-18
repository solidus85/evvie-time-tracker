/* Employee management functions */

App.prototype.loadEmployees = async function() {
    const employees = await this.api('/api/employees');
    this.employees = employees;
    document.querySelector('#employees-table tbody').innerHTML = employees.map(emp => `
        <tr>
            <td>${emp.friendly_name}</td>
            <td>${emp.system_name}</td>
            <td>${emp.active ? 'Active' : 'Inactive'}</td>
            <td>${emp.hidden ? 'Yes' : 'No'}</td>
            <td>
                <button onclick="app.editEmployee(${emp.id})" class="btn-primary">Edit</button>
                <button onclick="app.deleteEmployee(${emp.id})" class="btn-secondary">Delete</button>
            </td>
        </tr>
    `).join('');
};