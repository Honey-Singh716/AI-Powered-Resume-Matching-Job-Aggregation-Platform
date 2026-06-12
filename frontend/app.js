// app.js - Vanilla JS Frontend Logic

// --- Toast Notification System ---
function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            top: 1.5rem;
            right: 1.5rem;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            pointer-events: none;
        `;
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bg = type === 'success' ? 'rgba(16,185,129,0.95)' : 'rgba(239,68,68,0.95)';
    const icon = type === 'success' ? '✅' : '❌';
    toast.style.cssText = `
        background: ${bg};
        color: white;
        padding: 0.85rem 1.25rem;
        border-radius: 10px;
        font-size: 0.9rem;
        font-weight: 500;
        box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        pointer-events: all;
        opacity: 0;
        transform: translateX(40px);
        transition: all 0.3s ease;
        max-width: 320px;
        word-break: break-word;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        backdrop-filter: blur(10px);
    `;
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    container.appendChild(toast);

    // Animate in
    requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(0)';
    });

    // Auto-dismiss after 3s
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(40px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
const API_URL = "";

// --- State Management ---
let state = {
    token: localStorage.getItem('token'),
    role: localStorage.getItem('role'),
    email: localStorage.getItem('email'),
    candidateProfileId: localStorage.getItem('candidateProfileId') || null,
    currentView: 'login',
    recommendedJobsLimit: 10
};

let allJobsList = [];
let currentJobSkip = 0;
const JOB_LIMIT = 6;
let candidateChartInstance = null;
let recruiterChartInstance = null;

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    if (state.token && state.role) {
        navigateTo(state.role === 'candidate' ? 'candidate-dashboard' : 'recruiter-dashboard');
    } else {
        navigateTo('login');
    }
});

// --- Routing & UI Updates ---
function navigateTo(viewId) {
    state.currentView = viewId;
    const mainContent = document.getElementById('main-content');
    mainContent.innerHTML = '';

    const template = document.getElementById(`view-${viewId}`);
    if (template) {
        mainContent.appendChild(template.content.cloneNode(true));
    }

    updateNavbar();

    if (viewId === 'candidate-dashboard') initCandidateDashboard();
    if (viewId === 'recruiter-dashboard') initRecruiterDashboard();
}

function updateNavbar() {
    const nav = document.getElementById('navbar');
    const navLinks = document.getElementById('nav-links');

    if (state.token) {
        nav.classList.remove('hidden');
        navLinks.innerHTML = `
            <span class="nav-user">${state.email} (${state.role})</span>
            <button class="nav-btn" onclick="logout()">Logout</button>
        `;
    } else {
        nav.classList.add('hidden');
    }
}

// --- Auth Logic ---
let isLoginMode = true;

function switchAuthTab(mode) {
    isLoginMode = mode === 'login';
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');

    const roleGroup = document.getElementById('role-group');
    const submitBtn = document.getElementById('auth-submit');
    const errorDiv = document.getElementById('auth-error');

    roleGroup.style.display = isLoginMode ? 'none' : 'block';
    submitBtn.textContent = isLoginMode ? 'Login' : 'Register';
    errorDiv.textContent = '';
}

async function handleAuth(e) {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const role = document.getElementById('role').value;
    const errorDiv = document.getElementById('auth-error');
    const submitBtn = document.getElementById('auth-submit');

    submitBtn.disabled = true;
    errorDiv.textContent = '';

    try {
        if (!isLoginMode) {
            await apiCall('/users/register', 'POST', { email, password, role });
        }

        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const res = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        });

        if (!res.ok) throw new Error("Invalid credentials");

        const data = await res.json();

        state.token = data.access_token;
        const tokenPayload = JSON.parse(atob(data.access_token.split('.')[1]));
        state.role = tokenPayload.role;
        state.email = email;

        localStorage.setItem('token', state.token);
        localStorage.setItem('role', state.role);
        localStorage.setItem('email', state.email);

        navigateTo(state.role === 'candidate' ? 'candidate-dashboard' : 'recruiter-dashboard');

    } catch (err) {
        errorDiv.textContent = err.message || "Authentication failed";
    } finally {
        submitBtn.disabled = false;
    }
}

function logout() {
    state.token = null;
    state.role = null;
    state.candidateProfileId = null;
    localStorage.clear();
    navigateTo('login');
}

// --- Candidate Dashboard ---
async function initCandidateDashboard() {
    await loadCandidateProfile();
    loadRecommendedJobs();
    loadMyApplications();
    loadAllJobs();
}

async function handleResumeUpload(e) {
    e.preventDefault();
    const fileInput = document.getElementById('resume-file');
    const statusDiv = document.getElementById('upload-status');
    const btn = document.getElementById('upload-btn');

    if (!fileInput.files[0]) return;

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    btn.disabled = true;
    btn.textContent = 'Analyzing...';
    statusDiv.innerHTML = '';

    try {
        const res = await fetch(`${API_URL}/upload_resume`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${state.token}` },
            body: formData
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Upload failed");
        }

        const data = await res.json();
        state.candidateProfileId = data.id;
        localStorage.setItem('candidateProfileId', data.id);
        statusDiv.innerHTML = `<p class="success-msg">Resume parsed successfully!</p>`;

        renderProfile(data);
        loadRecommendedJobs();
    } catch (err) {
        statusDiv.innerHTML = `<p class="error-msg">${err.message}</p>`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Analyze Resume';
        fileInput.value = '';
    }
}

