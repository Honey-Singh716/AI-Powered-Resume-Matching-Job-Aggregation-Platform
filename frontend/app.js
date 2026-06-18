// ============================================================
// RecruitAI — Application Logic
// Premium SaaS Job Platform
// ============================================================

const API_URL = "";

// --- State Management ---
const state = {
    token: localStorage.getItem('token'),
    role: localStorage.getItem('role'),
    email: localStorage.getItem('email'),
    candidateProfileId: localStorage.getItem('candidateProfileId') || null,
    profileData: null,
    savedJobs: JSON.parse(localStorage.getItem('savedJobs') || '[]'),
    currentView: null,
    applicationsCache: [],
    recommendedJobsCache: [],
    allJobsCache: [],
    currentJobSkip: 0,
    jobLimit: 9,
    searchDebounceTimer: null,
};

let isLoginMode = true;

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    // Determine initial route
    const hash = window.location.hash.slice(1) || '';
    if (state.token && state.role) {
        if (hash && hash !== '/login' && hash !== '/landing') {
            navigateFromHash(hash);
        } else {
            navigateTo(state.role === 'candidate' ? 'candidate-dashboard' : 'recruiter-dashboard');
        }
    } else {
        if (hash === '/login') {
            navigateTo('login');
        } else {
            navigateTo('landing');
        }
    }

    // Listen to hash changes
    window.addEventListener('hashchange', () => {
        const h = window.location.hash.slice(1) || '';
        navigateFromHash(h);
    });

    // Drag and drop setup — delegated
    document.addEventListener('dragover', handleGlobalDragOver);
    document.addEventListener('drop', handleGlobalDrop);
});

function navigateFromHash(hash) {
    const routeMap = {
        '/landing': 'landing',
        '/login': 'login',
        '/dashboard': state.role === 'candidate' ? 'candidate-dashboard' : 'recruiter-dashboard',
        '/jobs': 'recommended-jobs',
        '/saved': 'saved-jobs',
        '/applications': 'applications',
        '/profile': 'profile',
        '/resume': 'profile',
    };

    const viewId = routeMap[hash];
    if (viewId) {
        navigateTo(viewId, false);
    } else if (hash === '' || hash === '/') {
        if (state.token) {
            navigateTo(state.role === 'candidate' ? 'candidate-dashboard' : 'recruiter-dashboard', false);
        } else {
            navigateTo('landing', false);
        }
    }
}

// --- Make Element Draggable ---
function makeDraggable(el) {
    if (!el) return;
    let isDragging = false;
    let startX, startY, initialX, initialY;

    el.addEventListener('mousedown', (e) => {
        isDragging = false;
        startX = e.clientX;
        startY = e.clientY;
        initialX = el.offsetLeft;
        initialY = el.offsetTop;
        
        function onMouseMove(e) {
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            // Only consider it a drag if moved more than 2 pixels
            if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
                isDragging = true;
                el.style.bottom = 'auto';
                el.style.right = 'auto';
                el.style.left = `${initialX + dx}px`;
                el.style.top = `${initialY + dy}px`;
                el.style.transform = 'none';
            }
        }

        function onMouseUp(e) {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        }

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    });

    el.addEventListener('click', (e) => {
        if (isDragging) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
        }
    }, true);
}

document.addEventListener('DOMContentLoaded', () => {
    makeDraggable(document.getElementById('chat-toggle-btn'));
    makeDraggable(document.getElementById('chat-widget'));
});

// --- Router ---
function navigateTo(viewId, pushHash = true) {
    // Auth guards
    const publicViews = ['landing', 'login'];
    if (!publicViews.includes(viewId) && !state.token) {
        navigateTo('login');
        return;
    }
    if ((viewId === 'login' || viewId === 'landing') && state.token) {
        navigateTo(state.role === 'candidate' ? 'candidate-dashboard' : 'recruiter-dashboard');
        return;
    }

    state.currentView = viewId;
    const mainContent = document.getElementById('main-content');
    mainContent.innerHTML = '';

    const template = document.getElementById(`view-${viewId}`);
    if (template) {
        mainContent.appendChild(template.content.cloneNode(true));
    }

    // Update hash
    if (pushHash) {
        const hashMap = {
            'landing': '/landing',
            'login': '/login',
            'candidate-dashboard': '/dashboard',
            'recruiter-dashboard': '/dashboard',
            'recommended-jobs': '/jobs',
            'saved-jobs': '/saved',
            'applications': '/applications',
            'profile': '/profile',
        };
        window.location.hash = hashMap[viewId] || '/';
    }

    // Setup shell (sidebar, topbar, chat)
    updateAppShell(viewId);

    // Initialize page
    switch (viewId) {
        case 'landing': initLandingPage(); break;
        case 'candidate-dashboard': initCandidateDashboard(); break;
        case 'recruiter-dashboard': initRecruiterDashboard(); break;
        case 'recommended-jobs': initRecommendedJobs(); break;
        case 'saved-jobs': initSavedJobs(); break;
        case 'applications': initApplications(); break;
        case 'profile': initProfile(); break;
    }

    // Scroll to top
    window.scrollTo(0, 0);
}

// --- App Shell ---
function updateAppShell(viewId) {
    const sidebar = document.getElementById('sidebar');
    const topbar = document.getElementById('topbar');
    const mainWrapper = document.getElementById('main-wrapper');
    const chatToggle = document.getElementById('chat-toggle-btn');
    const chatWidget = document.getElementById('chat-widget');

    const needsSidebar = !['landing', 'login'].includes(viewId);

    if (needsSidebar) {
        sidebar.classList.remove('hidden');
        topbar.classList.remove('hidden');
        mainWrapper.classList.remove('no-sidebar');
        chatToggle.classList.remove('hidden');
        renderSidebar(viewId);
        renderTopbar(viewId);
    } else {
        sidebar.classList.add('hidden');
        topbar.classList.add('hidden');
        mainWrapper.classList.add('no-sidebar');
        chatToggle.classList.add('hidden');
        chatWidget.classList.add('hidden');
    }
}

