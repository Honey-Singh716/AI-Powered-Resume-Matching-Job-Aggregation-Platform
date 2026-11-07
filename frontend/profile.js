// RecruitAI profile editor. Sections are optional; nothing is filled with sample data.

const profileEditor = {
    draft: null,
    saved: null,
    editing: null,
    saving: false,
    uploading: false,
};

const PF_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const PF_RING = 2 * Math.PI * 42;

function pfId() {
    return `pf_${Math.random().toString(36).slice(2, 10)}`;
}

function pfClone(value) {
    return JSON.parse(JSON.stringify(value));
}

function pfEl(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
}

function pfClear(node) {
    if (!node) return;
    while (node.firstChild) node.removeChild(node.firstChild);
}

function pfSafePhoto(value) {
    return typeof value === 'string' && /^data:image\/(jpeg|png|webp);base64,/i.test(value) ? value : '';
}

function pfInitials(name, email) {
    const source = (name || '').trim();
    if (source) {
        return source.split(/\s+/).slice(0, 2).map((part) => part.charAt(0).toUpperCase()).join('') || '?';
    }
    return (email || '?').charAt(0).toUpperCase();
}

function pfDraftFromServer(data) {
    const skills = Array.isArray(data.skills)
        ? data.skills.map((skill) => String(skill).trim()).filter(Boolean)
        : String(data.skills || '').split(',').map((skill) => skill.trim()).filter(Boolean);
    const withId = (item) => Object.assign({ id: pfId() }, item || {});
    return {
        full_name: data.full_name || '',
        email: data.email || state.email || '',
        professional_title: data.professional_title || '',
        profile_photo: pfSafePhoto(data.profile_photo),
        skills,
        experience_items: (data.experience_items || []).map(withId),
        education_items: (data.education_items || []).map(withId),
        certifications: (data.certifications || []).map(withId),
        experience_summary: data.experience_summary || '',
        education_summary: data.education_summary || '',
        resume_filename: data.resume_filename || '',
        candidate_id: data.candidate_id || null,
    };
}

function pfCompletionChecks(draft) {
    const data = draft || {};
    const skills = (data.skills || []).filter((skill) => String(skill).trim());
    return [
        { label: 'Full name added', done: !!(data.full_name || '').trim() },
        { label: 'Email address added', done: !!(data.email || '').trim() },
        { label: 'Professional title added', done: !!(data.professional_title || '').trim() },
        { label: 'Profile photo added', done: !!pfSafePhoto(data.profile_photo) },
        { label: 'Resume uploaded', done: !!(data.resume_filename || '').trim() },
        { label: 'At least one skill added', done: skills.length > 0 },
        { label: 'Experience added', done: (data.experience_items || []).length > 0 || !!(data.experience_summary || '').trim() },
        { label: 'Education added', done: (data.education_items || []).length > 0 || !!(data.education_summary || '').trim() },
        { label: 'Certification added', done: (data.certifications || []).length > 0 },
    ];
}

function pfIsDirty() {
    if (!profileEditor.draft || !profileEditor.saved) return false;
    return JSON.stringify(profileEditor.draft) !== JSON.stringify(profileEditor.saved);
}

function pfReadIdentity() {
    const draft = profileEditor.draft;
    if (!draft) return;
    draft.full_name = document.getElementById('pf-name').value;
    draft.email = document.getElementById('pf-email').value.trim();
    draft.professional_title = document.getElementById('pf-title').value;
}