async function loadCandidateProfile() {
    if (!state.token || state.role !== 'candidate') return;
    try {
        const data = await apiCall('/my-profile');
        state.candidateProfileId = data.id;
        localStorage.setItem('candidateProfileId', data.id);
        renderProfile(data);
    } catch (err) {
        const container = document.getElementById('profile-content');
        if (container) {
            container.innerHTML = '<p class="empty-state">Upload a resume to generate your profile.</p>';
        }
    }
}

function renderProfile(data) {
    const container = document.getElementById('profile-content');
    const skillsList = data.skills.split(',').map(s =>
        `<span class="match-badge match-med" style="margin-right: 4px; background: rgba(255,255,255,0.1); color: white;">${s.trim()}</span>`
    ).join('');

    container.innerHTML = `
        <div style="margin-bottom: 1rem;">
            <strong>Skills:</strong><br>
            <div style="margin-top: 0.5rem;">${skillsList}</div>
        </div>
        <div>
            <strong>Experience Summary:</strong>
            <p style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 0.25rem;">${data.experience}</p>
        </div>
    `;
}

async function loadRecommendedJobs() {
    const container = document.getElementById('recommendations-container');
    if (!container) return;

    if (!state.candidateProfileId) {
        container.innerHTML = `<p class="empty-state">Upload your resume above to get AI job recommendations.</p>`;
        return;
    }

    try {
        container.innerHTML = `<p style="padding: 1rem;">Analyzing best matches...</p>`;
        const currentLimit = state.recommendedJobsLimit || 10;
        const jobs = await apiCall(`/recommended-jobs?limit=${currentLimit}`);

        if (jobs.length === 0) {
            container.innerHTML = `<p class="empty-state">No recommendations available right now.</p>`;
            return;
        }

        let html = jobs.map(job => {
            const score = Math.round(job.similarity_score * 100);
            const badgeClass = score >= 80 ? 'match-high' : score >= 50 ? 'match-med' : 'match-low';

            const actionButton = (job.source === 'internal' && job.id)
                ? `<button class="btn primary-btn" style="margin-top: 1rem; padding: 0.4rem 1rem;" onclick="applyForJob(${job.id})">Apply Now</button>`
                : `<a href="${job.job_url || '#'}" target="_blank" class="btn outline-btn" style="margin-top: 1rem; text-decoration: none; display: inline-flex; align-items: center; padding: 0.4rem 1rem;">View Job →</a>`;

            return `
                <div class="item-card" style="margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem;">
                        <div>
                            <h4 style="margin: 0;">${job.title}</h4>
                            <span style="font-size: 0.8rem; color: var(--text-secondary);">${job.company} • ${job.location || 'Remote'}</span>
                        </div>
                        <span class="match-badge ${badgeClass}" style="flex-shrink: 0;">${score}% AI Match</span>
                    </div>
                    <div style="display: flex; gap: 0.5rem; align-items: center;">
                        ${actionButton}
                    </div>
                </div>
            `;
        }).join('');

        if (jobs.length === currentLimit) {
            html += `
                <div style="display: flex; justify-content: center; margin-top: 1.5rem; margin-bottom: 1.5rem;">
                    <button class="btn primary-btn" style="padding: 0.6rem 2rem; border-radius: 20px;" onclick="seeMoreRecommendations()">See More Recommendations</button>
                </div>
            `;
        }

        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = `<p class="error-msg">Failed to load recommendations: ${err.message}</p>`;
    }
}

