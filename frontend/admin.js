const API_URL = "";
let currentView = 'dashboard';
let charts = {};

// State for pagination
const state = {
    users: { skip: 0, limit: 20 },
    jobs: { skip: 0, limit: 20 },
    audit: { skip: 0, limit: 50 },
    searchTimers: {}
};

// Check Auth on load
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
});

function checkAuth() {
    const token = localStorage.getItem('token');
    const role = localStorage.getItem('role');
    
    if (!token || role !== 'admin') {
        document.getElementById('auth-guard').classList.remove('hidden');
        return; // Halt execution
    }

    // Initialize UI
    const email = localStorage.getItem('email') || 'admin@recruitai.com';
    document.getElementById('admin-email').textContent = email;
    document.getElementById('admin-avatar').textContent = email.charAt(0).toUpperCase();

    // Set up navigation
    setupNavigation();
    
    // Load initial view
    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
}

function adminLogout() {
    localStorage.clear();
    window.location.href = '/';
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

async function apiCall(endpoint, options = {}) {
    const token = localStorage.getItem('token');
    const defaultHeaders = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
    
    const config = {
        ...options,
        headers: { ...defaultHeaders, ...options.headers }
    };
    
    try {
        const response = await fetch(`${API_URL}/admin${endpoint}`, config);
        
        if (response.status === 401 || response.status === 403) {
            adminLogout();
            throw new Error("Unauthorized");
        }
        
        if (response.status === 204) return null; // No content for deletes
        
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'API Error');
        return data;
    } catch (err) {
        showToast(err.message, 'error');
        throw err;
    }
}

// ================= NAVIGATION =================

function setupNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            if (window.innerWidth <= 768) toggleSidebar();
        });
    });
}

function handleHashChange() {
    const hash = window.location.hash.replace('#', '') || 'dashboard';
    const validViews = ['dashboard', 'users', 'jobs', 'health', 'audit'];
    
    if (validViews.includes(hash)) {
        switchView(hash);
    } else {
        window.location.hash = 'dashboard';
    }
}

function switchView(viewId) {
    currentView = viewId;
    
    // Update nav classes
    document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
    const activeNav = document.getElementById(`nav-${viewId}`);
    if(activeNav) activeNav.classList.add('active');
    
    // Update view visibility
    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
    document.getElementById(`view-${viewId}`).classList.remove('hidden');
    
    // Update topbar title
    const titles = {
        'dashboard': 'Dashboard Overview',
        'users': 'User Management',
        'jobs': 'Job Management',
        'health': 'System Health',
        'audit': 'Audit Logs'
    };
    document.getElementById('topbar-title').textContent = titles[viewId];
    
    // Load view data
    refreshCurrentView();
}

function refreshCurrentView() {
    const btn = document.getElementById('refresh-btn');
    btn.innerHTML = '🔄 Refreshing...';
    btn.disabled = true;
    
    const viewLoaders = {
        'dashboard': loadDashboard,
        'users': loadUsers,
        'jobs': loadJobs,
        'health': loadHealth,
        'audit': loadAudit
    };
    
    if (viewLoaders[currentView]) {
        viewLoaders[currentView]().finally(() => {
            btn.innerHTML = '🔄 Refresh';
            btn.disabled = false;
        });
    }
}

// ================= DASHBOARD VIEW =================

async function loadDashboard() {
    try {
        // Load KPI Summary
        const summary = await apiCall('/dashboard/summary');
        updateKpiCards(summary);
        
        // Load Charts
        const chartData = await apiCall('/dashboard/charts');
        renderCharts(chartData);
        
    } catch (e) {
        console.error("Dashboard load failed", e);
    }
}

function updateKpiCards(data) {
    document.getElementById('kpi-val-users').textContent = data.total_users;
    document.getElementById('kpi-val-verified').textContent = data.verified_users;
    document.getElementById('kpi-val-jobs').textContent = data.total_jobs;
    document.getElementById('kpi-val-apps').textContent = data.total_applications;
    document.getElementById('kpi-val-candidates').textContent = data.candidates;
    document.getElementById('kpi-val-new-today').textContent = data.new_users_today;
    
    // Remove skeleton
    document.querySelectorAll('.kpi-card').forEach(c => c.classList.remove('skeleton'));
}

