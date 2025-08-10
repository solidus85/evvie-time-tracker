/* Children management functions */

App.prototype.loadChildren = async function() {
    const children = await this.api('/api/children');
    this.children = children;
    document.querySelector('#children-table tbody').innerHTML = children.map(child => `
        <tr>
            <td>${child.name}</td>
            <td>${child.code}</td>
            <td>${child.active ? 'Active' : 'Inactive'}</td>
            <td>
                <button onclick="app.editChild(${child.id})" class="btn-primary">Edit</button>
                <button onclick="app.deleteChild(${child.id})" class="btn-secondary">Delete</button>
            </td>
        </tr>
    `).join('');
};