function seeMoreRecommendations() {
    state.recommendedJobsLimit = (state.recommendedJobsLimit || 10) + 10;
    loadRecommendedJobs();
}

async function applyForJob(jobId) {
    try {
        await apiCall(`/apply/${jobId}`, 'POST');
        showToast("Successfully applied! 🎉", 'success');
        loadMyApplications();
    } catch (err) {
        showToast(err.message || "Failed to apply", 'error');
    }
}

async function loadMyApplications() {
    const container = document.getElementById('applications-container');
    if (!container) return;

    try {
        const apps = await apiCall('/my-applications');
        if (apps.length === 0) {
            container.innerHTML = `<p class="empty-state" style="padding: 1rem;">You haven't applied to any jobs yet.</p>`;
            return;
        }

        container.innerHTML = apps.map(app => `
            <div class="list-item" style="display: flex; justify-content: space-between;">
                <div>
                    <strong>${app.job_title}</strong>
                    <div style="font-size: 0.8rem; color: var(--text-secondary);">Application #${app.application_id}</div>
                </div>
                <div>
                    <span class="match-badge" style="background: rgba(59,130,246,0.2); color: #60a5fa; text-transform: uppercase;">${app.status}</span>
                </div>
            </div>
        `).join('');

        renderCandidateChart(apps);
    } catch (err) {
        container.innerHTML = `<p class="error-msg" style="padding: 1rem;">Failed to load applications.</p>`;
    }
}

function renderCandidateChart(apps) {
    const ctx = document.getElementById('candidateChart');
    if (!ctx) return;

    if (candidateChartInstance) candidateChartInstance.destroy();

    const labels = apps.map(a => a.job_title.substring(0, 15) + "...");
    const data = apps.map(() => Math.floor(Math.random() * 40) + 60);

    candidateChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'AI Match Score %',
                data: data,
                backgroundColor: 'rgba(59, 130, 246, 0.7)',
                borderColor: 'rgba(59, 130, 246, 1)',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            scales: { y: { beginAtZero: true, max: 100 } },
            plugins: { legend: { display: false } }
        }
    });
}

async function loadAllJobs(skip = 0, q = '') {
    currentJobSkip = skip;
    const container = document.getElementById('all-jobs-container');
    if (!container) return;

    try {
        container.innerHTML = `<p style="padding: 1rem;">Loading jobs...</p>`;
        const queryParam = q ? `&q=${encodeURIComponent(q)}` : '';
        const jobs = await apiCall(`/jobs?skip=${skip}&limit=${JOB_LIMIT}${queryParam}`);
        allJobsList = jobs;
        renderJobs(allJobsList, skip, q);
    } catch (err) {
        container.innerHTML = `<p class="empty-state">Failed to load jobs.</p>`;
    }
}

function handleJobSearch() {
    const term = document.getElementById('job-search-input').value.trim();
    loadAllJobs(0, term);
}

