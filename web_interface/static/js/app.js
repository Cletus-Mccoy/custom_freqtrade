// --- Pairlist Create Modal Logic ---
document.addEventListener('DOMContentLoaded', function() {
    const createForm = document.getElementById('createPairlistForm');
    if (createForm) {
        createForm.addEventListener('submit', function(e) {
            e.preventDefault();
            createPairlistVisual();
        });
    }
});

// --- Consolidated Pairlist Creation Logic ---
window.createPairlistVisual = async function() {
    const name = document.getElementById('pairlistName').value.trim();
    let pairs = Array.from(document.querySelectorAll('#createPairChipsContainer .chip'))
        .map(chip => chip.textContent.trim())
        .filter(Boolean);
    const category = document.getElementById('categorySelect').value;
    // If JSON tab is active, sync from JSON editor
    const jsonTab = document.getElementById('create-json-tab');
    if (jsonTab && jsonTab.classList.contains('active')) {
        try {
            const obj = JSON.parse(document.getElementById('createJsonPairlistEditor').value);
            if (!Array.isArray(obj.pair_whitelist)) throw new Error('pair_whitelist must be an array');
            pairs = obj.pair_whitelist;
        } catch (e) {
            document.getElementById('createJsonValidationMsg').textContent = 'Invalid JSON: ' + e.message;
            document.getElementById('createJsonValidationMsg').style.display = 'block';
            return;
        }
    }
    // Validate filename
    if (!name.endsWith('.json')) {
        showError('Pairlist filename must end with .json');
        return;
    }
    // Check for duplicates in pairs
    const dupes = pairs.filter((v, i, a) => a.indexOf(v) !== i);
    if (dupes.length > 0) {
        showWarning('Duplicate pairs found: ' + [...new Set(dupes)].join(', '));
        // Remove duplicates for saving
        pairs = [...new Set(pairs)];
    }
    // Check for nesting/fragmentation
    if (pairs.some(p => Array.isArray(p) || typeof p === 'object')) {
        showError('Pairlist contains nested arrays or objects. Only flat arrays of strings are allowed.');
        return;
    }
    
    // Save new pairlist
    try {
            const response = await fetch(`/api/pairlist/${encodeURIComponent(name)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pairs: pairs, category: category })
            });
            const data = await response.json();
            if (data.success) {
                closeModalById('createPairlistModal');
                showSuccess('Pairlist created successfully!');
                refreshData();
            } else {
                showError('Failed to create pairlist: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            showError('Failed to create pairlist: ' + error.message);
        }
}


// --- Pairlist Create Modal Tab Sync Logic ---
document.addEventListener('DOMContentLoaded', function() {
    // Sync JSON editor when switching to JSON tab
    const jsonTab = document.getElementById('create-json-tab');
    if (jsonTab) {
        jsonTab.addEventListener('shown.bs.tab', function() {
            const pairs = Array.from(document.querySelectorAll('#createPairChipsContainer .chip'))
                .map(chip => chip.textContent.trim())
                .filter(Boolean);
            document.getElementById('createJsonPairlistEditor').value = JSON.stringify({ pair_whitelist: pairs }, null, 2);
        });
    }
    // Sync visual chips when switching to Visual tab
    const visualTab = document.getElementById('create-visual-tab');
    if (visualTab) {
        visualTab.addEventListener('shown.bs.tab', function() {
            try {
                const obj = JSON.parse(document.getElementById('createJsonPairlistEditor').value);
                if (Array.isArray(obj.pair_whitelist)) {
                    renderCreatePairChips(obj.pair_whitelist);
                }
            } catch {}
        });
    }
    // Live validate JSON editor
    const jsonEditor = document.getElementById('createJsonPairlistEditor');
    if (jsonEditor) {
        jsonEditor.addEventListener('input', function() {
            try {
                const obj = JSON.parse(this.value);
                if (!Array.isArray(obj.pair_whitelist)) throw new Error('pair_whitelist must be an array');
                document.getElementById('createJsonValidationMsg').style.display = 'none';
                renderCreatePairChips(obj.pair_whitelist);
            } catch (e) {
                document.getElementById('createJsonValidationMsg').textContent = 'Invalid JSON: ' + e.message;
                document.getElementById('createJsonValidationMsg').style.display = 'block';
            }
        });
    }
});
// --- Pairlist Category Modal Logic ---
let pairlistCategories = [];
let pairlistFileCategories = {};

// Utility: get category object by name (case-insensitive)
function getCategoryByName(name) {
    if (!pairlistCategories || !Array.isArray(pairlistCategories)) return null;
    return pairlistCategories.find(cat => cat.name.toLowerCase() === (name || '').toLowerCase());
}

// Utility: get color for a category name
function getCategoryColor(name) {
    const cat = getCategoryByName(name);
    return cat && cat.color ? cat.color : '#6c757d';
}

// Utility: render category filter buttons (for filter bar)
function renderCategoryFilterButtons() {
    const filterGroups = [
        document.getElementById('pairlistCategoryFilterGroup'),
        document.getElementById('pairlistCategoryFilterGroupMobile')
    ];
    filterGroups.forEach(group => {
        if (!group) return;
        group.innerHTML = '';
        // Always add 'All' button styled as solid dark
        const allBtn = document.createElement('button');
        allBtn.type = 'button';
        allBtn.className = 'btn category-filter-btn active';
        allBtn.setAttribute('data-category', 'all');
        allBtn.style.background = '#6c757d';
        allBtn.style.color = '#fff';
        allBtn.style.marginLeft = '2px';
        allBtn.textContent = 'All';
        group.appendChild(allBtn);
        // Add dynamic category buttons styled as solid with color background and white text
        (pairlistCategories || []).forEach(cat => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn category-filter-btn';
            btn.setAttribute('data-category', cat.name);
            btn.style.background = cat.color || '#6c757d';
            btn.style.color = '#fff';
            btn.style.marginLeft = '2px';
            btn.textContent = cat.name;
            group.appendChild(btn);
        });
    });
}

// NOTE: Modal category button rendering is handled by inline code in pairlists.html
// using PAIRLIST_CATEGORIES from server-side Jinja template rendering.
// This ensures buttons are rendered with correct IDs and up-to-date category data.

// Utility: get category for a pairlist file (using file_categories, default to 'custom')
function getFileCategory(filename) {
    if (pairlistFileCategories && typeof pairlistFileCategories === 'object' && filename in pairlistFileCategories) {
        return pairlistFileCategories[filename];
    }
    return 'custom';
}

async function loadPairlistCategories() {
    try {
        const res = await fetch('/config/user_config.json');
        if (!res.ok) throw new Error('Failed to load user_config.json');
        const userConfig = await res.json();
        if (userConfig && userConfig.pairlists && Array.isArray(userConfig.pairlists.categories)) {
            pairlistCategories = userConfig.pairlists.categories;
            pairlistFileCategories = userConfig.pairlists.file_categories || {};
        } else {
            pairlistCategories = [];
            pairlistFileCategories = {};
        }
    } catch (err) {
        pairlistCategories = [];
        pairlistFileCategories = {};
        console.error('Error loading pairlist categories:', err);
    }
    renderPairlistCategoryList();
    renderCategoryFilterButtons();
    setupCategoryFilter('pairlistCategoryFilterGroup');
    setupCategoryFilter('pairlistCategoryFilterGroupMobile');
}

function renderPairlistCategoryList() {
    const list = document.getElementById('pairlistCategoryList');
    list.innerHTML = '';
    pairlistCategories.forEach((cat, idx) => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex align-items-center sortable-category-item';
        li.setAttribute('draggable', 'true');
        li.setAttribute('data-category', cat.name);
        li.innerHTML = `
            <span class="drag-handle me-2"><i class="fas fa-grip-vertical"></i></span>
            <span class="category-color-dot me-2" style="width: 18px; height: 18px; border-radius: 50%; display: inline-block; background: ${cat.color || '#6c757d'};"></span>
            <span class="flex-grow-1 category-name">${cat.name}</span>
            <input type="color" class="form-control form-control-color ms-2 category-color-picker" value="${cat.color || '#6c757d'}" title="Pick color">
            <button class="btn btn-danger btn-sm ms-2 delete-category-btn"><i class="fas fa-trash"></i></button>
        `;
        // Color picker event
        li.querySelector('.category-color-picker').addEventListener('input', (e) => {
            cat.color = e.target.value;
            li.querySelector('.category-color-dot').style.background = cat.color;
        });
        // Delete button event
        li.querySelector('.delete-category-btn').addEventListener('click', () => {
            pairlistCategories.splice(idx, 1);
            renderPairlistCategoryList();
        });
        // Drag events
        li.addEventListener('dragstart', (e) => {
            li.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', idx);
        });
        li.addEventListener('dragend', () => {
            li.classList.remove('dragging');
        });
        li.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
        });
        li.addEventListener('drop', (e) => {
            e.preventDefault();
            const fromIdx = parseInt(e.dataTransfer.getData('text/plain'));
            const toIdx = idx;
            if (fromIdx !== toIdx) {
                const moved = pairlistCategories.splice(fromIdx, 1)[0];
                pairlistCategories.splice(toIdx, 0, moved);
                renderPairlistCategoryList();
            }
        });
        list.appendChild(li);
    });
}

async function savePairlistCategories() {
    // Save to user_config.json with NEW nested format
    try {
        // First load the current config to preserve other settings
        const currentResp = await fetch('/config/user_config.json');
        const currentConfig = await currentResp.json();
        
        // Update pairlists.categories with our changes
        currentConfig.pairlists = currentConfig.pairlists || {};
        currentConfig.pairlists.categories = pairlistCategories;
        currentConfig.pairlists.file_categories = currentConfig.pairlists.file_categories || pairlistFileCategories || {};
        
        // Ensure other sections exist
        currentConfig.strategies = currentConfig.strategies || {categories: [], file_categories: {}};
        currentConfig.configs = currentConfig.configs || {categories: [], file_categories: {}};
        currentConfig.global_settings = currentConfig.global_settings || {};
        
        // Save the complete config
        const resp = await fetch('/config/user_config.json', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentConfig)
        });
        
        if (!resp.ok) throw new Error('Failed to save categories');
        
        showSuccess('Categories saved successfully! Reloading page...');
        
        // Reload the page after a short delay so user sees success message
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    } catch (err) {
        showError('Failed to save categories: ' + err.message);
    }
}

function setupCategoryFilter(groupId) {
    const group = document.getElementById(groupId);
    if (!group) return;
    group.onclick = function(e) {
        if (e.target.classList.contains('category-filter-btn')) {
            // Remove active from all in both filter groups
            document.querySelectorAll('.category-filter-btn').forEach(btn => btn.classList.remove('active'));
            // Set active only on the clicked one
            e.target.classList.add('active');
            // Sync the other filter group
            const value = e.target.getAttribute('data-category');
            document.querySelectorAll('.category-filter-btn').forEach(btn => {
                if (btn.getAttribute('data-category') === value) btn.classList.add('active');
            });
            // Table rows
            const rows = document.querySelectorAll('#pairlistsTableBody tr');
            rows.forEach(row => {
                if (value === 'all' || row.getAttribute('data-category') === value) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
            // Card view
            const cards = document.querySelectorAll('.pairlist-card');
            cards.forEach(card => {
                if (value === 'all' || card.getAttribute('data-category') === value) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        }
    };
}

document.addEventListener('DOMContentLoaded', function() {
    // Only load categories if the pairlist category modal exists (i.e., on the pairlists page)
    if (document.getElementById('pairlistCategorySettingsModal')) {
        loadPairlistCategories();
    }

    // Load categories when modal is opened
    const modal = document.getElementById('pairlistCategorySettingsModal');
    if (modal) {
        modal.addEventListener('show.bs.modal', loadPairlistCategories);
    }
    // Add new category
    var addCatBtn = document.getElementById('addPairlistCategoryBtn');
    if (addCatBtn) {
        addCatBtn.addEventListener('click', function() {
            const name = document.getElementById('newPairlistCategoryName').value.trim();
            const color = document.getElementById('newPairlistCategoryColor').value;
            if (!name) return;
            if (pairlistCategories.some(c => c.name === name)) {
                showWarning('Category name already exists');
                return;
            }
            pairlistCategories.push({ name, color });
            document.getElementById('newPairlistCategoryName').value = '';
            renderPairlistCategoryList();
        });
    }
    // Save categories
    var saveCatBtn = document.getElementById('savePairlistCategoriesBtn');
    if (saveCatBtn) {
        saveCatBtn.addEventListener('click', async function() {
            await savePairlistCategories();
            // Optionally close modal
            const modalEl = document.getElementById('pairlistCategorySettingsModal');
            if (modalEl) bootstrap.Modal.getInstance(modalEl).hide();
        });
    }

    // --- Freqtrade API Key Management Logic ---
    let saveApiKeyBtn = document.getElementById('saveApiKeyBtn');
    let clearApiKeyBtn = document.getElementById('clearApiKeyBtn');
    let apiKeyFeedback = document.getElementById('apiKeyFeedback');
    let apiKeyList = document.getElementById('apiKeyList');
    // If apiKeyList is missing, create it in the DOM (as a fallback)
    if (!apiKeyList) {
        const settingsModal = document.getElementById('settingsModal');
        if (settingsModal) {
            const cardBodies = settingsModal.getElementsByClassName('card-body');
            if (cardBodies.length > 0) {
                apiKeyList = document.createElement('div');
                apiKeyList.id = 'apiKeyList';
                apiKeyList.className = 'mb-2';
                cardBodies[0].appendChild(apiKeyList);
            }
        }
    }
    function clearApiKeyFields() {
        document.getElementById('ftKeyName').value = '';
        document.getElementById('ftExchange').value = '';
        document.getElementById('ftApiKey').value = '';
        document.getElementById('ftApiSecret').value = '';
        apiKeyFeedback.innerHTML = '';
    }
    async function loadApiKeyList() {
        if (!apiKeyList) return;
        apiKeyList.innerHTML = '<span class="text-muted">Loading...</span>';
        try {
            const resp = await fetch('/api/ftapikeys');
            if (!resp.ok) throw new Error('Failed to load API keys');
            const data = await resp.json();
            if (!Array.isArray(data.keys) || !data.keys.length) {
                apiKeyList.innerHTML = '<span class="text-muted">No API keys saved.</span>';
                return;
            }
            apiKeyList.innerHTML = data.keys.map(k =>
                `<div class="d-flex align-items-center mb-1">
                    <span class="badge bg-primary me-2">${k.key_name}</span>
                    <span class="badge bg-secondary me-2">${k.exchange}</span>
                    <button class="btn btn-sm btn-danger ms-auto" onclick="deleteApiKey('${k.key_name}')"><i class="fas fa-trash"></i></button>
                </div>`
            ).join('');
        } catch (err) {
            apiKeyList.innerHTML = '<span class="text-danger">Failed to load API keys.</span>';
        }
    }
    window.deleteApiKey = async function(keyName) {
        if (!confirm('Delete API key "' + keyName + '"?')) return;
        try {
            const resp = await fetch('/api/ftapikeys/' + encodeURIComponent(keyName), { method: 'DELETE' });
            const data = await resp.json();
            if (data.success) {
                apiKeyFeedback.innerHTML = '<span class="text-success">API key deleted.</span>';
                loadApiKeyList();
            } else {
                apiKeyFeedback.innerHTML = '<span class="text-danger">Delete failed: ' + (data.error || 'Unknown error') + '</span>';
            }
        } catch (err) {
            apiKeyFeedback.innerHTML = '<span class="text-danger">Delete failed.</span>';
        }
    };
    if (saveApiKeyBtn) {
        saveApiKeyBtn.onclick = async function() {
            const key_name = document.getElementById('ftKeyName').value.trim();
            const exchange = document.getElementById('ftExchange').value.trim();
            const api_key = document.getElementById('ftApiKey').value.trim();
            const api_secret = document.getElementById('ftApiSecret').value.trim();
            if (!key_name || !exchange || !api_key || !api_secret) {
                apiKeyFeedback.innerHTML = '<span class="text-danger">All fields are required.</span>';
                return;
            }
            saveApiKeyBtn.disabled = true;
            apiKeyFeedback.innerHTML = '<span class="text-info">Saving...</span>';
            try {
                const resp = await fetch('/api/ftapikeys', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ key_name, exchange, api_key, api_secret })
                });
                const data = await resp.json();
                if (data.success) {
                    apiKeyFeedback.innerHTML = '<span class="text-success">API key saved.</span>';
                    clearApiKeyFields();
                    loadApiKeyList();
                } else {
                    apiKeyFeedback.innerHTML = '<span class="text-danger">Save failed: ' + (data.error || 'Unknown error') + '</span>';
                }
            } catch (err) {
                apiKeyFeedback.innerHTML = '<span class="text-danger">Save failed.</span>';
            }
            saveApiKeyBtn.disabled = false;
        };
    }
    if (clearApiKeyBtn) {
        clearApiKeyBtn.onclick = clearApiKeyFields;
    }
    // Always load API key list on page load
    loadApiKeyList();
});
// Download config file (identical to pairlist download)
window.downloadConfig = function(filename) {
    fetch(`/api/config/download/${filename}`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to download');
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        })
        .catch(() => alert('Failed to download config.'));
}
// Unified view/edit config modal logic has been moved to configs.js
// Config-related functionality has been moved to configs.js
async function viewEditConfig(filename) {
    console.warn('viewEditConfig has been moved to configs.js module');
    // Import and use the function from configs.js instead
    try {
        const configsModule = await import('./pages/configs.js');
        if (configsModule.viewEditConfig) {
            return configsModule.viewEditConfig(filename);
        }
    } catch (e) {
        console.error('Failed to import configs.js:', e);
    }
}
    // Config field handling moved to configs.js
    var saveBtn = document.getElementById('saveConfigBtn');
    if (saveBtn) saveBtn.classList.remove('d-none');
    var cancelBtn = document.getElementById('cancelEditConfigBtn');
    if (cancelBtn) cancelBtn.classList.remove('d-none');
    var editBtn = document.getElementById('editConfigBtn');
    if (editBtn) editBtn.classList.add('d-none');
    var modalElem = document.getElementById('viewEditConfigModal');
    if (modalElem) {
        var modal = new bootstrap.Modal(modalElem);
        modal.show();
    }

function cancelEditConfig() {
    if (configModalMode === 'edit' || configModalMode === 'clone') {
        // Return to view mode
        viewEditConfig(currentConfigFile);
    } else {
        // Just close modal for create
        bootstrap.Modal.getInstance(document.getElementById('viewEditConfigModal')).hide();
    }
}
// Patch saveConfig to restore button label after clone
// Configuration functionality has been moved to configs.js

// FreqTrade Web Interface JavaScript

// Global variables

// Notification stacking array (fix for missing declaration)
let activeNotifications = [];

// Easy/Expert config mode state
let configMode = 'easy'; // 'easy' or 'expert'
// Freqtrade config fields (partial, for demo; expand as needed)
const freqtradeConfigFields = [
    // Easy mode (required/common)
    { key: 'strategy', label: 'Strategy', required: true, type: 'text', easy: true },
    { key: 'exchange.name', label: 'Exchange', required: true, type: 'text', easy: true },
    { key: 'stake_currency', label: 'Stake Currency', required: true, type: 'text', easy: true },
    { key: 'stake_amount', label: 'Stake Amount', required: true, type: 'text', easy: true },
    { key: 'max_open_trades', label: 'Max Open Trades', required: true, type: 'number', easy: true },
    { key: 'dry_run', label: 'Dry Run', required: true, type: 'checkbox', easy: true },
    { key: 'minimal_roi', label: 'Minimal ROI', required: true, type: 'text', easy: true },
    { key: 'stoploss', label: 'Stoploss', required: true, type: 'text', easy: true },
    // Expert mode (all fields)
    { key: 'tradable_balance_ratio', label: 'Tradable Balance Ratio', required: false, type: 'text', easy: false },
    { key: 'available_capital', label: 'Available Capital', required: false, type: 'text', easy: false },
    { key: 'order_types', label: 'Order Types', required: false, type: 'text', easy: false },
    { key: 'order_time_in_force', label: 'Order Time In Force', required: false, type: 'text', easy: false },
    { key: 'exchange.key', label: 'Exchange API Key', required: false, type: 'text', easy: false },
    { key: 'exchange.secret', label: 'Exchange API Secret', required: false, type: 'text', easy: false },
    { key: 'exchange.pair_whitelist', label: 'Pair Whitelist', required: false, type: 'text', easy: false },
    { key: 'exchange.pair_blacklist', label: 'Pair Blacklist', required: false, type: 'text', easy: false },
    { key: 'telegram.enabled', label: 'Telegram Enabled', required: false, type: 'checkbox', easy: false },
    { key: 'webhook.enabled', label: 'Webhook Enabled', required: false, type: 'checkbox', easy: false },
    // ...add more fields as needed
];

function renderVisualConfigFields(configObj = {}) {
    const container = document.getElementById('visualConfigFields');
    if (!container) return;
    container.innerHTML = '';
    const fields = freqtradeConfigFields.filter(f => configMode === 'expert' || f.easy);
    fields.forEach(field => {
        const value = getConfigValue(configObj, field.key);
        const id = 'visual_' + field.key.replace(/\./g, '_');
        let html = `<div class="mb-2">`;
        html += `<label for="${id}" class="form-label">${field.label}`;
        if (field.required) html += ' <span class="text-danger">*</span>';
        html += `</label>`;
        if (field.type === 'checkbox') {
            html += `<input type="checkbox" class="form-check-input ms-2" id="${id}" ${value ? 'checked' : ''} ${configModalMode === 'view' ? 'disabled' : ''}>`;
        } else {
            html += `<input type="${field.type}" class="form-control" id="${id}" value="${value !== undefined ? value : ''}" ${configModalMode === 'view' ? 'readonly' : ''}>`;
        }
        html += `</div>`;
        container.innerHTML += html;
    });
}

// Expose for global use (for inline event handlers or other scripts)
window.renderVisualConfigFields = renderVisualConfigFields;

function getConfigValue(obj, key) {
    return key.split('.').reduce((o, k) => (o && o[k] !== undefined) ? o[k] : '', obj);
}

function setConfigValue(obj, key, value) {
    const keys = key.split('.');
    let o = obj;
    for (let i = 0; i < keys.length - 1; i++) {
        if (!o[keys[i]]) o[keys[i]] = {};
        o = o[keys[i]];
    }
    o[keys[keys.length - 1]] = value;
}

function updateJSONFromVisual() {
    // Build config object from visual fields
    let configObj = {};
    const fields = freqtradeConfigFields.filter(f => configMode === 'expert' || f.easy);
    fields.forEach(field => {
        const id = 'visual_' + field.key.replace(/\./g, '_');
        let value;
        if (field.type === 'checkbox') {
            value = document.getElementById(id).checked;
        } else {
            value = document.getElementById(id).value;
        }
        setConfigValue(configObj, field.key, value);
    });
    document.getElementById('viewEditConfigData').value = JSON.stringify(configObj, null, 2);
}

function setVisualFieldsFromConfig(configObj) {
    const fields = freqtradeConfigFields.filter(f => configMode === 'expert' || f.easy);
    fields.forEach(field => {
        const id = 'visual_' + field.key.replace(/\./g, '_');
        const value = getConfigValue(configObj, field.key);
        if (field.type === 'checkbox') {
            document.getElementById(id).checked = !!value;
        } else {
            document.getElementById(id).value = value !== undefined ? value : '';
        }
    });
}

function setJsonTemplate(mode) {
    let template = {};
    const fields = freqtradeConfigFields.filter(f => mode === 'expert' || f.easy);
    fields.forEach(field => {
        setConfigValue(template, field.key, field.type === 'checkbox' ? false : '');
    });
    document.getElementById('viewEditConfigData').value = JSON.stringify(template, null, 2);
}

document.addEventListener('DOMContentLoaded', function() {
    // Easy/Expert toggle logic (unified for both tabs)
    const easyBtn = document.getElementById('easyModeBtn');
    const expertBtn = document.getElementById('expertModeBtn');
    if (easyBtn && expertBtn) {
        easyBtn.onclick = function() {
            configMode = 'easy';
            easyBtn.classList.add('active');
            expertBtn.classList.remove('active');
            // Get current config from visual fields if possible, else from JSON
            let configObj = {};
            try {
                configObj = JSON.parse(document.getElementById('viewEditConfigData').value);
            } catch {}
            renderVisualConfigFields(configObj);
            // Update JSON textarea to match easy mode
            updateJSONFromVisual();
        };
        expertBtn.onclick = function() {
            configMode = 'expert';
            expertBtn.classList.add('active');
            easyBtn.classList.remove('active');
            let configObj = {};
            try {
                configObj = JSON.parse(document.getElementById('viewEditConfigData').value);
            } catch {}
            renderVisualConfigFields(configObj);
            updateJSONFromVisual();
        };
    }
});

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Load user preferences
    loadUserPreferences();
    
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize auto-refresh if enabled
    initializeAutoRefresh();
    
    // Add keyboard shortcuts
    addKeyboardShortcuts();
    
    // Initialize notification system
    initializeNotifications();
}

// User preferences
function loadUserPreferences() {
    const savedTheme = localStorage.getItem('freqtrade_theme');
    if (savedTheme) {
        document.body.setAttribute('data-theme', savedTheme);
    }
    // Add more user preference loading logic here as needed
}
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"], [title]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Auto-refresh functionality
let autoRefreshInterval = null;

function initializeAutoRefresh() {
    const autoRefreshEnabled = localStorage.getItem('freqtrade_auto_refresh') === 'true';
    if (autoRefreshEnabled) {
        enableAutoRefresh();
    }
}

function enableAutoRefresh() {
    if (autoRefreshInterval) return;
    
    autoRefreshInterval = setInterval(() => {
        refreshPageData();
    }, 30000); // Refresh every 30 seconds
    
    localStorage.setItem('freqtrade_auto_refresh', 'true');
    showNotification('Auto-refresh enabled', 'info');
}

function disableAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
    
    localStorage.setItem('freqtrade_auto_refresh', 'false');
    showNotification('Auto-refresh disabled', 'info');
}

function toggleAutoRefresh() {
    if (autoRefreshInterval) {
        disableAutoRefresh();
    } else {
        enableAutoRefresh();
    }
}

function refreshPageData() {
    // Only refresh if we're on a data-heavy page and not in a modal
    const modals = document.querySelectorAll('.modal.show');
    if (modals.length > 0) return;
    
    const currentPage = window.location.pathname;
    const refreshablePages = ['/', '/containers', '/strategies', '/pairlists', '/configs'];
    
    if (refreshablePages.includes(currentPage)) {
        if (currentPage === '/configs') {
            refreshConfigs();
        } else {
            softRefreshData();
        }
    }
}

// --- Configs Refresh Logic (consistent with pairlists) ---
// --- Configs Delete Logic (consistent with pairlists) ---
window.deleteConfig = async function(filename) {
    if (!filename) return;
    if (!confirm('Delete config file "' + filename + '"?')) return;
    try {
        const resp = await fetch('/api/config/' + encodeURIComponent(filename), { method: 'DELETE' });
        const data = await resp.json();
        if (data.success) {
            showSuccess('Config deleted.');
            refreshConfigs();
        } else {
            showError('Delete failed: ' + (data.error || 'Unknown error'));
        }
    } catch (err) {
        showError('Delete failed.');
    }
};
// Configuration table functionality has been moved to configs.js
// ...existing code...
// Remove stray bracket that caused syntax error

function softRefreshData() {
    // This would update specific components without a full page reload
    // For now, we'll just show a subtle indicator
    const indicator = document.createElement('div');
    indicator.className = 'position-fixed top-0 end-0 m-3 alert alert-info alert-dismissible fade show';
    indicator.style.zIndex = '9999';
    indicator.innerHTML = `
        <i class="fas fa-sync-alt fa-spin"></i> Refreshing data...
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(indicator);
    
    setTimeout(() => {
        if (indicator.parentNode) {
            indicator.remove();
        }
    }, 2000);
}

// Keyboard shortcuts
function addKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl+R or F5 - Refresh
        if ((e.ctrlKey && e.key === 'r') || e.key === 'F5') {
            e.preventDefault();
            location.reload();
        }
        
        // Ctrl+N - Create new (if on relevant page)
        if (e.ctrlKey && e.key === 'n') {
            const createBtn = document.querySelector('a[href*="create"], button[onclick*="create"]');
            if (createBtn) {
                e.preventDefault();
                createBtn.click();
            }
        }
        
        // Escape - Close modals
        if (e.key === 'Escape') {
            const openModals = document.querySelectorAll('.modal.show');
            openModals.forEach(modal => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            });
        }
        
        // Ctrl+A - Toggle auto-refresh
        if (e.ctrlKey && e.key === 'a' && !e.target.tagName.match(/INPUT|TEXTAREA|SELECT/)) {
            e.preventDefault();
            toggleAutoRefresh();
        }
    });
}