function renderCharts(data) {
    if (typeof Chart === 'undefined') return;
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.color = '#a2a3b7';
    
    // 1. Registrations Chart
    const regCtx = document.getElementById('chart-registrations');
    if (charts.reg) charts.reg.destroy();
    
    const regLabels = data.user_registrations.map(d => d.date);
    const regData = data.user_registrations.map(d => d.count);
    
    charts.reg = new Chart(regCtx, {
        type: 'line',
        data: {
            labels: regLabels,
            datasets: [{
                label: 'New Users',
                data: regData,
                borderColor: '#3699ff',
                backgroundColor: 'rgba(54, 153, 255, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: { responsive: true, plugins: { legend: { display: false } } }
    });
    
    // 2. Roles Chart
    const roleCtx = document.getElementById('chart-roles');
    if (charts.role) charts.role.destroy();
    
    charts.role = new Chart(roleCtx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(data.role_distribution),
            datasets: [{
                data: Object.values(data.role_distribution),
                backgroundColor: ['#3699ff', '#1bc5bd', '#ffa800', '#f64e60']
            }]
        },
        options: { responsive: true, cutout: '70%' }
    });
    
    // 3. Job Sources Chart
    const sourceCtx = document.getElementById('chart-sources');
    if (charts.source) charts.source.destroy();
    
    charts.source = new Chart(sourceCtx, {
        type: 'bar',
        data: {
            labels: Object.keys(data.jobs_by_source),
            datasets: [{
                label: 'Jobs',
                data: Object.values(data.jobs_by_source),
                backgroundColor: '#1bc5bd',
                borderRadius: 4
            }]
        },
        options: { responsive: true, plugins: { legend: { display: false } } }
    });
    
    // 4. Verification Chart
    const verCtx = document.getElementById('chart-verification');
    if (charts.ver) charts.ver.destroy();
    
    charts.ver = new Chart(verCtx, {
        type: 'pie',
        data: {
            labels: ['Verified', 'Unverified'],
            datasets: [{
                data: [data.verification_distribution.verified, data.verification_distribution.unverified],
                backgroundColor: ['#1bc5bd', '#f64e60']
            }]
        },
        options: { responsive: true }
    });
}

// ================= USERS VIEW =================

function debounceUserSearch() {
    clearTimeout(state.searchTimers.users);
    state.searchTimers.users = setTimeout(() => {
        state.users.skip = 0;
        loadUsers();
    }, 500);
}

async function loadUsers() {
    const loader = document.getElementById('users-loader');
    const tbody = document.getElementById('users-tbody');
    const empty = document.getElementById('users-empty');
    
    loader.classList.remove('hidden');
    
    try {
        const search = document.getElementById('user-search').value;
        const role = document.getElementById('user-role-filter').value;
        const verified = document.getElementById('user-verified-filter').value;
        
        let query = `?skip=${state.users.skip}&limit=${state.users.limit}`;
        if (search) query += `&search=${encodeURIComponent(search)}`;
        if (role) query += `&role=${role}`;
        if (verified) query += `&is_verified=${verified}`;
        
        const data = await apiCall(`/users${query}`);
        
        tbody.innerHTML = '';
        if (data.users.length === 0) {
            empty.classList.remove('hidden');
        } else {
            empty.classList.add('hidden');
            data.users.forEach(u => {
                const tr = document.createElement('tr');
                const vBadge = u.is_verified ? '<span class="badge badge-success">Verified</span>' : '<span class="badge badge-warning">Pending</span>';
                const date = u.created_at ? new Date(u.created_at).toLocaleDateString() : 'Unknown';
                
                tr.innerHTML = `
                    <td>#${u.id}</td>
                    <td>${u.email}</td>
                    <td><span class="badge badge-secondary">${u.role}</span></td>
                    <td>${vBadge}</td>
                    <td>${date}</td>
                    <td class="actions-cell">
                        <button class="btn btn-sm btn-ghost" onclick="viewUserDetail(${u.id})">View</button>
                        <button class="btn btn-sm btn-primary" onclick="toggleUserVerification(${u.id})">Toggle Ver</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteUser(${u.id})">Del</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }
        
        renderPagination('users-pagination', data.total, state.users.skip, state.users.limit, (newSkip) => {
            state.users.skip = newSkip;
            loadUsers();
        });
        
    } catch (e) {
        console.error(e);
    } finally {
        loader.classList.add('hidden');
    }
}

async function viewUserDetail(id) {
    try {
        const data = await apiCall(`/users/${id}`);
        document.getElementById('modal-user-title').textContent = `User #${id} Detail`;
        
        const vBadge = data.is_verified ? '<span class="badge badge-success">Verified</span>' : '<span class="badge badge-warning">Unverified</span>';
        
        document.getElementById('modal-user-body').innerHTML = `
            <div class="detail-row"><span class="detail-label">Email</span><span class="detail-value">${data.email}</span></div>
            <div class="detail-row"><span class="detail-label">Role</span><span class="detail-value badge badge-secondary">${data.role}</span></div>
            <div class="detail-row"><span class="detail-label">Status</span><span class="detail-value">${vBadge}</span></div>
            <div class="detail-row"><span class="detail-label">Has Profile</span><span class="detail-value">${data.has_candidate_profile ? 'Yes' : 'No'}</span></div>
            <div class="detail-row"><span class="detail-label">Applications</span><span class="detail-value">${data.application_count}</span></div>
            <div class="detail-row"><span class="detail-label">Joined</span><span class="detail-value">${data.created_at ? new Date(data.created_at).toLocaleString() : 'N/A'}</span></div>
        `;
        
        document.getElementById('user-modal-overlay').classList.remove('hidden');
    } catch (e) {
        console.error(e);
    }
}

function closeUserModal() {
    document.getElementById('user-modal-overlay').classList.add('hidden');
}

async function toggleUserVerification(id) {
    if(!confirm('Toggle verification status for this user?')) return;
    try {
        await apiCall(`/users/${id}/toggle-verification`, { method: 'POST' });
        showToast('User verification toggled');
        loadUsers();
    } catch(e) {}
}

async function deleteUser(id) {
    if(!confirm('WARNING: Permanently delete this user? This cannot be undone.')) return;
    try {
        await apiCall(`/users/${id}`, { method: 'DELETE' });
        showToast('User deleted successfully');
        loadUsers();
    } catch(e) {}
}

// ================= JOBS VIEW =================

function debounceJobSearch() {
    clearTimeout(state.searchTimers.jobs);
    state.searchTimers.jobs = setTimeout(() => {
        state.jobs.skip = 0;
        loadJobs();
    }, 500);
}

async function loadJobs() {
    const loader = document.getElementById('jobs-loader');
    const tbody = document.getElementById('jobs-tbody');
    const empty = document.getElementById('jobs-empty');
    
    loader.classList.remove('hidden');
    
    try {
        // Load stats first
        const stats = await apiCall('/jobs/stats');
        document.getElementById('stat-total-jobs').textContent = `Total: ${stats.total_jobs}`;
        document.getElementById('stat-internal-jobs').textContent = `Internal: ${stats.internal_jobs}`;
        document.getElementById('stat-agg-jobs').textContent = `Aggregated: ${stats.aggregated_jobs}`;
        
        // Load table data
        const search = document.getElementById('job-search').value;
        const source = document.getElementById('job-source-filter').value;
        
        let query = `?skip=${state.jobs.skip}&limit=${state.jobs.limit}`;
        if (search) query += `&search=${encodeURIComponent(search)}`;
        if (source) query += `&source=${source}`;
        
        const data = await apiCall(`/jobs${query}`);
        
        tbody.innerHTML = '';
        if (data.jobs.length === 0) {
            empty.classList.remove('hidden');
        } else {
            empty.classList.add('hidden');
            data.jobs.forEach(j => {
                const tr = document.createElement('tr');
                const srcBadgeClass = j.source === 'internal' ? 'badge-primary' : 'badge-success';
                const date = new Date(j.created_at).toLocaleDateString();
                
                tr.innerHTML = `
                    <td>#${j.id}</td>
                    <td><strong>${j.title}</strong></td>
                    <td>${j.company}</td>
                    <td>${j.location || 'Any'}</td>
                    <td><span class="badge ${srcBadgeClass}">${j.source}</span></td>
                    <td>${j.employment_type || '-'}</td>
                    <td>${date}</td>
                    <td class="actions-cell">
                        <button class="btn btn-sm btn-danger" onclick="deleteJob(${j.id})">Del</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }
        
        renderPagination('jobs-pagination', data.total, state.jobs.skip, state.jobs.limit, (newSkip) => {
            state.jobs.skip = newSkip;
            loadJobs();
        });
        
    } catch (e) {
        console.error(e);
    } finally {
        loader.classList.add('hidden');
    }
}

async function deleteJob(id) {
    if(!confirm('Permanently delete this job?')) return;
    try {
        await apiCall(`/jobs/${id}`, { method: 'DELETE' });
        showToast('Job deleted');
        loadJobs();
    } catch(e) {}
}

// ================= SYSTEM HEALTH =================

async function loadHealth() {
    try {
        const data = await apiCall('/system/health');
        
        // Update Overall Badge
        const badge = document.getElementById('health-badge');
        badge.className = `health-badge ${data.overall_status}`;
        const icons = { 'healthy': '✅ System Healthy', 'warning': '⚠️ Degraded', 'unhealthy': '❌ Critical Failure' };
        badge.innerHTML = icons[data.overall_status];
        
        // Render Cards
        const grid = document.getElementById('health-grid');
        grid.innerHTML = '';
        
        data.services.forEach(s => {
            const card = document.createElement('div');
            card.className = `health-card ${s.status}`;
            
            const sIcons = { 'healthy': '🟢', 'warning': '🟡', 'unhealthy': '🔴', 'unknown': '⚪' };
            const timeStr = new Date(s.last_checked).toLocaleTimeString();
            const ms = s.response_ms ? `${s.response_ms}ms` : '-';
            
            card.innerHTML = `
                <div class="health-icon">${sIcons[s.status]}</div>
                <div class="health-info">
                    <div class="health-name">${s.name}</div>
                    <div class="health-msg">${s.message}</div>
                    <div class="health-meta">
                        <span>Resp: ${ms}</span>
                        <span>Chk: ${timeStr}</span>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });
        
    } catch (e) {
        console.error(e);
    }
}

// ================= AUDIT LOGS =================

async function loadAudit() {
    const loader = document.getElementById('audit-loader');
    const tbody = document.getElementById('audit-tbody');
    const empty = document.getElementById('audit-empty');
    
    loader.classList.remove('hidden');
    
    try {
        const data = await apiCall(`/audit-logs?skip=${state.audit.skip}&limit=${state.audit.limit}`);
        
        tbody.innerHTML = '';
        if (data.logs.length === 0) {
            empty.classList.remove('hidden');
        } else {
            empty.classList.add('hidden');
            data.logs.forEach(l => {
                const tr = document.createElement('tr');
                const date = new Date(l.created_at).toLocaleString();
                const sBadge = l.status === 'success' ? 'success' : 'danger';
                
                tr.innerHTML = `
                    <td><small>${date}</small></td>
                    <td>${l.admin_email} (ID:${l.admin_user_id})</td>
                    <td><strong>${l.action}</strong></td>
                    <td>${l.resource_type || '-'}:${l.resource_id || '-'}</td>
                    <td>${l.description || '-'}</td>
                    <td><span class="badge badge-${sBadge}">${l.status}</span></td>
                `;
                tbody.appendChild(tr);
            });
        }
        
        renderPagination('audit-pagination', data.total, state.audit.skip, state.audit.limit, (newSkip) => {
            state.audit.skip = newSkip;
            loadAudit();
        });
        
    } catch (e) {
        console.error(e);
    } finally {
        loader.classList.add('hidden');
    }
}

// ================= UTILS =================

function renderPagination(containerId, total, skip, limit, onPageClick) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    const totalPages = Math.ceil(total / limit);
    if (totalPages <= 1) return;
    
    const currentPage = Math.floor(skip / limit) + 1;
    
    // Prev Button
    const prev = document.createElement('button');
    prev.className = 'page-btn';
    prev.textContent = '«';
    prev.disabled = currentPage === 1;
    prev.onclick = () => onPageClick(skip - limit);
    container.appendChild(prev);
    
    // Pages
    for (let i = 1; i <= totalPages; i++) {
        // Simple logic for large page counts (just show 1,2,3,4,5 or surround current)
        if (totalPages > 7) {
            if (i !== 1 && i !== totalPages && Math.abs(i - currentPage) > 2) {
                if (i === 2 || i === totalPages - 1) {
                    const dots = document.createElement('span');
                    dots.textContent = '...';
                    dots.style.padding = '0 5px';
                    container.appendChild(dots);
                }
                continue;
            }
        }
        
        const btn = document.createElement('button');
        btn.className = `page-btn ${i === currentPage ? 'active' : ''}`;
        btn.textContent = i;
        btn.onclick = () => onPageClick((i - 1) * limit);
        container.appendChild(btn);
    }
    
    // Next Button
    const next = document.createElement('button');
    next.className = 'page-btn';
    next.textContent = '»';
    next.disabled = currentPage === totalPages;
    next.onclick = () => onPageClick(skip + limit);
    container.appendChild(next);
}