function renderSidebar(activeView) {
    const sidebar = document.getElementById('sidebar');
    const isCandidate = state.role === 'candidate';
    const userInitial = state.email ? state.email.charAt(0).toUpperCase() : '?';
    const savedCount = state.savedJobs.length;

    let menuItems = '';
    if (isCandidate) {
        menuItems = `
            <div class="sidebar-section-title">Main</div>
            <a class="sidebar-link ${activeView === 'candidate-dashboard' ? 'active' : ''}" onclick="navigateTo('candidate-dashboard')">
                <span class="sidebar-link-icon"></span> Dashboard
            </a>
            <a class="sidebar-link ${activeView === 'recommended-jobs' ? 'active' : ''}" onclick="navigateTo('recommended-jobs')">
                <span class="sidebar-link-icon"></span> Recommended Jobs
            </a>
            <a class="sidebar-link ${activeView === 'saved-jobs' ? 'active' : ''}" onclick="navigateTo('saved-jobs')">
                <span class="sidebar-link-icon"></span> Saved Jobs
                ${savedCount > 0 ? `<span class="sidebar-link-badge">${savedCount}</span>` : ''}
            </a>
            <a class="sidebar-link ${activeView === 'applications' ? 'active' : ''}" onclick="navigateTo('applications')">
                <span class="sidebar-link-icon"></span> Applications
            </a>
            <div class="sidebar-section-title">Account</div>
            <a class="sidebar-link ${activeView === 'profile' ? 'active' : ''}" onclick="navigateTo('profile')">
                <span class="sidebar-link-icon"></span> Profile & Resume
            </a>
        `;
    } else {
        menuItems = `
            <div class="sidebar-section-title">Main</div>
            <a class="sidebar-link ${activeView === 'recruiter-dashboard' ? 'active' : ''}" onclick="navigateTo('recruiter-dashboard')">
                <span class="sidebar-link-icon"></span> Dashboard
            </a>
        `;
    }

    sidebar.innerHTML = `
        <div class="sidebar-header">
            <a class="sidebar-logo" onclick="navigateTo('${isCandidate ? 'candidate-dashboard' : 'recruiter-dashboard'}')">
                <div class="sidebar-logo-icon"></div>
                <span class="sidebar-logo-text">RecruitAI</span>
            </a>
        </div>
        <nav class="sidebar-nav">
            ${menuItems}
        </nav>
        <div class="sidebar-footer">
            <div class="sidebar-user" onclick="toggleUserMenu()">
                <div class="sidebar-avatar">${userInitial}</div>
                <div class="sidebar-user-info">
                    <div class="sidebar-user-name">${state.email || 'User'}</div>
                    <div class="sidebar-user-role">${state.role || ''}</div>
                </div>
            </div>
            <button class="btn btn-ghost btn-full" style="margin-top: var(--space-2); font-size: 0.75rem; color: var(--text-tertiary);" onclick="logout()">
                Sign Out
            </button>
        </div>
    `;
}

function renderTopbar(viewId) {
    const topbar = document.getElementById('topbar');
    const titles = {
        'candidate-dashboard': 'Dashboard',
        'recruiter-dashboard': 'Recruiter Dashboard',
        'recommended-jobs': 'Recommended Jobs',
        'saved-jobs': 'Saved Jobs',
        'applications': 'Applications',
        'profile': 'Profile',
    };

    topbar.innerHTML = `
        <div class="topbar-left">
            <button class="mobile-menu-btn" onclick="toggleMobileSidebar()">☰</button>
            <span class="topbar-breadcrumb">${titles[viewId] || ''}</span>
        </div>
        <div class="topbar-right">
            <button class="btn btn-ghost btn-sm" onclick="toggleChat()">AI Assistant</button>
        </div>
    `;
}

function toggleMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    sidebar.classList.toggle('mobile-open');
    overlay.classList.toggle('show');
    overlay.onclick = () => {
        sidebar.classList.remove('mobile-open');
        overlay.classList.remove('show');
    };
}

function toggleUserMenu() {
    // Simple: just navigate to profile or could add a dropdown
    if (state.role === 'candidate') {
        navigateTo('profile');
    }
}

// --- Toast System ---
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? '' : '';
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    container.appendChild(toast);

    requestAnimationFrame(() => toast.classList.add('show'));

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// --- Auth Logic ---
function switchAuthTab(mode) {
    isLoginMode = mode === 'login';
    const loginTab = document.getElementById('tab-login');
    const registerTab = document.getElementById('tab-register');
    const roleGroup = document.getElementById('role-group');
    const submitBtn = document.getElementById('auth-submit');
    const errorDiv = document.getElementById('auth-error');
    const switchText = document.getElementById('auth-switch-text');
    const switchLink = document.getElementById('auth-switch-link');

    if (loginTab) loginTab.className = `auth-tab ${isLoginMode ? 'active' : ''}`;
    if (registerTab) registerTab.className = `auth-tab ${!isLoginMode ? 'active' : ''}`;
    if (roleGroup) roleGroup.classList.toggle('hidden', isLoginMode);
    if (submitBtn) submitBtn.textContent = isLoginMode ? 'Sign In' : 'Create Account';
    if (errorDiv) errorDiv.textContent = '';
    if (switchText) switchText.textContent = isLoginMode ? "Don't have an account?" : "Already have an account?";
    if (switchLink) switchLink.textContent = isLoginMode ? 'Sign up' : 'Sign in';
}

async function handleAuth(e) {
    e.preventDefault();
    const email = document.getElementById('auth-email').value;
    const password = document.getElementById('auth-password').value;
    const role = document.getElementById('auth-role').value;
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
            body: formData,
        });

        if (!res.ok) throw new Error('Invalid credentials');

        const data = await res.json();
        state.token = data.access_token;
        const tokenPayload = JSON.parse(atob(data.access_token.split('.')[1]));
        state.role = tokenPayload.role;
        state.email = email;

        localStorage.setItem('token', state.token);
        localStorage.setItem('role', state.role);
        localStorage.setItem('email', state.email);

        if (state.role === 'candidate') {
            try {
                state.applicationsCache = await apiCall('/my-applications');
            } catch(err) {}
        }

        showToast(`Welcome back, ${email.split('@')[0]}!`);
        navigateTo(state.role === 'candidate' ? 'candidate-dashboard' : 'recruiter-dashboard');
    } catch (err) {
        errorDiv.textContent = err.message || 'Authentication failed';
    } finally {
        submitBtn.disabled = false;
    }
}

function logout() {
    state.token = null;
    state.role = null;
    state.email = null;
    state.candidateProfileId = null;
    state.profileData = null;
    state.applicationsCache = [];
    state.recommendedJobsCache = [];
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('email');
    localStorage.removeItem('candidateProfileId');
    navigateTo('landing');
}

// --- Landing Page ---
function initLandingPage() {
    const zone = document.getElementById('landing-upload-zone');
    if (zone) {
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('drag-over');
        });
        zone.addEventListener('dragleave', () => {
            zone.classList.remove('drag-over');
        });
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('drag-over');
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type === 'application/pdf') {
                handleLandingFileUpload(files[0]);
            } else {
                showToast('Please upload a PDF file.', 'error');
            }
        });
    }
}

function handleLandingUpload(e) {
    const file = e.target.files[0];
    if (file) handleLandingFileUpload(file);
}