function pfSetBanner(message, type) {
    const banner = document.getElementById('pf-banner');
    if (!banner) return;
    if (!message) {
        banner.textContent = '';
        banner.className = 'pf-banner hidden';
        return;
    }
    banner.textContent = message;
    banner.className = `pf-banner is-${type || 'success'}`;
    banner.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

function pfSetStatus(message, type) {
    const status = document.getElementById('pf-resume-status');
    if (!status) return;
    status.textContent = message || '';
    status.className = `pf-status${type ? ` is-${type}` : ''}`;
}

function pfShowFieldErrors(fields) {
    ['full_name', 'email', 'professional_title', 'skills'].forEach((key) => {
        const error = document.getElementById(`pf-error-${key}`);
        if (error) error.textContent = fields[key] || '';
    });
    const name = document.getElementById('pf-name');
    const email = document.getElementById('pf-email');
    const title = document.getElementById('pf-title');
    if (name) name.classList.toggle('is-invalid', !!fields.full_name);
    if (email) email.classList.toggle('is-invalid', !!fields.email);
    if (title) title.classList.toggle('is-invalid', !!fields.professional_title);
}

function pfFormatApiError(data) {
    const detail = data && data.detail;
    if (typeof detail === 'string') return { message: detail, fields: {} };
    if (Array.isArray(detail)) {
        const fields = {};
        const lines = detail.map((err) => {
            const loc = (err.loc || []).filter((part) => part !== 'body');
            const message = String(err.msg || 'Invalid value').replace(/^Value error,\s*/i, '');
            if (loc.length === 1) fields[String(loc[0])] = message;
            const label = loc.map((part) => String(part).replace(/_/g, ' ')).join(' ');
            return label ? `${label}: ${message}` : message;
        });
        return { message: lines[0] || 'Please correct the highlighted fields.', fields };
    }
    if (detail && typeof detail === 'object') {
        return {
            message: detail.message || 'Please correct the highlighted fields.',
            fields: detail.fields || {},
        };
    }
    return { message: 'Could not save your profile.', fields: {} };
}

async function initProfile() {
    const loading = document.getElementById('pf-loading');
    const content = document.getElementById('pf-content');
    if (!loading || !content) return;

    try {
        const account = await apiCall('/users/me');
        profileEditor.editing = null;
        profileEditor.saving = false;
        profileEditor.uploading = false;
        pfApplyAccount(account);
        pfBind();
        loading.classList.add('hidden');
        content.classList.remove('hidden');
        pfSetBanner('', 'success');
    } catch (err) {
        loading.textContent = err.message || 'Could not load your profile.';
    }
}

function pfApplyAccount(account, options = {}) {
    const previous = profileEditor.draft;
    const previousSaved = profileEditor.saved;
    const next = pfDraftFromServer(account);
    profileEditor.saved = pfClone(next);
    if (options.preserveEdits && previous && previousSaved) {
        ['full_name', 'email', 'professional_title', 'profile_photo', 'experience_items', 'education_items', 'certifications'].forEach((key) => {
            if (JSON.stringify(previous[key]) !== JSON.stringify(previousSaved[key])) {
                next[key] = previous[key];
            }
        });
    }
    profileEditor.draft = next;
    state.email = account.email || state.email;
    if (state.email) localStorage.setItem('email', state.email);
    if (account.access_token) {
        state.token = account.access_token;
        localStorage.setItem('token', state.token);
    }
    if (account.candidate_id) {
        state.candidateProfileId = String(account.candidate_id);
        localStorage.setItem('candidateProfileId', state.candidateProfileId);
        state.profileData = Object.assign({}, state.profileData || {}, {
            id: account.candidate_id,
            skills: (account.skills || []).join(','),
            experience: account.experience || account.experience_summary || '',
            education: account.education || account.education_summary || '',
        });
    }
    pfPaint();
}

function pfBind() {
    const content = document.getElementById('pf-content');
    if (!content || content.dataset.bound === 'true') return;
    content.dataset.bound = 'true';

    ['pf-name', 'pf-email', 'pf-title'].forEach((id) => {
        document.getElementById(id).addEventListener('input', () => {
            pfReadIdentity();
            pfShowFieldErrors({});
            pfRenderAvatar();
            pfRenderCompletion();
            pfRenderDirty();
        });
    });

    document.getElementById('pf-avatar-btn').addEventListener('click', () => {
        document.getElementById('pf-photo-input').click();
    });
    document.getElementById('pf-photo-change').addEventListener('click', () => {
        document.getElementById('pf-photo-input').click();
    });
    document.getElementById('pf-photo-remove').addEventListener('click', () => {
        profileEditor.draft.profile_photo = '';
        pfRenderAvatar();
        pfRenderCompletion();
        pfRenderDirty();
    });
    document.getElementById('pf-photo-input').addEventListener('change', pfOnPhoto);

    const resume = document.getElementById('pf-resume-file');
    resume.addEventListener('change', () => {
        const file = resume.files && resume.files[0];
        if (file) pfUploadResume(file);
    });
    const zone = document.getElementById('pf-dropzone');
    zone.addEventListener('dragover', (event) => {
        event.preventDefault();
        zone.classList.add('is-dragover');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('is-dragover'));
    zone.addEventListener('drop', (event) => {
        event.preventDefault();
        zone.classList.remove('is-dragover');
        const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
        if (file) pfUploadResume(file);
    });

    document.getElementById('pf-choose-file').addEventListener('click', () => {
        document.getElementById('pf-resume-file').click();
    });
    document.getElementById('pf-edit-name').addEventListener('click', () => document.getElementById('pf-name').focus());
    document.getElementById('pf-edit-title').addEventListener('click', () => document.getElementById('pf-title').focus());
    document.getElementById('pf-skill-toggle').addEventListener('click', () => {
        document.getElementById('pf-skill-row').classList.remove('hidden');
        document.getElementById('pf-skill-input').focus();
    });
    document.getElementById('pf-skill-add').addEventListener('click', pfAddSkill);
    document.getElementById('pf-skill-input').addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            pfAddSkill();
        }
    });

    document.getElementById('pf-exp-current').addEventListener('change', (event) => {
        const end = document.getElementById('pf-exp-end');
        end.disabled = event.target.checked;
        if (event.target.checked) end.value = '';
    });

    content.addEventListener('click', pfOnClick);
    document.getElementById('pf-save').addEventListener('click', pfSave);
    document.getElementById('pf-discard').addEventListener('click', pfDiscard);
}