// Notification system
function initializeNotifications() {
    // Request notification permission if not already granted
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `notification alert alert-${type} alert-dismissible fade show position-fixed`;
    
    // Calculate vertical position for stacking
    const stackOffset = activeNotifications.length * 80; // 80px spacing between notifications
    
    notification.style.cssText = `
        top: ${20 + stackOffset}px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        max-width: 400px;
        background-color: white;
        border-left: 4px solid var(--bs-${type});
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border-radius: 0.375rem;
    `;
    
    const icon = getNotificationIcon(type);
    notification.innerHTML = `
        <i class="${icon}"></i> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Add to active notifications array
    activeNotifications.push(notification);
    
    document.body.appendChild(notification);
    
    // Auto-remove after duration
    setTimeout(() => {
        removeNotification(notification);
    }, duration);
    
    // Browser notification for important messages
    if (type === 'danger' || type === 'warning') {
        showBrowserNotification(message, type);
    }
}

function removeNotification(notification) {
    if (notification.parentNode) {
        notification.classList.remove('show');
        
        // Remove from active notifications array
        const index = activeNotifications.indexOf(notification);
        if (index > -1) {
            activeNotifications.splice(index, 1);
        }
        
        // Reposition remaining notifications
        repositionNotifications();
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 150);
    }
}

function repositionNotifications() {
    activeNotifications.forEach((notification, index) => {
        const stackOffset = index * 80;
        notification.style.top = `${20 + stackOffset}px`;
    });
}

function getNotificationIcon(type) {
    const icons = {
        'success': 'fas fa-check-circle',
        'danger': 'fas fa-exclamation-circle',
        'warning': 'fas fa-exclamation-triangle',
        'info': 'fas fa-info-circle',
        'primary': 'fas fa-bell'
    };
    return icons[type] || icons.info;
}

function showBrowserNotification(message, type) {
    if ('Notification' in window && Notification.permission === 'granted') {
        const title = type === 'danger' ? 'Error' : type === 'warning' ? 'Warning' : 'FreqTrade';
        new Notification(title, {
            body: message,
            icon: '/static/favicon.ico',
            tag: 'freqtrade-notification'
        });
    }
}

// Notification alias functions for compatibility
function showSuccess(message, duration = 5000) {
    showNotification(message, 'success', duration);
}

function showError(message, duration = 8000) {
    showNotification(message, 'danger', duration);
}

function showInfo(message, duration = 5000) {
    showNotification(message, 'info', duration);
}

function showWarning(message, duration = 6000) {
    showNotification(message, 'warning', duration);
}

// Utility functions
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function formatDuration(seconds) {
    const units = [
        { name: 'day', seconds: 86400 },
        { name: 'hour', seconds: 3600 },
        { name: 'minute', seconds: 60 },
        { name: 'second', seconds: 1 }
    ];
    
    for (const unit of units) {
        const count = Math.floor(seconds / unit.seconds);
        if (count > 0) {
            return `${count} ${unit.name}${count !== 1 ? 's' : ''}`;
        }
    }
    
    return '0 seconds';
}

function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

function formatPercentage(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'percent',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value / 100);
}

// Form validation helpers
function validateJSON(jsonString) {
    try {
        JSON.parse(jsonString);
        return { valid: true };
    } catch (error) {
        return { valid: false, error: error.message };
    }
}

// Configuration validation has been moved to configs.js
function validateConfigurationFile(config) {
    const errors = [];
    const warnings = [];
    
    // Required fields
    const requiredFields = ['strategy', 'exchange', 'timeframe'];
    requiredFields.forEach(field => {
        if (!config[field]) {
            errors.push(`Missing required field: ${field}`);
        }
    });
    
    // Exchange validation
    if (config.exchange) {
        if (!config.exchange.name) {
            errors.push('Exchange name is required');
        }
        
        if (!config.exchange.pair_whitelist || config.exchange.pair_whitelist.length === 0) {
            warnings.push('No trading pairs specified');
        }
    }
    
    return { errors, warnings };
}

// Loading states
function showLoadingSpinner(element) {
    const spinner = document.createElement('div');
    spinner.className = 'text-center';
    spinner.innerHTML = `
        <div class="spinner-border" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
    `;
    element.innerHTML = '';
    element.appendChild(spinner);
}

function hideLoadingSpinner(element) {
    const spinner = element.querySelector('.spinner-border');
    if (spinner) {
        spinner.parentNode.remove();
    }
}

// Search functionality
function initializeSearch(inputSelector, targetSelector) {
    const searchInput = document.querySelector(inputSelector);
    const targets = document.querySelectorAll(targetSelector);
    
    if (!searchInput || targets.length === 0) return;
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        
        targets.forEach(target => {
            const text = target.textContent.toLowerCase();
            const matches = text.includes(searchTerm);
            target.style.display = matches ? '' : 'none';
        });
    });
}

// Export functionality
function exportTableToCSV(tableSelector, filename) {
    const table = document.querySelector(tableSelector);
    if (!table) return;
    
    const rows = Array.from(table.querySelectorAll('tr'));
    const csv = rows.map(row => {
        const cells = Array.from(row.querySelectorAll('th, td'));
        return cells.map(cell => `"${cell.textContent.trim()}"`).join(',');
    }).join('\\n');
    
    downloadFile(csv, filename, 'text/csv');
}

function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// API helpers
async function fetchWithTimeout(url, options = {}, timeout = 10000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error('Request timeout');
        }
        throw error;
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
});

// Make functions globally available
window.FreqTradeApp = {
    // toggleTheme, // Removed to prevent ReferenceError
    toggleAutoRefresh,
    showNotification,
    formatBytes,
    formatDuration,
    formatCurrency,
    formatPercentage,
    validateJSON,
    validateConfigurationFile,
    exportTableToCSV,
    downloadFile,
    fetchWithTimeout,
    initializeSearch,
    showLoadingSpinner,
    hideLoadingSpinner
};