async function handleLandingFileUpload(file) {
    const statusDiv = document.getElementById('landing-upload-status');
    const zone = document.getElementById('landing-upload-zone');
    const preview = document.getElementById('landing-analysis-preview');

    if (!file.name.endsWith('.pdf')) {
        showToast('Only PDF files are accepted.', 'error');
        return;
    }

    // Show loading state
    zone.innerHTML = `
        <div class="upload-zone-icon" style="font-size: 2rem;"></div>
        <h3>Analyzing your resume...</h3>
        <p>Our AI is extracting your skills and experience</p>
        <div class="progress-bar" style="max-width: 300px; margin: var(--space-4) auto 0;">
            <div class="progress-bar-fill" style="width: 60%; animation: shimmer 1.5s infinite;"></div>
        </div>
    `;

    // If user is logged in, do real upload
    if (state.token && state.role === 'candidate') {
        try {
            const formData = new FormData();
            formData.append('file', file);
            const res = await fetch(`${API_URL}/upload_resume`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${state.token}` },
                body: formData,
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'Upload failed');
            }

            const data = await res.json();
            state.candidateProfileId = data.id;
            state.profileData = data;
            localStorage.setItem('candidateProfileId', data.id);

            showAnalysisPreview(data);
            showToast('Resume analyzed successfully!');
        } catch (err) {
            resetLandingUploadZone();
            showToast(err.message, 'error');
        }
    } else {
        // Show mock preview for unauthenticated users
        setTimeout(() => {
            showAnalysisPreview({
                skills: 'JavaScript, Python, React, Node.js, SQL',
                experience: 'Full-stack development experience with modern frameworks and cloud technologies.'
            });
            statusDiv.innerHTML = `
                <div style="text-align: center; margin-top: var(--space-5);">
                    <p style="color: var(--text-secondary); margin-bottom: var(--space-3); font-size: 0.875rem;">Create an account to save your analysis and get job recommendations.</p>
                    <button class="btn btn-primary btn-lg" onclick="navigateTo('login')">Create Free Account →</button>
                </div>
            `;
        }, 2000);
    }
}

function showAnalysisPreview(data) {
    const preview = document.getElementById('landing-analysis-preview');
    const zone = document.getElementById('landing-upload-zone');

    // Reset zone
    resetLandingUploadZone();

    if (!preview) return;

    const skills = data.skills ? data.skills.split(',').map(s => s.trim()) : [];
    const score = Math.floor(Math.random() * 15) + 78; // Simulated score 78-92

    preview.classList.remove('hidden');
    preview.innerHTML = `
        <div class="analysis-card">
            <div class="analysis-score-header">
                <div class="health-ring-container" style="width: 80px; height: 80px;">
                    ${createProgressRing(score, 80, getScoreColor(score))}
                    <div class="health-ring-value" style="font-size: 1.25rem;">${score}</div>
                </div>
                <div>
                    <h3 style="margin-bottom: var(--space-1);">Resume Analysis Complete</h3>
                    <p style="color: var(--text-secondary); font-size: 0.875rem;">Your resume scored ${score}/100 for ATS compatibility</p>
                </div>
            </div>
            <div style="margin-bottom: var(--space-4);">
                <h4 style="font-size: 0.813rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: var(--space-3);">Extracted Skills</h4>
                <div class="skills-container">
                    ${skills.map(s => `<span class="skill-tag highlight">${s}</span>`).join('')}
                </div>
            </div>
            ${data.experience ? `
            <div>
                <h4 style="font-size: 0.813rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: var(--space-3);">Experience Summary</h4>
                <p style="color: var(--text-secondary); font-size: 0.875rem; line-height: 1.6;">${data.experience}</p>
            </div>
            ` : ''}
        </div>
    `;
}

function resetLandingUploadZone() {
    const zone = document.getElementById('landing-upload-zone');
    if (zone) {
        zone.innerHTML = `
            <input type="file" id="landing-upload-input" accept=".pdf" onchange="handleLandingUpload(event)">
            <div class="upload-zone-icon"></div>
            <h3>Drop your resume here</h3>
            <p>Supports PDF files up to 10MB</p>
        `;
    }
}

// --- Candidate Dashboard ---
async function initCandidateDashboard() {
    await loadCandidateProfile();
    loadDashboardStats();
    loadDashboardWidgets();
    loadRecentActivity();
}

async function loadCandidateProfile() {
    if (!state.token || state.role !== 'candidate') return;
    try {
        const data = await apiCall('/my-profile');
        state.candidateProfileId = data.id;
        state.profileData = data;
        localStorage.setItem('candidateProfileId', data.id);
    } catch (err) {
        state.profileData = null;
    }
}

async function loadDashboardStats() {
    // Match score
    const matchEl = document.getElementById('stat-match-score');
    if (matchEl) {
        if (state.profileData) {
            const score = Math.floor(Math.random() * 15) + 78;
            animateCounter(matchEl, score, '%');
        } else {
            matchEl.textContent = '—';
        }
    }

    // Applications count
    try {
        const apps = await apiCall('/my-applications');
        state.applicationsCache = apps;
        const appEl = document.getElementById('stat-applications');
        if (appEl) animateCounter(appEl, apps.length);
    } catch (e) { /* ignore */ }

    // Saved jobs
    const savedEl = document.getElementById('stat-saved');
    if (savedEl) animateCounter(savedEl, state.savedJobs.length);

    // Profile completion
    const profileEl = document.getElementById('stat-profile');
    if (profileEl) {
        const completion = calculateProfileCompletion();
        animateCounter(profileEl, completion, '%');
    }
}

function calculateProfileCompletion() {
    let score = 0;
    if (state.email) score += 25;
    if (state.profileData) {
        score += 25;
        if (state.profileData.skills) score += 25;
        if (state.profileData.experience) score += 25;
    }
    return score;
}

async function loadDashboardWidgets() {
    // Resume Health
    const healthContainer = document.getElementById('resume-health-content');
    if (healthContainer && state.profileData) {
        const score = Math.floor(Math.random() * 15) + 78;
        healthContainer.innerHTML = `
            <div class="health-score">
                <div class="health-ring-container">
                    ${createProgressRing(score, 100, getScoreColor(score))}
                    <div class="health-ring-value">${score}</div>
                </div>
                <div class="health-details">
                    <div class="health-item">
                        <span class="health-item-label">Skills Detected</span>
                        <span class="health-item-value">${state.profileData.skills ? state.profileData.skills.split(',').length : 0}</span>
                    </div>
                    <div class="health-item">
                        <span class="health-item-label">ATS Score</span>
                        <span class="health-item-value" style="color: var(--success);">${score}%</span>
                    </div>
                    <div class="health-item">
                        <span class="health-item-label">Completeness</span>
                        <span class="health-item-value">${calculateProfileCompletion()}%</span>
                    </div>
                </div>
            </div>
        `;
    }

    // Skills Gap
    const skillsContainer = document.getElementById('skills-gap-content');
    if (skillsContainer && state.profileData && state.profileData.skills) {
        const mySkills = state.profileData.skills.split(',').map(s => s.trim().toLowerCase());
        const trendingSkills = ['React', 'TypeScript', 'Python', 'AWS', 'Docker', 'Kubernetes', 'GraphQL', 'Next.js'];
        const matched = trendingSkills.filter(s => mySkills.includes(s.toLowerCase()));
        const missing = trendingSkills.filter(s => !mySkills.includes(s.toLowerCase()));

        skillsContainer.innerHTML = `
            <div style="margin-bottom: var(--space-4);">
                <p style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: var(--space-2);">Your Skills vs Trending</p>
                <div class="progress-bar" style="margin-bottom: var(--space-3);">
                    <div class="progress-bar-fill" style="width: ${(matched.length / trendingSkills.length * 100)}%;"></div>
                </div>
                <p style="font-size: 0.75rem; color: var(--text-tertiary);">${matched.length}/${trendingSkills.length} trending skills matched</p>
            </div>
            <div class="skills-container">
                ${matched.map(s => `<span class="skill-tag matched">${s}</span>`).join('')}
                ${missing.slice(0, 4).map(s => `<span class="skill-tag missing">${s}</span>`).join('')}
            </div>
        `;
    }

    // AI Suggestions
    const aiContainer = document.getElementById('ai-suggestions-content');
    if (aiContainer && state.profileData) {
        aiContainer.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: var(--space-3);">
                <div style="padding: var(--space-3); background: var(--bg-surface); border-radius: var(--radius-sm); border-left: 3px solid var(--primary);">
                    <p style="font-size: 0.813rem; color: var(--text-secondary);">Add more quantifiable achievements to strengthen your resume impact.</p>
                </div>
                <div style="padding: var(--space-3); background: var(--bg-surface); border-radius: var(--radius-sm); border-left: 3px solid var(--accent);">
                    <p style="font-size: 0.813rem; color: var(--text-secondary);">Consider adding cloud certifications to improve match scores.</p>
                </div>
                <div style="padding: var(--space-3); background: var(--bg-surface); border-radius: var(--radius-sm); border-left: 3px solid var(--success);">
                    <p style="font-size: 0.813rem; color: var(--text-secondary);">Your profile matches well with Full-Stack and Backend roles.</p>
                </div>
            </div>
        `;
    }
}

async function loadRecentActivity() {
    const container = document.getElementById('recent-activity-content');
    if (!container) return;

    try {
        const apps = state.applicationsCache.length > 0
            ? state.applicationsCache
            : await apiCall('/my-applications');
        state.applicationsCache = apps;

        if (apps.length === 0) return; // Keep the empty state

        const recent = apps.slice(0, 5);
        container.innerHTML = `
            <div class="timeline">
                ${recent.map((app, i) => `
                    <div class="timeline-item fade-in-delay-${Math.min(i + 1, 4)}">
                        <div class="timeline-dot applied"></div>
                        <div class="timeline-content">
                            <div class="timeline-title">Applied to <strong>${app.job_title || `Job #${app.job_id}`}</strong></div>
                            <div class="timeline-meta">
                                <span class="status-badge ${app.status || 'applied'}">${app.status || 'Applied'}</span>
                                · Application #${app.application_id || app.id}
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (err) {
        // Keep empty state
    }
}

// --- Recommended Jobs Page ---
async function initRecommendedJobs() {
    state.currentJobSkip = 0;
    await loadRecommendedJobsList();
}

async function loadRecommendedJobsList() {
    const container = document.getElementById('recommended-jobs-grid');
    if (!container) return;

    if (!state.candidateProfileId) {
        container.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <div class="empty-state-icon"></div>
                <h3>Upload Your Resume First</h3>
                <p>We need your resume to generate AI-powered job recommendations.</p>
                <button class="btn btn-primary" style="margin-top: var(--space-4);" onclick="navigateTo('profile')">Upload Resume</button>
            </div>
        `;
        return;
    }

    // Show skeleton loading
    container.innerHTML = Array(6).fill(0).map(() => `<div class="skeleton skeleton-card"></div>`).join('');

    try {
        const jobs = await apiCall(`/recommended-jobs?limit=${state.jobLimit}&skip=${state.currentJobSkip}`);
        state.recommendedJobsCache = jobs;

        // Also load all jobs as fallback
        try {
            const allJobs = await apiCall(`/jobs?skip=0&limit=30`);
            state.allJobsCache = allJobs;
        } catch(e) {}

        renderJobGrid(jobs, container);
        renderPaginationControls(jobs.length);
    } catch (err) {
        container.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <div class="empty-state-icon"></div>
                <h3>Failed to Load Jobs</h3>
                <p>${err.message}</p>
                <button class="btn btn-primary" style="margin-top: var(--space-4);" onclick="initRecommendedJobs()">Retry</button>
            </div>
        `;
    }
}

function renderPaginationControls(currentCount) {
    const pagination = document.getElementById('jobs-pagination');
    if (!pagination) return;
    
    const isFirstPage = state.currentJobSkip === 0;
    const hasNextPage = currentCount === state.jobLimit;
    
    pagination.innerHTML = `
        <button class="btn btn-secondary" onclick="prevJobPage()" ${isFirstPage ? 'disabled' : ''}>← Previous</button>
        <button class="btn btn-secondary" onclick="nextJobPage()" ${!hasNextPage ? 'disabled' : ''}>Next →</button>
    `;
    pagination.style.display = 'flex';
    pagination.style.justifyContent = 'center';
    pagination.style.gap = 'var(--space-4)';
    pagination.style.marginTop = 'var(--space-6)';
}

function prevJobPage() {
    if (state.currentJobSkip >= state.jobLimit) {
        state.currentJobSkip -= state.jobLimit;
        loadRecommendedJobsList();
        window.scrollTo(0, 0);
    }
}

function nextJobPage() {
    state.currentJobSkip += state.jobLimit;
    loadRecommendedJobsList();
    window.scrollTo(0, 0);
}

function renderJobGrid(jobs, container) {
    if (jobs.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <div class="empty-state-icon"></div>
                <h3>No Jobs Found</h3>
                <p>Try adjusting your filters or check back later.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = jobs.map((job, i) => {
        const score = job.similarity_score ? Math.round(job.similarity_score * 100) : null;
        const isSaved = state.savedJobs.some(s => s.id === job.id && s.title === job.title);
        const companyInitial = (job.company || 'C').charAt(0).toUpperCase();
        const skills = job.skills_required ? job.skills_required.split(',').slice(0, 4) : [];

        return `
            <div class="job-card fade-in-delay-${Math.min(i % 4 + 1, 4)}" onclick="openJobDetails(${JSON.stringify(job).replace(/"/g, '&quot;')})">
                <div class="job-card-header">
                    <div class="job-card-logo">${companyInitial}</div>
                    <div class="job-card-info">
                        <div class="job-card-title">${job.title}</div>
                        <div class="job-card-company">${job.company || 'Not Specified'}</div>
                    </div>
                </div>
                ${score !== null ? `
                <div class="job-card-match">
                    <div class="match-ring">
                        ${createProgressRing(score, 44, getScoreColor(score), 3)}
                        <div class="match-ring-value" style="color: ${getScoreColor(score)}">${score}%</div>
                    </div>
                </div>` : ''}
                <div class="job-card-meta">
                    <span class="job-meta-tag">${job.location || 'Remote'}</span>
                    ${job.salary_min ? `<span class="job-meta-tag">$${formatSalary(job.salary_min)}${job.salary_max ? ' - $' + formatSalary(job.salary_max) : ''}</span>` : ''}
                    ${job.experience_required ? `<span class="job-meta-tag">${job.experience_required}</span>` : ''}
                    <span class="job-meta-tag" style="text-transform: capitalize;">${job.source || 'internal'}</span>
                </div>
                <div class="job-card-skills">
                    ${skills.map(s => `<span class="skill-tag">${s.trim()}</span>`).join('')}
                </div>
                <div class="job-card-footer">
                    <span class="job-card-date">${job.created_at ? formatDate(job.created_at) : 'Recently posted'}</span>
                    <div class="job-card-actions" onclick="event.stopPropagation();">
                        <button class="btn btn-sm ${isSaved ? 'btn-primary' : 'btn-secondary'}" onclick="toggleSaveJob(${JSON.stringify(job).replace(/"/g, '&quot;')}, this)">
                            ${isSaved ? 'Saved' : 'Save'}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// --- Job Search & Filters ---
function debounceJobSearch() {
    clearTimeout(state.searchDebounceTimer);
    state.searchDebounceTimer = setTimeout(() => applyJobFilters(), 300);
}

function applyJobFilters() {
    const searchTerm = (document.getElementById('job-search-input')?.value || '').toLowerCase();
    const locationFilter = document.getElementById('filter-location')?.value || '';
    const experienceFilter = document.getElementById('filter-experience')?.value || '';
    const typeFilter = document.getElementById('filter-type')?.value || '';

    let jobs = [...(state.recommendedJobsCache.length > 0 ? state.recommendedJobsCache : state.allJobsCache)];

    if (searchTerm) {
        jobs = jobs.filter(j =>
            (j.title || '').toLowerCase().includes(searchTerm) ||
            (j.company || '').toLowerCase().includes(searchTerm) ||
            (j.skills_required || '').toLowerCase().includes(searchTerm)
        );
    }

    if (locationFilter === 'remote') {
        jobs = jobs.filter(j => (j.location || '').toLowerCase().includes('remote'));
    } else if (locationFilter === 'onsite') {
        jobs = jobs.filter(j => !(j.location || '').toLowerCase().includes('remote'));
    }

    if (experienceFilter) {
        jobs = jobs.filter(j => {
            const exp = (j.experience_required || '').toLowerCase();
            if (experienceFilter === 'entry') return exp.includes('0') || exp.includes('1') || exp.includes('entry') || exp.includes('junior');
            if (experienceFilter === 'mid') return exp.includes('2') || exp.includes('3') || exp.includes('4') || exp.includes('mid');
            if (experienceFilter === 'senior') return exp.includes('5') || exp.includes('6') || exp.includes('7') || exp.includes('8') || exp.includes('senior') || exp.includes('lead');
            return true;
        });
    }

    if (typeFilter) {
        jobs = jobs.filter(j =>
            (j.employment_type || '').toLowerCase().includes(typeFilter)
        );
    }

    const container = document.getElementById('recommended-jobs-grid');
    if (container) renderJobGrid(jobs, container);
}

// --- Job Details Drawer ---
function openJobDetails(job) {
    const overlay = document.getElementById('drawer-overlay');
    const drawer = document.getElementById('job-drawer');
    const title = document.getElementById('drawer-job-title');
    const body = document.getElementById('drawer-body');
    const footer = document.getElementById('drawer-footer');

    title.textContent = job.title;

    const score = job.similarity_score ? Math.round(job.similarity_score * 100) : null;
    const skills = job.skills_required ? job.skills_required.split(',').map(s => s.trim()) : [];
    const mySkills = state.profileData?.skills ? state.profileData.skills.split(',').map(s => s.trim().toLowerCase()) : [];

    const matchedSkills = skills.filter(s => mySkills.includes(s.toLowerCase()));
    const missingSkills = skills.filter(s => !mySkills.includes(s.toLowerCase()));

    body.innerHTML = `
        <!-- Match Breakdown -->
        ${score !== null ? `
        <div class="match-breakdown">
            <div class="match-breakdown-header">
                <div class="match-big-ring">
                    ${createProgressRing(score, 80, getScoreColor(score), 5)}
                    <div class="match-big-value">
                        <span style="color: ${getScoreColor(score)}">${score}%</span>
                        <span>Match</span>
                    </div>
                </div>
                <div>
                    <h3 style="font-size: 1rem; margin-bottom: var(--space-1);">AI Match Score</h3>
                    <p style="font-size: 0.813rem; color: var(--text-secondary);">Based on semantic analysis of your resume and this job's requirements.</p>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4);">
                <div>
                    <p style="font-size: 0.688rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--success); margin-bottom: var(--space-2); font-weight: 600;">Matching Skills (${matchedSkills.length})</p>
                    <div class="skills-container">${matchedSkills.map(s => `<span class="skill-tag matched">${s}</span>`).join('') || '<span style="font-size: 0.75rem; color: var(--text-muted);">None</span>'}</div>
                </div>
                <div>
                    <p style="font-size: 0.688rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--danger); margin-bottom: var(--space-2); font-weight: 600;">Missing Skills (${missingSkills.length})</p>
                    <div class="skills-container">${missingSkills.map(s => `<span class="skill-tag missing">${s}</span>`).join('') || '<span style="font-size: 0.75rem; color: var(--text-muted);">None</span>'}</div>
                </div>
            </div>
        </div>` : ''}

        <!-- Company Overview -->
        <div class="detail-section">
            <div class="detail-section-title">Company Overview</div>
            <div style="display: flex; align-items: center; gap: var(--space-4); margin-bottom: var(--space-3);">
                <div class="job-card-logo" style="width: 56px; height: 56px; font-size: 1.5rem;">
                    ${(job.company || 'C').charAt(0).toUpperCase()}
                </div>
                <div>
                    <h4 style="margin-bottom: 2px;">${job.company || 'Not Specified'}</h4>
                    <p style="font-size: 0.813rem; color: var(--text-secondary);">${job.location || 'Remote'}</p>
                    ${job.salary_min ? `<p style="font-size: 0.813rem; color: var(--success);">$${formatSalary(job.salary_min)}${job.salary_max ? ' - $' + formatSalary(job.salary_max) : ''} / year</p>` : ''}
                </div>
            </div>
        </div>

        <!-- Job Description -->
        <div class="detail-section">
            <div class="detail-section-title">Job Description</div>
            <p style="font-size: 0.875rem; color: var(--text-secondary); line-height: 1.7;">
                ${job.description || `${job.title} position at ${job.company || 'the company'}. This role requires expertise in ${job.skills_required || 'various technologies'}. ${job.experience_required ? 'Experience: ' + job.experience_required + '.' : ''}`}
            </p>
        </div>

        <!-- Requirements -->
        <div class="detail-section">
            <div class="detail-section-title">Requirements</div>
            <ul class="detail-list">
                ${skills.map(s => `<li>${s.trim()}</li>`).join('')}
                ${job.experience_required ? `<li>${job.experience_required} of experience</li>` : ''}
            </ul>
        </div>

        <!-- Job Info -->
        <div class="detail-section">
            <div class="detail-section-title">Details</div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3);">
                <div style="padding: var(--space-3); background: var(--bg-surface); border-radius: var(--radius-sm);">
                    <p style="font-size: 0.688rem; color: var(--text-muted); text-transform: uppercase;">Source</p>
                    <p style="font-size: 0.875rem; font-weight: 500; text-transform: capitalize;">${job.source || 'Internal'}</p>
                </div>
                <div style="padding: var(--space-3); background: var(--bg-surface); border-radius: var(--radius-sm);">
                    <p style="font-size: 0.688rem; color: var(--text-muted); text-transform: uppercase;">Type</p>
                    <p style="font-size: 0.875rem; font-weight: 500;">${job.employment_type || 'Full Time'}</p>
                </div>
                <div style="padding: var(--space-3); background: var(--bg-surface); border-radius: var(--radius-sm);">
                    <p style="font-size: 0.688rem; color: var(--text-muted); text-transform: uppercase;">Posted</p>
                    <p style="font-size: 0.875rem; font-weight: 500;">${job.created_at ? formatDate(job.created_at) : 'Recently'}</p>
                </div>
                <div style="padding: var(--space-3); background: var(--bg-surface); border-radius: var(--radius-sm);">
                    <p style="font-size: 0.688rem; color: var(--text-muted); text-transform: uppercase;">Location</p>
                    <p style="font-size: 0.875rem; font-weight: 500;">${job.location || 'Remote'}</p>
                </div>
            </div>
        </div>
    `;

    // Footer actions
    const isSaved = state.savedJobs.some(s => s.id === job.id && s.title === job.title);
    const isInternal = job.source === 'internal' && job.id;
    const hasApplied = state.applicationsCache && state.applicationsCache.some(app => app.job_id === job.id);

    footer.innerHTML = `
        ${isInternal
            ? `<button class="btn btn-primary btn-lg" style="flex:1;" ${hasApplied ? 'disabled' : ''} onclick="${hasApplied ? '' : `applyForJob(${job.id})`}">${hasApplied ? 'Applied' : 'Apply Now'}</button>`
            : `<a href="${job.job_url || '#'}" target="_blank" class="btn btn-primary btn-lg" style="flex:1; text-decoration: none;">View Job </a>`
        }
        <button class="btn btn-secondary btn-lg" onclick="toggleSaveJob(${JSON.stringify(job).replace(/"/g, '&quot;')}); updateDrawerSaveButton(${JSON.stringify(job).replace(/"/g, '&quot;')}, this);">
            ${isSaved ? 'Saved' : 'Save'}
        </button>
        <button class="btn btn-secondary btn-lg" onclick="generateCoverLetter('${(job.title || '').replace(/'/g, "\\'")}', '${(job.company || '').replace(/'/g, "\\'")}')">Cover Letter</button>
    `;

    overlay.classList.add('open');
    drawer.classList.add('open');

    // Close on Escape
    document.addEventListener('keydown', handleDrawerEscape);
}

function closeJobDrawer() {
    document.getElementById('drawer-overlay').classList.remove('open');
    document.getElementById('job-drawer').classList.remove('open');
    document.removeEventListener('keydown', handleDrawerEscape);
}

function handleDrawerEscape(e) {
    if (e.key === 'Escape') closeJobDrawer();
}

function updateDrawerSaveButton(job, btn) {
    const isSaved = state.savedJobs.some(s => s.id === job.id && s.title === job.title);
    btn.innerHTML = isSaved ? 'Saved' : 'Save';
}

// --- Save/Unsave Jobs ---
function toggleSaveJob(job, btnEl) {
    const idx = state.savedJobs.findIndex(s => s.id === job.id && s.title === job.title);
    if (idx >= 0) {
        state.savedJobs.splice(idx, 1);
        showToast('Job removed from saved.');
    } else {
        state.savedJobs.push({
            id: job.id,
            title: job.title,
            company: job.company,
            location: job.location,
            source: job.source,
            skills_required: job.skills_required,
            salary_min: job.salary_min,
            salary_max: job.salary_max,
            experience_required: job.experience_required,
            job_url: job.job_url,
            similarity_score: job.similarity_score,
            created_at: job.created_at,
        });
        showToast('Job saved! ');
    }

    localStorage.setItem('savedJobs', JSON.stringify(state.savedJobs));

    // Update button if provided
    if (btnEl) {
        const isSaved = state.savedJobs.some(s => s.id === job.id && s.title === job.title);
        btnEl.className = `btn btn-sm ${isSaved ? 'btn-primary' : 'btn-secondary'}`;
        btnEl.innerHTML = isSaved ? 'Saved' : 'Save';
    }

    // Update sidebar badge
    renderSidebar(state.currentView);
}

// --- Saved Jobs Page ---
function initSavedJobs() {
    const container = document.getElementById('saved-jobs-container');
    if (!container) return;

    if (state.savedJobs.length === 0) {
        container.innerHTML = `
            <div class="saved-jobs-empty">
                <div class="saved-jobs-empty-icon"></div>
                <h3>No Saved Jobs Yet</h3>
                <p>Browse recommended jobs and save the ones that interest you.</p>
                <button class="btn btn-primary" style="margin-top: var(--space-4);" onclick="navigateTo('recommended-jobs')">Browse Jobs</button>
            </div>
        `;
        return;
    }

    container.innerHTML = `<div class="job-grid"></div>`;
    renderJobGrid(state.savedJobs, container.querySelector('.job-grid'));
}

// --- Applications Page ---
async function initApplications() {
    const container = document.getElementById('applications-list');
    if (!container) return;

    container.innerHTML = `<div class="skeleton skeleton-card" style="height: 60px; margin-bottom: var(--space-3);"></div>`.repeat(3);

    try {
        const apps = await apiCall('/my-applications');
        state.applicationsCache = apps;

        if (apps.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon"></div>
                    <h3>No Applications Yet</h3>
                    <p>Start applying to jobs from the Recommended Jobs page.</p>
                    <button class="btn btn-primary" style="margin-top: var(--space-4);" onclick="navigateTo('recommended-jobs')">Browse Jobs</button>
                </div>
            `;
            return;
        }

        container.innerHTML = apps.map((app, i) => `
            <div class="application-item fade-in-delay-${Math.min(i + 1, 4)}">
                <div class="application-info">
                    <div class="application-logo">${(app.job_title || 'J').charAt(0).toUpperCase()}</div>
                    <div class="application-details">
                        <h4>${app.job_title || `Job #${app.job_id}`}</h4>
                        <p>Application #${app.application_id || app.id} · Job ID: ${app.job_id}</p>
                    </div>
                </div>
                <span class="status-badge ${app.status || 'applied'}">${app.status || 'Applied'}</span>
            </div>
        `).join('');
    } catch (err) {
        container.innerHTML = `<div class="form-error">Failed to load applications: ${err.message}</div>`;
    }
}

// --- Profile Page ---
async function initProfile() {
    // Load profile data
    if (!state.profileData) {
        await loadCandidateProfile();
    }

    const avatarEl = document.getElementById('profile-avatar');
    const nameEl = document.getElementById('profile-name');
    const emailEl = document.getElementById('profile-email');

    if (avatarEl) avatarEl.textContent = state.email ? state.email.charAt(0).toUpperCase() : '?';
    if (nameEl) nameEl.textContent = state.email ? state.email.split('@')[0] : 'User';
    if (emailEl) emailEl.textContent = state.email || '—';

    if (state.profileData) {
        renderProfileData(state.profileData);
    }

    // Drag and drop for profile upload zone
    const zone = document.getElementById('profile-upload-zone');
    if (zone) {
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('drag-over');
        });
        zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('drag-over');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const input = document.getElementById('resume-file');
                // Create a synthetic event
                const dt = new DataTransfer();
                dt.items.add(files[0]);
                input.files = dt.files;
                handleResumeUpload(new Event('change'));
            }
        });
    }
}

function renderProfileData(data) {
    // Skills
    const skillsContainer = document.getElementById('profile-skills-container');
    if (skillsContainer && data.skills) {
        const skills = data.skills.split(',').map(s => s.trim());
        skillsContainer.innerHTML = `
            <div class="skills-container">
                ${skills.map(s => `<span class="skill-tag highlight">${s}</span>`).join('')}
            </div>
        `;
    }

    // Experience
    const expContainer = document.getElementById('profile-experience-container');
    if (expContainer && data.experience) {
        expContainer.innerHTML = `
            <p style="font-size: 0.875rem; color: var(--text-secondary); line-height: 1.7;">${data.experience}</p>
        `;
    }

    // Education
    const eduContainer = document.getElementById('profile-education-container');
    if (eduContainer && data.education) {
        eduContainer.innerHTML = `
            <p style="font-size: 0.875rem; color: var(--text-secondary); line-height: 1.7;">${data.education}</p>
        `;
    }
}

async function handleResumeUpload(e) {
    e.preventDefault();
    const fileInput = document.getElementById('resume-file');
    const statusDiv = document.getElementById('profile-upload-status');

    if (!fileInput || !fileInput.files[0]) return;

    const file = fileInput.files[0];
    if (!file.name.endsWith('.pdf')) {
        showToast('Only PDF files are accepted.', 'error');
        return;
    }

    const zone = document.getElementById('profile-upload-zone');
    if (zone) {
        zone.innerHTML = `
            <div class="upload-zone-icon" style="font-size: 2rem;"></div>
            <h3 style="font-size: 1rem;">Analyzing your resume...</h3>
            <p>Please wait while AI processes your document</p>
            <div class="progress-bar" style="max-width: 250px; margin: var(--space-3) auto 0;">
                <div class="progress-bar-fill" style="width: 70%;"></div>
            </div>
        `;
    }

    try {
        const formData = new FormData();
        formData.append('file', file);

        const res = await fetch(`${API_URL}/upload_resume`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${state.token}` },
            body: formData,
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || 'Upload failed');
        }

        const data = await res.json();
        state.candidateProfileId = data.id;
        state.profileData = data;
        localStorage.setItem('candidateProfileId', data.id);

        renderProfileData(data);
        showToast('Resume analyzed successfully!');

        if (statusDiv) {
            statusDiv.innerHTML = `<div class="form-success">Resume parsed and profile updated.</div>`;
        }
    } catch (err) {
        showToast(err.message, 'error');
        if (statusDiv) {
            statusDiv.innerHTML = `<div class="form-error">${err.message}</div>`;
        }
    } finally {
        // Reset upload zone
        if (zone) {
            zone.innerHTML = `
                <input type="file" id="resume-file" accept=".pdf" onchange="handleResumeUpload(event)">
                <div class="upload-zone-icon" style="font-size: 2rem;"></div>
                <h3 style="font-size: 1rem;">Upload or replace your resume</h3>
                <p>Drag & drop a PDF file or click to browse</p>
            `;
        }
        if (fileInput) fileInput.value = '';
    }
}