function pfOnClick(event) {
    const button = event.target.closest('[data-pf-action]');
    if (!button) return;
    const action = button.dataset.pfAction;
    const id = button.dataset.pfId;
    if (action === 'remove-skill') pfRemoveSkill(id);
    if (action === 'toggle-experience') pfToggleForm('experience');
    if (action === 'toggle-education') pfToggleForm('education');
    if (action === 'toggle-certification') pfToggleForm('certification');
    if (action === 'cancel-form') pfCloseForm(button.dataset.pfForm);
    if (action === 'submit-experience') pfSubmitExperience();
    if (action === 'submit-education') pfSubmitEducation();
    if (action === 'submit-certification') pfSubmitCertification();
    if (action === 'edit-experience') pfEditExperience(id);
    if (action === 'edit-education') pfEditEducation(id);
    if (action === 'edit-certification') pfEditCertification(id);
    if (action === 'remove-experience') pfRemoveItem('experience_items', id);
    if (action === 'remove-education') pfRemoveItem('education_items', id);
    if (action === 'remove-certification') pfRemoveItem('certifications', id);
    if (action === 'clear-experience-summary') pfClearSummary('experience_summary');
    if (action === 'clear-education-summary') pfClearSummary('education_summary');
}

function pfPaint() {
    pfFillIdentity();
    pfRenderAvatar();
    pfRenderSkills();
    pfRenderExperience();
    pfRenderEducation();
    pfRenderCerts();
    pfRenderResume();
    pfRenderCompletion();
    pfRenderDirty();
}

function pfFillIdentity() {
    const draft = profileEditor.draft;
    if (!draft) return;
    document.getElementById('pf-name').value = draft.full_name;
    document.getElementById('pf-email').value = draft.email;
    document.getElementById('pf-title').value = draft.professional_title;
}

function pfRenderAvatar() {
    const draft = profileEditor.draft;
    const img = document.getElementById('pf-avatar-img');
    const initials = document.getElementById('pf-avatar-initials');
    const remove = document.getElementById('pf-photo-remove');
    if (!draft || !img || !initials) return;
    const photo = pfSafePhoto(draft.profile_photo);
    if (photo) {
        img.src = photo;
        img.hidden = false;
        initials.hidden = true;
    } else {
        img.removeAttribute('src');
        img.hidden = true;
        initials.hidden = false;
        initials.textContent = pfInitials(draft.full_name, draft.email);
    }
    if (remove) remove.hidden = !photo;
}

function pfRenderSkills() {
    const list = document.getElementById('pf-skills');
    if (!list || !profileEditor.draft) return;
    pfClear(list);
    const skills = profileEditor.draft.skills;
    if (!skills.length) return;
    skills.forEach((skill, index) => {
        const pill = pfEl('span', 'pf-skill');
        pill.appendChild(pfEl('span', '', skill));
        const remove = pfEl('button', 'pf-skill-remove', '×');
        remove.type = 'button';
        remove.setAttribute('aria-label', `Remove ${skill}`);
        remove.dataset.pfAction = 'remove-skill';
        remove.dataset.pfId = String(index);
        pill.appendChild(remove);
        list.appendChild(pill);
    });
}

function pfEmptyIcon(name) {
    const icons = {
        briefcase: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/></svg>',
        education: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M22 10L12 5 2 10l10 5 10-5z"/><path d="M6 12v5c3 2 9 2 12 0v-5"/></svg>',
        award: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="6"/><path d="M8.5 13.5L7 22l5-3 5 3-1.5-8.5"/></svg>',
    };
    return icons[name] || '';
}

function pfRenderExperience() {
    const summary = (profileEditor.draft.experience_summary || '').trim();
    pfRenderSummary('pf-experience-summary', summary, 'clear-experience-summary');
    pfRenderEntries('pf-experience-list', profileEditor.draft.experience_items, {
        hideEmpty: !!summary,
        emptyTitle: 'No experience added yet',
        emptyHint: 'Start by adding your work experience or projects.',
        emptyIcon: 'briefcase',
        edit: 'edit-experience',
        remove: 'remove-experience',
        title: (item) => item.role,
        meta: (item) => [item.company, pfMonthRange(item)].filter(Boolean).join(' · '),
        body: (item) => item.description,
    });
}