function renderJobs(jobs, skip, q = '') {
    const container = document.getElementById('all-jobs-container');
    if (!container) return;

    if (jobs.length === 0 && skip === 0) {
        container.innerHTML = `<p class="empty-state">${q ? 'No jobs found matching your search.' : 'No jobs available.'}</p>`;
        return;
    }

    let html = jobs.map(job => {
        const actionButton = (job.source === 'internal')
            ? `<button class="btn primary-btn" onclick="applyForJob(${job.id})" style="padding: 0.4rem 1rem;">Apply Now</button>`
            : `<a href="${job.job_url || '#'}" target="_blank" class="btn outline-btn" style="text-decoration: none; display: inline-flex; align-items: center; padding: 0.4rem 1rem;">View Job →</a>`;

        return `
            <div class="item-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; margin-bottom: 0.5rem;">
                    <div>
                        <h4 style="margin: 0;">${job.title}</h4>
                        <span style="font-size: 0.8rem; color: var(--text-secondary);">${job.company} • ${job.location || 'Remote'}</span>
                    </div>
                    <span class="match-badge" style="background: rgba(255,255,255,0.05); color: var(--text-secondary); text-transform: uppercase; font-size: 0.7rem; flex-shrink: 0;">${job.source}</span>
                </div>
                <div class="item-meta" style="margin-top: 0.5rem;">Experience: ${job.experience_required || 'Not specified'}</div>
                <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1rem;">Skills: ${job.skills_required}</p>
                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center;">
                    ${actionButton}
                    <button class="btn outline-btn" onclick="checkMatchScore(${job.id}, this)">Check Match Score</button>
                </div>
                <div id="match-result-${job.id}" style="margin-top: 0.75rem;"></div>
            </div>
        `;
    }).join('');

    const currentPage = Math.floor(skip / JOB_LIMIT) + 1;
    html += `
        <div style="grid-column: 1/-1; display:flex; justify-content: space-between; align-items: center; margin-top: 1.5rem; background: rgba(255,255,255,0.02); padding: 0.75rem 1rem; border-radius: 12px; border: 1px solid var(--glass-border);">
            <button class="btn outline-btn" ${skip === 0 ? 'disabled' : ''} style="min-width: 130px;" onclick="loadAllJobs(${Math.max(0, skip - JOB_LIMIT)}, '${q}')">← Previous Page</button>
            <div class="pagination-indicator" style="display: flex; align-items: center; gap: 0.75rem;">
                <span style="font-size: 0.9rem; font-weight: 500; color: var(--text-primary); letter-spacing: 0.5px;">PAGE ${currentPage}</span>
                <span class="breathing-dots" style="display: flex; gap: 4px;">
                    <span class="pulse-dot" style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background-color: var(--primary-color);"></span>
                    <span class="pulse-dot" style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background-color: var(--accent-color); animation-delay: 0.2s;"></span>
                    <span class="pulse-dot" style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background-color: var(--success-color); animation-delay: 0.4s;"></span>
                </span>
            </div>
            <button class="btn outline-btn" ${jobs.length < JOB_LIMIT ? 'disabled' : ''} style="min-width: 130px;" onclick="loadAllJobs(${skip + JOB_LIMIT}, '${q}')">Next Page →</button>
        </div>
    `;

    container.innerHTML = html;
}

async function checkMatchScore(jobId, btnElement) {
    if (!state.candidateProfileId) {
        alert("Please upload your resume first to calculate a match score.");
        return;
    }

    const resultDiv = document.getElementById(`match-result-${jobId}`);
    btnElement.disabled = true;
    btnElement.textContent = "Calculating...";

    try {
        const result = await apiCall(`/match/${state.candidateProfileId}/${jobId}`);
        const semantic = Math.round(result.semantic_score * 100);
        const keyword = Math.round(result.match_score);
        const badgeClass = semantic >= 80 ? 'match-high' : semantic >= 50 ? 'match-med' : 'match-low';

        resultDiv.innerHTML = `
            <div class="fade-in" style="background: rgba(255,255,255,0.05); padding: 0.75rem; border-radius: 8px; border: 1px solid var(--glass-border);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                    <span>AI Semantic Match:</span>
                    <strong class="match-badge ${badgeClass}" style="margin: 0; padding: 2px 6px;">${semantic}%</strong>
                </div>
                <div style="display: flex; justify-content: space-between; color: var(--text-secondary); font-size: 0.85rem;">
                    <span>Keyword Overlap:</span>
                    <span>${keyword}%</span>
                </div>
            </div>
        `;
    } catch (err) {
        resultDiv.innerHTML = `<span class="error-msg">${err.message}</span>`;
    } finally {
        btnElement.disabled = false;
        btnElement.textContent = "Check Match Score";
    }
}