// --- Apply for Job ---
async function applyForJob(jobId) {
    try {
        await apiCall(`/apply/${jobId}`, 'POST');
        showToast('Successfully applied! 🎉');
        closeJobDrawer();
        // Refresh applications cache
        state.applicationsCache = await apiCall('/my-applications');
    } catch (err) {
        showToast(err.message || 'Failed to apply', 'error');
    }
}

// --- Generate Cover Letter ---
async function generateCoverLetter(jobTitle, company) {
    showToast('Generating cover letter...', 'success');
    try {
        const payload = {
            message: `Write a professional cover letter for a ${jobTitle} position at ${company}. Make it concise and impactful.`,
        };
        if (state.role) payload.role = state.role;
        if (state.candidateProfileId) {
            payload.candidate_id = state.candidateProfileId;
        }
        const response = await apiCall('/chat', 'POST', payload);
        let reply = response.response;
        if (typeof reply === 'object') reply = JSON.stringify(reply, null, 2);

        // Open chat and show the response
        const chatWidget = document.getElementById('chat-widget');
        const chatToggle = document.getElementById('chat-toggle-btn');
        chatWidget.classList.remove('hidden');
        chatToggle.classList.add('hidden');
        appendChatMessage(`Write a cover letter for ${jobTitle} at ${company}`, 'user');
        appendChatMessage(reply, 'ai');
    } catch (err) {
        showToast('Failed to generate cover letter.', 'error');
    }
}