function pfRenderEducation() {
    const summary = (profileEditor.draft.education_summary || '').trim();
    pfRenderSummary('pf-education-summary', summary, 'clear-education-summary');
    pfRenderEntries('pf-education-list', profileEditor.draft.education_items, {
        hideEmpty: !!summary,
        emptyTitle: 'No education details added yet',
        emptyHint: 'Add your degree, institution and graduation year.',
        emptyIcon: 'education',
        edit: 'edit-education',
        remove: 'remove-education',
        title: (item) => item.degree,
        meta: (item) => [item.school, item.field, pfYearRange(item)].filter(Boolean).join(' · '),
    });
}

function pfRenderCerts() {
    pfRenderEntries('pf-cert-list', profileEditor.draft.certifications, {
        emptyTitle: 'No certifications added yet',
        emptyHint: 'Add your certifications and achievements.',
        emptyIcon: 'award',
        edit: 'edit-certification',
        remove: 'remove-certification',
        title: (item) => item.name,
        meta: (item) => [item.issuer, item.year].filter(Boolean).join(' · '),
    });
}

function pfRenderSummary(id, text, action) {
    const host = document.getElementById(id);
    if (!host) return;
    pfClear(host);
    const value = (text || '').trim();
    if (!value) return;
    const box = pfEl('div', 'pf-summary');
    box.appendChild(pfEl('p', 'pf-summary-label', 'From your resume'));
    box.appendChild(pfEl('p', 'pf-summary-text', value));
    const button = pfEl('button', 'pf-text-btn', 'Remove summary');
    button.type = 'button';
    button.dataset.pfAction = action;
    box.appendChild(button);
    host.appendChild(box);
}

function pfRenderEntries(id, items, config) {
    const list = document.getElementById(id);
    if (!list) return;
    pfClear(list);
    if (!items.length) {
        if (config.hideEmpty) return;
        const box = pfEl('div', 'pf-empty-box');
        const mark = pfEl('span', 'pf-empty-mark');
        mark.innerHTML = pfEmptyIcon(config.emptyIcon);
        box.appendChild(mark);
        box.appendChild(pfEl('strong', '', config.emptyTitle));
        box.appendChild(pfEl('span', '', config.emptyHint));
        list.appendChild(box);
        return;
    }
    items.forEach((item) => {
        const card = pfEl('article', 'pf-entry');
        const head = pfEl('div', 'pf-entry-head');
        const copy = pfEl('div', '');
        copy.appendChild(pfEl('h3', 'pf-entry-title', config.title(item)));
        const meta = config.meta(item);
        if (meta) copy.appendChild(pfEl('p', 'pf-entry-meta', meta));
        const actions = pfEl('div', 'pf-entry-actions');
        const edit = pfEl('button', 'pf-text-btn', 'Edit');
        edit.type = 'button';
        edit.dataset.pfAction = config.edit;
        edit.dataset.pfId = item.id;
        const remove = pfEl('button', 'pf-text-btn pf-text-danger', 'Remove');
        remove.type = 'button';
        remove.dataset.pfAction = config.remove;
        remove.dataset.pfId = item.id;
        actions.append(edit, remove);
        head.append(copy, actions);
        card.appendChild(head);
        const body = config.body ? config.body(item) : '';
        if (body) card.appendChild(pfEl('p', 'pf-entry-body', body));
        list.appendChild(card);
    });
}

function pfMonthRange(item) {
    const start = pfFormatMonth(item.start_date);
    const end = item.current ? 'Present' : pfFormatMonth(item.end_date);
    return [start, end].filter(Boolean).join(' – ');
}

function pfYearRange(item) {
    return [item.start_year, item.end_year].filter(Boolean).join(' – ');
}

function pfFormatMonth(value) {
    if (!value || !/^\d{4}-\d{2}$/.test(value)) return '';
    const [year, month] = value.split('-');
    const index = Number(month) - 1;
    if (index < 0 || index > 11) return '';
    return `${PF_MONTHS[index]} ${year}`;
}

function pfRenderResume() {
    const title = document.getElementById('pf-dropzone-title');
    const hint = document.getElementById('pf-dropzone-hint');
    const input = document.getElementById('pf-resume-file');
    if (!title || !hint || !profileEditor.draft) return;
    if (profileEditor.uploading) {
        title.textContent = 'Reading your resume…';
        hint.textContent = 'This can take a moment.';
    } else if (profileEditor.draft.resume_filename) {
        title.textContent = profileEditor.draft.resume_filename;
        hint.textContent = 'Drop a new PDF here, or choose a file to replace it.';
    } else {
        title.textContent = 'Upload or replace your resume';
        hint.textContent = 'Drag and drop a PDF file here or click to browse';
    }
    if (input) input.disabled = profileEditor.uploading || profileEditor.saving;
}