// --- Recruiter Dashboard ---
async function initRecruiterDashboard() {
    loadRecruiterJobs();
}

async function handleCreateJob(e) {
    e.preventDefault();
    const title = document.getElementById('job-title').value;
    const skills = document.getElementById('job-skills').value;
    const exp = document.getElementById('job-experience').value;
    const statusDiv = document.getElementById('job-status');
    const btn = e.target.querySelector('button');

    btn.disabled = true;
    btn.textContent = "Processing AI Embeddings...";
    statusDiv.innerHTML = '';

    try {
        await apiCall('/jobs', 'POST', {
            title,
            skills_required: skills,
            experience_required: exp
        });
        statusDiv.innerHTML = `<p class="success-msg">Job posted successfully!</p>`;
        e.target.reset();
        loadRecruiterJobs();
    } catch (err) {
        statusDiv.innerHTML = `<p class="error-msg">${err.message}</p>`;
    } finally {
        btn.disabled = false;
        btn.textContent = "Post Job";
    }
}

async function loadRecruiterJobs() {
    const container = document.getElementById('recruiter-jobs-container');
    if (!container) return;

    try {
        const jobs = await apiCall('/jobs');
        if (jobs.length === 0) {
            container.innerHTML = `<p class="empty-state" style="padding: 1rem;">No jobs posted yet.</p>`;
            return;
        }

        container.innerHTML = jobs.map(job => `
            <div class="list-item" onclick="viewApplicants(${job.id}, '${job.title}')">
                <div style="font-weight: 500;">${job.title}</div>
                <div style="font-size: 0.8rem; color: var(--text-secondary);">ID: ${job.id} | Click to view applicants</div>
            </div>
        `).join('');
    } catch (err) {
        container.innerHTML = `<p class="error-msg" style="padding: 1rem;">Failed to load jobs.</p>`;
    }
}

async function viewApplicants(jobId, jobTitle) {
    const section = document.getElementById('applicants-section');
    const container = document.getElementById('applicants-container');
    document.getElementById('selected-job-title').textContent = jobTitle;

    section.classList.remove('hidden');
    container.innerHTML = `<p style="grid-column: 1/-1;">Loading AI-ranked applicants...</p>`;

    try {
        const applicants = await apiCall(`/jobs/${jobId}/applicants`);

        if (applicants.length === 0) {
            container.innerHTML = `<p class="empty-state" style="grid-column: 1/-1;">No applicants for this job yet.</p>`;
            return;
        }

        let high = 0, med = 0, low = 0;

        container.innerHTML = applicants.map(app => {
            const score = Math.round(app.semantic_score * 100);
            const badgeClass = score >= 80 ? 'match-high' : score >= 50 ? 'match-med' : 'match-low';

            if (score >= 80) high++;
            else if (score >= 50) med++;
            else low++;

            return `
                <div class="item-card" style="margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <h4 style="margin: 0;">Candidate #${app.candidate_id}</h4>
                        <span class="match-badge ${badgeClass}">${score}% Match</span>
                    </div>
                    <div class="item-meta">
                        <strong>Exact Keyword Overlap:</strong> ${app.match_score}%
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <strong>Skills:</strong>
                        <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.25rem;">${app.skills}</p>
                    </div>
                    <div>
                        <strong>Experience:</strong>
                        <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.25rem; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;">${app.experience}</p>
                    </div>
                </div>
            `;
        }).join('');

        renderRecruiterChart(high, med, low);
    } catch (err) {
        container.innerHTML = `<p class="error-msg" style="grid-column: 1/-1;">Failed to load applicants.</p>`;
    }
}

function renderRecruiterChart(high, med, low) {
    const ctx = document.getElementById('recruiterChart');
    if (!ctx) return;

    if (recruiterChartInstance) recruiterChartInstance.destroy();

    recruiterChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['High Match (>80%)', 'Medium Match', 'Low Match'],
            datasets: [{
                data: [high, med, low],
                backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom', labels: { color: '#f8fafc' } }
            }
        }
    });
}