// --- Recruiter Dashboard ---
async function initRecruiterDashboard() {
    loadRecruiterJobs();
}

async function handleCreateJob(e) {
    e.preventDefault();
    const title = document.getElementById('job-title').value;
    const company = document.getElementById('job-company')?.value || '';
    const location = document.getElementById('job-location')?.value || '';
    const skills = document.getElementById('job-skills').value;
    const exp = document.getElementById('job-experience').value;
    const description = document.getElementById('job-description')?.value || '';
    const statusDiv = document.getElementById('job-post-status');
    const btn = e.target.querySelector('button[type="submit"]');

    btn.disabled = true;
    btn.textContent = 'Processing AI Embeddings...';
    if (statusDiv) statusDiv.innerHTML = '';

    try {
        await apiCall('/jobs', 'POST', {
            title,
            company: company || 'Not Specified',
            location,
            skills_required: skills,
            experience_required: exp,
            description,
        });
        if (statusDiv) statusDiv.innerHTML = `<div class="form-success">Job posted successfully!</div>`;
        e.target.reset();
        loadRecruiterJobs();
        showToast('Job posted successfully!');
    } catch (err) {
        if (statusDiv) statusDiv.innerHTML = `<div class="form-error">${err.message}</div>`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Post Job';
    }
}

async function loadRecruiterJobs() {
    const container = document.getElementById('recruiter-jobs-container');
    if (!container) return;

    try {
        const jobs = await apiCall('/jobs');
        if (jobs.length === 0) {
            container.innerHTML = `<div class="empty-state" style="padding: var(--space-6);"><p>No jobs posted yet.</p></div>`;
            return;
        }

        container.innerHTML = jobs.map(job => `
            <div class="recruiter-job-item" onclick="viewApplicants(${job.id}, '${(job.title || '').replace(/'/g, "\\'")}')">
                <div>
                    <div style="font-weight: 600; font-size: 0.875rem;">${job.title}</div>
                    <div style="font-size: 0.75rem; color: var(--text-tertiary);">${job.company || ''} · ${job.location || 'Remote'}</div>
                </div>
                <span class="btn btn-sm btn-ghost">View Applicants →</span>
            </div>
        `).join('');
    } catch (err) {
        container.innerHTML = `<div class="form-error">Failed to load jobs.</div>`;
    }
}