function pfRenderCompletion() {
    const checks = pfCompletionChecks(profileEditor.draft);
    const done = checks.filter((item) => item.done).length;
    const percent = Math.round((done / checks.length) * 100);
    const label = document.getElementById('pf-complete-percent');
    const fill = document.getElementById('pf-complete-fill');
    if (label) label.textContent = `${percent}%`;
    if (fill) fill.style.width = `${percent}%`;
}

function pfRenderDirty() {
    const label = document.getElementById('pf-dirty');
    const saveLabel = document.getElementById('pf-save-label');
    const save = document.getElementById('pf-save');
    const discard = document.getElementById('pf-discard');
    const dirty = pfIsDirty();
    if (label) {
        label.hidden = !profileEditor.saving && !dirty;
        label.textContent = profileEditor.saving ? 'Saving…' : 'You have unsaved changes';
    }
    if (saveLabel) saveLabel.textContent = profileEditor.saving ? 'Saving…' : 'Save Changes';
    if (save) save.disabled = profileEditor.saving || profileEditor.uploading;
    if (discard) discard.disabled = profileEditor.saving || profileEditor.uploading;
}

function pfAddSkill() {
    const input = document.getElementById('pf-skill-input');
    const error = document.getElementById('pf-error-skills');
    const value = input.value.trim().replace(/\s+/g, ' ');
    if (!value) {
        if (error) error.textContent = 'Enter a skill to add it.';
        input.focus();
        return;
    }
    if (value.length > 40) {
        if (error) error.textContent = 'Each skill must be 40 characters or fewer.';
        return;
    }
    if (value.includes(',')) {
        if (error) error.textContent = 'Enter one skill at a time, without commas.';
        return;
    }
    if (profileEditor.draft.skills.some((skill) => skill.toLowerCase() === value.toLowerCase())) {
        if (error) error.textContent = 'That skill is already on your profile.';
        return;
    }
    if (profileEditor.draft.skills.length >= 40) {
        if (error) error.textContent = 'You can add up to 40 skills.';
        return;
    }
    profileEditor.draft.skills.push(value);
    input.value = '';
    if (error) error.textContent = '';
    pfRenderSkills();
    pfRenderCompletion();
    pfRenderDirty();
    input.focus();
}

function pfRemoveSkill(index) {
    profileEditor.draft.skills.splice(Number(index), 1);
    pfRenderSkills();
    pfRenderCompletion();
    pfRenderDirty();
}

function pfToggleForm(section) {
    const form = document.getElementById(pfFormId(section));
    const willOpen = form.classList.contains('hidden');
    pfCloseForm('experience');
    pfCloseForm('education');
    pfCloseForm('certification');
    if (!willOpen) return;
    profileEditor.editing = null;
    pfSetSubmitLabel(section, false);
    form.classList.remove('hidden');
    const first = form.querySelector('input, textarea');
    if (first) first.focus();
}

function pfCloseForm(section) {
    const form = document.getElementById(pfFormId(section));
    if (!form) return;
    form.classList.add('hidden');
    form.querySelectorAll('input, textarea').forEach((field) => {
        if (field.type === 'checkbox') field.checked = false;
        else field.value = '';
        field.disabled = false;
    });
    const error = form.querySelector('.pf-field-error');
    if (error) error.textContent = '';
    if (profileEditor.editing && profileEditor.editing.section === section) profileEditor.editing = null;
    pfSetSubmitLabel(section, false);
}

function pfFormId(section) {
    if (section === 'experience') return 'pf-experience-form';
    if (section === 'education') return 'pf-education-form';
    return 'pf-cert-form';
}

function pfSetSubmitLabel(section, editing) {
    const labels = {
        experience: ['Add experience', 'Update experience'],
        education: ['Add education', 'Update education'],
        certification: ['Add certification', 'Update certification'],
    };
    const ids = { experience: 'pf-exp-submit', education: 'pf-edu-submit', certification: 'pf-cert-submit' };
    const button = document.getElementById(ids[section]);
    if (button) button.textContent = labels[section][editing ? 1 : 0];
}

function pfFormError(id, message) {
    const node = document.getElementById(id);
    if (node) node.textContent = message || '';
    return !message;
}

function pfValidMonth(value) {
    return !value || /^\d{4}-(0[1-9]|1[0-2])$/.test(value);
}

function pfValidYear(value) {
    return !value || /^(19|20)\d{2}$/.test(value);
}