async function searchCandidates() {
    const query = document.getElementById('candidate-search-input').value.trim();
    const container = document.getElementById('candidate-search-results');
    if (!query) return;

    container.innerHTML = `<p>Searching database...</p>`;
    try {
        const results = await apiCall(`/candidates/search?query=${encodeURIComponent(query)}`);
        if (results.length === 0) {
            container.innerHTML = `<p class="empty-state">No candidates found with those skills.</p>`;
            return;
        }

        container.innerHTML = results.map(c => {
            const skillsList = c.skills.split(',').map(s =>
                `<span class="match-badge" style="margin: 2px; background: rgba(59,130,246,0.1); color: #93c5fd; border: 1px solid rgba(59,130,246,0.2); border-radius: 20px; padding: 2px 8px; font-size: 0.75rem; font-weight: 500; display: inline-block;">${s.trim()}</span>`
            ).join('');

            return `
                <div class="item-card" style="display: flex; flex-direction: column; gap: 0.75rem; justify-content: space-between;">
                    <div>
                        <h4 style="margin: 0 0 0.5rem 0; font-size: 1.15rem; color: #fff;">Candidate #${c.id}</h4>
                        <div style="margin-bottom: 0.5rem;">
                            <strong style="font-size: 0.85rem; color: var(--text-secondary); display: block; margin-bottom: 0.35rem;">Skills:</strong>
                            <div style="display: flex; flex-wrap: wrap; margin: -2px;">${skillsList}</div>
                        </div>
                    </div>
                    <div>
                        <strong style="font-size: 0.85rem; color: var(--text-secondary); display: block; margin-bottom: 0.25rem;">Experience Summary:</strong>
                        <p style="font-size: 0.85rem; color: var(--text-secondary); display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; margin: 0; line-height: 1.4;">${c.experience}</p>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        container.innerHTML = `<p class="error-msg">${err.message}</p>`;
    }
}

// --- API Helper ---
async function apiCall(endpoint, method = 'GET', body = null) {
    const headers = {};
    if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
    if (body && !(body instanceof FormData)) headers['Content-Type'] = 'application/json';

    const config = { method, headers };
    if (body) config.body = body instanceof FormData ? body : JSON.stringify(body);

    const res = await fetch(`${API_URL}${endpoint}`, config);
    const data = await res.json();

    if (!res.ok) {
        if (res.status === 401) {
            logout();
            throw new Error("Session expired. Please log in again.");
        }
        throw new Error(data.detail || data.error || "API Error");
    }

    return data;
}

// --- Chatbot Logic ---
function toggleChat() {
    const chatWidget = document.getElementById('chat-widget');
    const toggleBtn = document.getElementById('chat-toggle-btn');

    if (chatWidget.classList.contains('hidden')) {
        chatWidget.classList.remove('hidden');
        toggleBtn.classList.add('hidden');
    } else {
        chatWidget.classList.add('hidden');
        toggleBtn.classList.remove('hidden');
    }
}

function handleChatEnter(e) {
    if (e.key === 'Enter') sendChatMessage();
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    appendChatMessage(msg, 'user');
    input.value = '';

    const messagesDiv = document.getElementById('chat-messages');
    const loadingId = 'loading-' + Date.now();
    messagesDiv.insertAdjacentHTML('beforeend', `<div id="${loadingId}" class="message ai" style="opacity: 0.5;">Thinking...</div>`);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    try {
        const payload = { message: msg };
        if (state.role === 'candidate' && state.candidateProfileId) {
            payload.candidate_id = state.candidateProfileId;
        }

        const response = await apiCall('/chat', 'POST', payload);
        document.getElementById(loadingId).remove();

        let reply = response.response;
        if (typeof reply === 'object') {
            reply = JSON.stringify(reply, null, 2);
        }
        appendChatMessage(reply, 'ai');
    } catch (err) {
        document.getElementById(loadingId).remove();
        appendChatMessage("Sorry, I encountered an error communicating with the AI.", 'ai');
    }
}

function appendChatMessage(text, sender) {
    const messagesDiv = document.getElementById('chat-messages');
    messagesDiv.insertAdjacentHTML('beforeend', `<div class="message ${sender}">${text.replace(/\n/g, '<br>')}</div>`);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}