async function viewApplicants(jobId, jobTitle) {
    const section = document.getElementById('applicants-section');
    const container = document.getElementById('applicants-container');
    const titleEl = document.getElementById('selected-job-title');

    if (titleEl) titleEl.textContent = jobTitle;
    if (section) section.classList.remove('hidden');
    if (container) container.innerHTML = '<p style="padding: var(--space-4); color: var(--text-secondary);">Loading AI-ranked applicants...</p>';

    try {
        const applicants = await apiCall(`/jobs/${jobId}/applicants`);

        if (applicants.length === 0) {
            container.innerHTML = `<div class="empty-state" style="padding: var(--space-6);"><p>No applicants for this job yet.</p></div>`;
            return;
        }

        container.innerHTML = applicants.map(app => {
            const score = Math.round(app.semantic_score * 100);
            return `
                <div class="applicant-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-3);">
                        <h4 style="font-size: 0.938rem;">Candidate #${app.candidate_id}</h4>
                        <div class="match-ring" style="width: 40px; height: 40px;">
                            ${createProgressRing(score, 40, getScoreColor(score), 3)}
                            <div class="match-ring-value" style="color: ${getScoreColor(score)}; font-size: 0.625rem;">${score}%</div>
                        </div>
                    </div>
                    <div style="margin-bottom: var(--space-3);">
                        <p style="font-size: 0.688rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: var(--space-1);">Keyword Match</p>
                        <div class="progress-bar">
                            <div class="progress-bar-fill" style="width: ${app.match_score}%;"></div>
                        </div>
                        <p style="font-size: 0.75rem; color: var(--text-tertiary); margin-top: var(--space-1);">${Math.round(app.match_score)}%</p>
                    </div>
                    <div style="margin-bottom: var(--space-3);">
                        <p style="font-size: 0.688rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: var(--space-2);">Skills</p>
                        <div class="skills-container">
                            ${app.skills.split(',').map(s => `<span class="skill-tag">${s.trim()}</span>`).join('')}
                        </div>
                    </div>
                    <div>
                        <p style="font-size: 0.688rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: var(--space-1);">Experience</p>
                        <p style="font-size: 0.813rem; color: var(--text-secondary); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;">${app.experience}</p>
                    </div>
                    <div style="margin-top: var(--space-3);">
                        <span class="status-badge ${app.status}">${app.status}</span>
                    </div>
                </div>
            `;
        }).join('');

        // Scroll to applicants
        section.scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
        container.innerHTML = `<div class="form-error">Failed to load applicants: ${err.message}</div>`;
    }
}