function pfSubmitExperience() {
    const role = document.getElementById('pf-exp-role').value.trim().replace(/\s+/g, ' ');
    const company = document.getElementById('pf-exp-company').value.trim().replace(/\s+/g, ' ');
    const start = document.getElementById('pf-exp-start').value;
    const current = document.getElementById('pf-exp-current').checked;
    const end = current ? '' : document.getElementById('pf-exp-end').value;
    const description = document.getElementById('pf-exp-description').value.trim();
    if (!role || !company) return pfFormError('pf-exp-error', 'Role and company are required.');
    if (role.length > 120 || company.length > 120) return pfFormError('pf-exp-error', 'Role and company must be 120 characters or fewer.');
    if (!pfValidMonth(start) || !pfValidMonth(end)) return pfFormError('pf-exp-error', 'Use a valid start and end month.');
    if (start && end && end < start) return pfFormError('pf-exp-error', 'End date must be the same month as the start date, or later.');
    if (description.length > 2000) return pfFormError('pf-exp-error', 'Description must be 2000 characters or fewer.');
    pfUpsert('experience_items', 'experience', {
        role, company, start_date: start, end_date: end, current, description,
    });
}

function pfSubmitEducation() {
    const school = document.getElementById('pf-edu-school').value.trim().replace(/\s+/g, ' ');
    const degree = document.getElementById('pf-edu-degree').value.trim().replace(/\s+/g, ' ');
    const field = document.getElementById('pf-edu-field').value.trim().replace(/\s+/g, ' ');
    const start = document.getElementById('pf-edu-start').value.trim();
    const end = document.getElementById('pf-edu-end').value.trim();
    if (!school || !degree) return pfFormError('pf-edu-error', 'School and degree are required.');
    if (!pfValidYear(start) || !pfValidYear(end)) return pfFormError('pf-edu-error', 'Years must be four digits, such as 2022.');
    if (start && end && Number(end) < Number(start)) return pfFormError('pf-edu-error', 'End year must be the same as the start year, or later.');
    pfUpsert('education_items', 'education', { school, degree, field, start_year: start, end_year: end });
}

function pfSubmitCertification() {
    const name = document.getElementById('pf-cert-name').value.trim().replace(/\s+/g, ' ');
    const issuer = document.getElementById('pf-cert-issuer').value.trim().replace(/\s+/g, ' ');
    const year = document.getElementById('pf-cert-year').value.trim();
    if (!name) return pfFormError('pf-cert-error', 'Certification name is required.');
    if (!pfValidYear(year)) return pfFormError('pf-cert-error', 'Year must be four digits, such as 2024.');
    pfUpsert('certifications', 'certification', { name, issuer, year });
}

function pfUpsert(listKey, section, values) {
    const list = profileEditor.draft[listKey];
    if (profileEditor.editing && profileEditor.editing.section === section) {
        const index = list.findIndex((item) => item.id === profileEditor.editing.id);
        if (index >= 0) list[index] = Object.assign({ id: profileEditor.editing.id }, values);
    } else {
        list.push(Object.assign({ id: pfId() }, values));
    }
    pfCloseForm(section);
    pfPaint();
}

function pfEditExperience(id) {
    const item = profileEditor.draft.experience_items.find((entry) => entry.id === id);
    if (!item) return;
    pfCloseForm('education');
    pfCloseForm('certification');
    profileEditor.editing = { section: 'experience', id };
    document.getElementById('pf-experience-form').classList.remove('hidden');
    document.getElementById('pf-exp-role').value = item.role || '';
    document.getElementById('pf-exp-company').value = item.company || '';
    document.getElementById('pf-exp-start').value = item.start_date || '';
    document.getElementById('pf-exp-current').checked = !!item.current;
    const end = document.getElementById('pf-exp-end');
    end.disabled = !!item.current;
    end.value = item.current ? '' : (item.end_date || '');
    document.getElementById('pf-exp-description').value = item.description || '';
    pfSetSubmitLabel('experience', true);
    document.getElementById('pf-exp-role').focus();
}

function pfEditEducation(id) {
    const item = profileEditor.draft.education_items.find((entry) => entry.id === id);
    if (!item) return;
    pfCloseForm('experience');
    pfCloseForm('certification');
    profileEditor.editing = { section: 'education', id };
    document.getElementById('pf-education-form').classList.remove('hidden');
    document.getElementById('pf-edu-school').value = item.school || '';
    document.getElementById('pf-edu-degree').value = item.degree || '';
    document.getElementById('pf-edu-field').value = item.field || '';
    document.getElementById('pf-edu-start').value = item.start_year || '';
    document.getElementById('pf-edu-end').value = item.end_year || '';
    pfSetSubmitLabel('education', true);
    document.getElementById('pf-edu-school').focus();
}