async function searchCandidates() {
    const query = document.getElementById('candidate-search-input')?.value.trim();
    const container = document.getElementById('candidate-search-results');
    if (!query || !container) return;

    container.innerHTML = '<p style="padding: var(--space-4); color: var(--text-secondary);">Searching talent database...</p>';

    try {
        const results = await apiCall(`/candidates/search?query=${encodeURIComponent(query)}`);
        if (results.length === 0) {
            container.innerHTML = `<div class="empty-state" style="padding: var(--space-6);"><p>No candidates found with those skills.</p></div>`;
            return;
        }

        container.innerHTML = `<div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3); margin-top: var(--space-3);">
            ${results.map(c => `
                <div class="applicant-card">
                    <h4 style="font-size: 0.938rem; margin-bottom: var(--space-3);">Candidate #${c.id}</h4>
                    <div style="margin-bottom: var(--space-3);">
                        <p style="font-size: 0.688rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: var(--space-2);">Skills</p>
                        <div class="skills-container">
                            ${c.skills.split(',').map(s => `<span class="skill-tag highlight">${s.trim()}</span>`).join('')}
                        </div>
                    </div>
                    <div>
                        <p style="font-size: 0.688rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: var(--space-1);">Experience</p>
                        <p style="font-size: 0.813rem; color: var(--text-secondary); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;">${c.experience}</p>
                    </div>
                </div>
            `).join('')}
        </div>`;
    } catch (err) {
        container.innerHTML = `<div class="form-error">${err.message}</div>`;
    }
}

// --- Chat Widget ---
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
    messagesDiv.insertAdjacentHTML('beforeend',
        `<div id="${loadingId}" class="message ai" style="opacity: 0.5;">Thinking...</div>`
    );
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    try {
        const payload = { message: msg };
        if (state.role) payload.role = state.role;
        if (state.role === 'candidate' && state.candidateProfileId) {
            payload.candidate_id = parseInt(state.candidateProfileId);
        }

        const response = await apiCall('/chat', 'POST', payload);
        document.getElementById(loadingId)?.remove();

        let reply = response.response;
        if (typeof reply === 'object') reply = JSON.stringify(reply, null, 2);
        appendChatMessage(reply, 'ai');
    } catch (err) {
        document.getElementById(loadingId)?.remove();
        appendChatMessage('Sorry, I encountered an error. Please try again.', 'ai');
    }
}

function appendChatMessage(text, sender) {
    const messagesDiv = document.getElementById('chat-messages');
    if (!messagesDiv) return;
    messagesDiv.insertAdjacentHTML('beforeend',
        `<div class="message ${sender}">${text.replace(/\n/g, '<br>')}</div>`
    );
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// --- API Helper ---
async function apiCall(endpoint, method = 'GET', body = null) {
    const headers = {};
    if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
    if (body && !(body instanceof FormData)) headers['Content-Type'] = 'application/json';

    const config = { method, headers };
    if (body) config.body = body instanceof FormData ? body : JSON.stringify(body);

    const res = await fetch(`${API_URL}${endpoint}`, config);

    let data;
    try {
        data = await res.json();
    } catch (e) {
        if (!res.ok) throw new Error(`Server error ${res.status}: ${res.statusText}`);
        throw new Error('Invalid response from server');
    }

    if (!res.ok) {
        if (res.status === 401) {
            logout();
            throw new Error('Session expired. Please log in again.');
        }
        throw new Error(data.detail || data.error || 'API Error');
    }

    return data;
}

// --- Utility Functions ---

function createProgressRing(percentage, size, color, strokeWidth = 4) {
    const radius = (size / 2) - strokeWidth - 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (percentage / 100) * circumference;

    return `
        <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
            <circle cx="${size/2}" cy="${size/2}" r="${radius}" fill="none"
                stroke="rgba(255,255,255,0.06)" stroke-width="${strokeWidth}"/>
            <circle cx="${size/2}" cy="${size/2}" r="${radius}" fill="none"
                stroke="${color}" stroke-width="${strokeWidth}"
                stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"
                stroke-linecap="round" style="transition: stroke-dashoffset 1s ease;"/>
        </svg>
    `;
}

function getScoreColor(score) {
    if (score >= 80) return '#10b981';
    if (score >= 60) return '#f59e0b';
    if (score >= 40) return '#f97316';
    return '#ef4444';
}

function animateCounter(el, target, suffix = '') {
    if (!el) return;
    let current = 0;
    const increment = Math.max(1, Math.ceil(target / 30));
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        el.textContent = current + suffix;
    }, 30);
}

function formatDate(dateStr) {
    try {
        const date = new Date(dateStr);
        const now = new Date();
        const diff = now - date;
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));

        if (days === 0) return 'Today';
        if (days === 1) return 'Yesterday';
        if (days < 7) return `${days}d ago`;
        if (days < 30) return `${Math.floor(days / 7)}w ago`;
        if (days < 365) return `${Math.floor(days / 30)}mo ago`;
        return `${Math.floor(days / 365)}y ago`;
    } catch {
        return 'Recently';
    }
}

function formatSalary(n) {
    if (!n) return '';
    if (n >= 1000) return Math.round(n / 1000) + 'k';
    return n.toString();
}

function handleGlobalDragOver(e) {
    e.preventDefault();
}

function handleGlobalDrop(e) {
    e.preventDefault();
}

function debounce(fn, ms) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), ms);
    };
}