function pfEditCertification(id) {
    const item = profileEditor.draft.certifications.find((entry) => entry.id === id);
    if (!item) return;
    pfCloseForm('experience');
    pfCloseForm('education');
    profileEditor.editing = { section: 'certification', id };
    document.getElementById('pf-cert-form').classList.remove('hidden');
    document.getElementById('pf-cert-name').value = item.name || '';
    document.getElementById('pf-cert-issuer').value = item.issuer || '';
    document.getElementById('pf-cert-year').value = item.year || '';
    pfSetSubmitLabel('certification', true);
    document.getElementById('pf-cert-name').focus();
}

function pfRemoveItem(listKey, id) {
    profileEditor.draft[listKey] = profileEditor.draft[listKey].filter((item) => item.id !== id);
    if (profileEditor.editing && profileEditor.editing.id === id) {
        pfCloseForm(profileEditor.editing.section);
    }
    pfPaint();
}

function pfClearSummary(key) {
    profileEditor.draft[key] = '';
    pfPaint();
}

function pfPendingForm() {
    const sections = [
        ['experience', ['pf-exp-role', 'pf-exp-company', 'pf-exp-start', 'pf-exp-end', 'pf-exp-description']],
        ['education', ['pf-edu-school', 'pf-edu-degree', 'pf-edu-field', 'pf-edu-start', 'pf-edu-end']],
        ['certification', ['pf-cert-name', 'pf-cert-issuer', 'pf-cert-year']],
    ];
    return sections.some(([section, ids]) => {
        const form = document.getElementById(pfFormId(section));
        if (!form || form.classList.contains('hidden')) return false;
        return ids.some((id) => (document.getElementById(id).value || '').trim());
    });
}

function pfValidateIdentity() {
    pfReadIdentity();
    const draft = profileEditor.draft;
    const fields = {};
    const name = draft.full_name.trim().replace(/\s+/g, ' ');
    const title = draft.professional_title.trim().replace(/\s+/g, ' ');
    const email = draft.email.trim();
    draft.full_name = name;
    draft.professional_title = title;
    draft.email = email;
    if (name && (name.length > 80 || ![...name].every((ch) => ch.toLowerCase() !== ch.toUpperCase() || ch === ' ' || ".'-".includes(ch)))) {
        if (name.length > 80) fields.full_name = 'Name must be 80 characters or fewer.';
        else if (![...name].every((ch) => /\p{L}/u.test(ch) || ch === ' ' || ".'-".includes(ch))) {
            fields.full_name = 'Name can only include letters, spaces, apostrophes, periods, and hyphens.';
        }
    }
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        fields.email = 'Enter a valid email address.';
    }
    if (title.length > 120) fields.professional_title = 'Professional title must be 120 characters or fewer.';
    pfShowFieldErrors(fields);
    pfFillIdentity();
    return Object.keys(fields).length ? fields : null;
}

async function pfOnPhoto(event) {
    const file = event.target.files && event.target.files[0];
    event.target.value = '';
    if (!file) return;
    try {
        profileEditor.draft.profile_photo = await pfReadPhoto(file);
        pfRenderAvatar();
        pfRenderCompletion();
        pfRenderDirty();
        pfSetBanner('', 'success');
    } catch (err) {
        pfSetBanner(err.message || 'Could not use that photo.', 'error');
    }
}

function pfReadPhoto(file) {
    return new Promise((resolve, reject) => {
        if (!/^image\/(jpeg|png|webp)$/.test(file.type)) {
            reject(new Error('Use a JPG, PNG, or WebP photo.'));
            return;
        }
        if (file.size > 5 * 1024 * 1024) {
            reject(new Error('Profile photo must be 5 MB or smaller.'));
            return;
        }
        const image = new Image();
        const url = URL.createObjectURL(file);
        image.onload = () => {
            const scale = Math.min(1, 512 / Math.max(image.width, image.height));
            const canvas = document.createElement('canvas');
            canvas.width = Math.max(1, Math.round(image.width * scale));
            canvas.height = Math.max(1, Math.round(image.height * scale));
            canvas.getContext('2d').drawImage(image, 0, 0, canvas.width, canvas.height);
            URL.revokeObjectURL(url);
            resolve(canvas.toDataURL('image/jpeg', 0.86));
        };
        image.onerror = () => {
            URL.revokeObjectURL(url);
            reject(new Error('Could not read that photo.'));
        };
        image.src = url;
    });
}

async function pfUploadResume(file) {
    const input = document.getElementById('pf-resume-file');
    if (profileEditor.uploading || profileEditor.saving) return;
    const isPdf = file.type === 'application/pdf' || /\.pdf$/i.test(file.name);
    if (!isPdf) {
        pfSetStatus('Only PDF files are accepted.', 'error');
        showToast('Only PDF files are accepted.', 'error');
        if (input) input.value = '';
        return;
    }
    if (file.size > 5 * 1024 * 1024) {
        pfSetStatus('PDF must be 5 MB or smaller.', 'error');
        showToast('PDF must be 5 MB or smaller.', 'error');
        if (input) input.value = '';
        return;
    }
    if (pfIsDirty()) {
        const proceed = window.confirm('You have unsaved changes. Uploading a resume updates your skills and resume summaries now. Continue?');
        if (!proceed) {
            if (input) input.value = '';
            return;
        }
    }

    profileEditor.uploading = true;
    pfSetStatus('', '');
    pfRenderResume();
    pfRenderDirty();
    try {
        const body = new FormData();
        body.append('file', file);
        const response = await fetch(`${API_URL}/upload_resume`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${state.token}` },
            body,
        });
        let payload = {};
        try { payload = await response.json(); } catch (_) { payload = {}; }
        if (!response.ok) {
            const detail = payload.detail;
            throw new Error(typeof detail === 'string' ? detail : 'Resume upload failed.');
        }
        state.candidateProfileId = payload.id;
        state.profileData = payload;
        localStorage.setItem('candidateProfileId', payload.id);
        const account = await apiCall('/users/me');
        pfApplyAccount(account, { preserveEdits: true });
        pfSetStatus('Resume uploaded. Review the extracted details, then save any other changes.', 'success');
        showToast('Resume uploaded.');
    } catch (err) {
        if (err.message !== 'Session expired. Please log in again.') {
            pfSetStatus(err.message || 'Resume upload failed.', 'error');
            showToast(err.message || 'Resume upload failed.', 'error');
        }
    } finally {
        profileEditor.uploading = false;
        if (input) input.value = '';
        pfRenderResume();
        pfRenderDirty();
    }
}

function pfPayload() {
    const draft = profileEditor.draft;
    const strip = (item) => {
        const copy = Object.assign({}, item);
        delete copy.id;
        return copy;
    };
    return {
        full_name: draft.full_name,
        email: draft.email,
        professional_title: draft.professional_title,
        profile_photo: draft.profile_photo || '',
        skills: draft.skills,
        experience_items: draft.experience_items.map(strip),
        education_items: draft.education_items.map(strip),
        certifications: draft.certifications.map(strip),
        experience_summary: draft.experience_summary || '',
        education_summary: draft.education_summary || '',
    };
}

async function pfSave() {
    if (profileEditor.saving || profileEditor.uploading || !profileEditor.draft) return;
    if (pfPendingForm()) {
        pfSetBanner('Add or cancel the entry you started before saving.', 'error');
        return;
    }
    const identityErrors = pfValidateIdentity();
    if (identityErrors) {
        pfSetBanner('Please correct the highlighted fields.', 'error');
        return;
    }

    profileEditor.saving = true;
    pfRenderDirty();
    pfSetBanner('', 'success');
    try {
        const response = await fetch(`${API_URL}/my-profile`, {
            method: 'PUT',
            headers: {
                Authorization: `Bearer ${state.token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(pfPayload()),
        });
        let payload = {};
        try { payload = await response.json(); } catch (_) { payload = {}; }
        if (response.status === 401) {
            logout();
            return;
        }
        if (!response.ok) {
            const formatted = pfFormatApiError(payload);
            pfShowFieldErrors(formatted.fields);
            throw new Error(formatted.message);
        }
        pfApplyAccount(payload);
        if (typeof renderSidebar === 'function' && state.currentView) {
            renderSidebar(state.currentView);
            renderTopbar(state.currentView);
        }
        const notice = payload.notice ? ` ${payload.notice}` : '';
        pfSetBanner(`Profile saved.${notice}`, 'success');
        showToast('Profile saved.');
    } catch (err) {
        pfSetBanner(err.message || 'Could not save your profile.', 'error');
        showToast(err.message || 'Could not save your profile.', 'error');
    } finally {
        profileEditor.saving = false;
        pfRenderResume();
        pfRenderDirty();
    }
}

function pfDiscard() {
    if (profileEditor.saving || profileEditor.uploading) return;
    if (!pfIsDirty() && !pfPendingForm()) {
        pfSetBanner('There are no changes to discard.', 'success');
        return;
    }
    if (!window.confirm('Discard unsaved changes?')) return;
    profileEditor.draft = pfClone(profileEditor.saved);
    profileEditor.editing = null;
    pfCloseForm('experience');
    pfCloseForm('education');
    pfCloseForm('certification');
    pfShowFieldErrors({});
    pfPaint();
    pfSetBanner('Unsaved changes were discarded.', 'success');
}
