// --- Pairlist Create Modal Logic ---

// Global notification stack
const activeNotifications = [];
document.addEventListener('DOMContentLoaded', function() {
    const createForm = document.getElementById('createPairlistForm');
    if (createForm) {
        createForm.addEventListener('submit', function(e) {
            e.preventDefault();
            createPairlistVisual();
        });
    }
        // Ensure categories are loaded and picker is rendered when create modal is opened
        const createModal = document.getElementById('createPairlistModal');
        if (createModal) {
            createModal.addEventListener('show.bs.modal', async function() {
                // Always reload categories from config for freshness
                await loadPairlistCategories();
                renderCategorySelectButtons('createPairlistCategoryGroup', 'createPairlistCategory');
            });
        }
});

// --- Consolidated Pairlist Creation Logic ---
window.createPairlistVisual = async function() {
    const name = document.getElementById('pairlistName').value.trim();
    let pairs = Array.from(document.querySelectorAll('#createPairChipsContainer .chip'))
        .map(chip => chip.textContent.trim())
        .filter(Boolean);
    const category = document.getElementById('createPairlistCategory').value;
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
    // Check for filename conflict
    let conflict = false;
    try {
        const resp = await fetch(`/api/pairlist/${encodeURIComponent(name)}`);
        if (resp.ok) conflict = true;
    } catch {}
    if (conflict) {
        showPairlistConflictModal(name, pairs, category);
    } else {
        saveUploadedPairlist(name, pairs, false, category);
    }
};

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
        document.getElementById('categoryFilterGroup'),
        document.getElementById('categoryFilterGroupMobile')
    ];
    filterGroups.forEach(group => {
        if (!group) return;
        group.innerHTML = '';
        // Always add 'All' button styled as outline-secondary
        const allBtn = document.createElement('button');
        allBtn.type = 'button';
        allBtn.className = 'btn btn-outline-secondary category-filter-btn active';
        allBtn.setAttribute('data-category', 'all');
        allBtn.textContent = 'All';
        group.appendChild(allBtn);
        // Add dynamic category buttons styled as filled with color and white text
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

// Utility: render category select buttons (for modals) and set up picker
function renderCategorySelectButtons(groupId, inputId, initialValue = 'custom') {
    const group = document.getElementById(groupId);
    const input = document.getElementById(inputId);
    if (!group || !input) return;
    group.innerHTML = '';
    (pairlistCategories || []).forEach(cat => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn category-select-btn w-20';
        btn.setAttribute('data-value', cat.name);
        btn.style.background = cat.color || '#6c757d';
        btn.style.color = '#fff';
        btn.textContent = cat.name;
        group.appendChild(btn);
    });
    // Set up picker logic and initial value
    setTimeout(() => {
        if (typeof setupCategoryPicker === 'function') {
            setupCategoryPicker(groupId, inputId, initialValue);
        }
    }, 0);
}

async function loadPairlistCategories() {
    try {
        const resp = await fetch('/config/user_config.json');
        if (!resp.ok) throw new Error('Failed to load user_config.json');
        const data = await resp.json();
        // Support both formats: { pairlist_categories: [{name,color},...] } and { categories: [...], category_colors: {...} }
        if (Array.isArray(data.pairlist_categories)) {
            pairlistCategories = data.pairlist_categories;
        } else if (Array.isArray(data.categories) && typeof data.category_colors === 'object') {
            pairlistCategories = data.categories.map(cat => ({ name: cat, color: data.category_colors[cat] || '#6c757d' }));
        } else {
            pairlistCategories = [];
        }
    } catch (err) {
        pairlistCategories = [];
    }
    renderPairlistCategoryList();
    renderCategoryFilterButtons();
    setupCategoryFilter('categoryFilterGroup');
    setupCategoryFilter('categoryFilterGroupMobile');
    renderCategorySelectButtons('pairlistCategoryGroup', 'pairlistCategory', 'custom');
    renderCategorySelectButtons('clonePairlistCategoryGroup', 'clonePairlistCategory', 'custom');
    renderCategorySelectButtons('uploadPairlistCategoryGroup', 'uploadPairlistCategory', 'custom');
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
    // Save to user_config.json
    try {
        const resp = await fetch('/config/user_config.json', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pairlist_categories: pairlistCategories })
        });
        if (!resp.ok) throw new Error('Failed to save categories');
        showSuccess('Categories saved');
        // Refresh category list, filters, and selectors
        await loadPairlistCategories();
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
    // Load categories and render filter bar on page load
    loadPairlistCategories();

    // Load categories when modal is opened
    const modal = document.getElementById('pairlistCategorySettingsModal');
    if (modal) {
        modal.addEventListener('show.bs.modal', loadPairlistCategories);
    }
    // Add new category
    document.getElementById('addPairlistCategoryBtn').addEventListener('click', function() {
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
    // Save categories
    document.getElementById('savePairlistCategoriesBtn').addEventListener('click', async function() {
        await savePairlistCategories();
        // Optionally close modal
        const modalEl = document.getElementById('pairlistCategorySettingsModal');
        if (modalEl) bootstrap.Modal.getInstance(modalEl).hide();
    });
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
// Unified view/edit config modal logic (mirroring pairlists)
window.viewEditConfig = async function viewEditConfig(filename) {
    configModalMode = 'view';
    currentConfigFile = filename;
    document.getElementById('viewEditConfigTitle').textContent = 'Configuration: ' + filename;
    // Always set the config name field and make it readonly (like pairlists)
    var nameField = document.getElementById('viewEditConfigName');
    if (nameField) {
        nameField.value = filename;
        nameField.readOnly = true;
    }
    document.getElementById('viewEditConfigData').readOnly = true;
    document.getElementById('visualStrategy').readOnly = true;
    document.getElementById('visualTimeframe').readOnly = true;
    document.getElementById('visualExchange').readOnly = true;
    document.getElementById('visualPairs').readOnly = true;
    // Hide Save/Cancel, show Edit
    document.getElementById('saveConfigBtn').classList.add('d-none');
    document.getElementById('cancelEditConfigBtn').classList.add('d-none');
    document.getElementById('editConfigBtn').classList.remove('d-none');
    // Hide validation messages
    const configJsonValidationMsg = document.getElementById('configJsonValidationMsg');
    if (configJsonValidationMsg) configJsonValidationMsg.style.display = 'none';
    try {
        const resp = await fetch(`/api/config/${encodeURIComponent(filename)}`);
        if (!resp.ok) throw new Error('Failed to load config');
        const data = await resp.json();
        resetConfigTabsAndFields('edit', data);
    } catch (err) {
        document.getElementById('viewEditConfigData').value = 'Error loading configuration: ' + err.message;
    }
    var modal = new bootstrap.Modal(document.getElementById('viewEditConfigModal'));
    modal.show();
}

function enableConfigEditing() {
    configModalMode = 'edit';
    // Always keep config name readonly in edit mode (like pairlists)
    var nameField = document.getElementById('viewEditConfigName');
    if (nameField) {
        nameField.readOnly = true;
    }
    document.getElementById('viewEditConfigData').readOnly = false;
    document.getElementById('visualStrategy').readOnly = false;
    document.getElementById('visualTimeframe').readOnly = false;
    document.getElementById('visualExchange').readOnly = false;
    document.getElementById('visualPairs').readOnly = false;
    document.getElementById('saveConfigBtn').classList.remove('d-none');
    document.getElementById('cancelEditConfigBtn').classList.remove('d-none');
    document.getElementById('editConfigBtn').classList.add('d-none');
}
// --- Config Modal Visual/JSON Tab Logic ---
// --- Configs Modal Logic ---
let configModalMode = 'view'; // 'view', 'edit', 'create', 'upload'
let currentConfigFile = null;


function resetConfigTabsAndFields(mode, configObj) {
    // Always show and activate the visual/json tabs
    const visualTab = document.getElementById('visual-config-tab');
    const jsonTab = document.getElementById('json-config-tab');
    const visualContent = document.getElementById('visual-config-content');
    const jsonContent = document.getElementById('json-config-content');
    if (visualTab && jsonTab && visualContent && jsonContent) {
        visualTab.classList.add('active');
        jsonTab.classList.remove('active');
        visualContent.classList.add('show', 'active');
        jsonContent.classList.remove('show', 'active');
    }
    // Set fields
    if (mode === 'create') {
        document.getElementById('mainConfigNameRow').style.display = 'none';
        document.getElementById('configCategory').value = 'custom';
        const defaultConfig = {};
        document.getElementById('viewEditConfigData').value = JSON.stringify(defaultConfig, null, 2);
        renderVisualConfigFields(defaultConfig);
    } else if (mode === 'edit' && configObj) {
        document.getElementById('mainConfigNameRow').style.display = '';
        document.getElementById('viewEditConfigName').value = configObj.filename || configObj.name || '';
        document.getElementById('viewEditConfigName').readOnly = true;
        document.getElementById('configCategory').value = configObj.category || 'custom';
        document.getElementById('viewEditConfigData').value = JSON.stringify(configObj, null, 2);
        renderVisualConfigFields(configObj);
    }
    // Hide validation/duplication messages
    const configJsonValidationMsg = document.getElementById('configJsonValidationMsg');
    if (configJsonValidationMsg) configJsonValidationMsg.style.display = 'none';
    const configNameDuplicateMsg = document.getElementById('configNameDuplicateMsg');
    if (configNameDuplicateMsg) configNameDuplicateMsg.style.display = 'none';
}
// End of FreqTradeApp global assignment

function createConfig() {
    configModalMode = 'create';
    currentConfigFile = null;
    document.getElementById('viewEditConfigTitle').textContent = 'Create Configuration';
    document.getElementById('viewEditConfigName').readOnly = false;
    document.getElementById('viewEditConfigData').readOnly = false;
    document.getElementById('visualStrategy').readOnly = false;
    document.getElementById('visualTimeframe').readOnly = false;
    document.getElementById('visualExchange').readOnly = false;
    document.getElementById('visualPairs').readOnly = false;
    document.getElementById('saveConfigBtn').classList.remove('d-none');
    document.getElementById('cancelEditConfigBtn').classList.remove('d-none');
    document.getElementById('editConfigBtn').classList.add('d-none');
    resetConfigTabsAndFields('create');
}

async function editConfig(btn) {
    configModalMode = 'edit';
    const config = JSON.parse(btn.getAttribute('data-config'));
    currentConfigFile = config.filename;
    document.getElementById('viewEditConfigTitle').textContent = 'Edit Configuration';
    document.getElementById('viewEditConfigName').readOnly = false;
    document.getElementById('viewEditConfigData').readOnly = false;
    document.getElementById('visualStrategy').readOnly = false;
    document.getElementById('visualTimeframe').readOnly = false;
    document.getElementById('visualExchange').readOnly = false;
    document.getElementById('visualPairs').readOnly = false;
    document.getElementById('saveConfigBtn').classList.remove('d-none');
    document.getElementById('cancelEditConfigBtn').classList.remove('d-none');
    document.getElementById('editConfigBtn').classList.add('d-none');
    // Show loading state
    document.getElementById('viewEditConfigData').value = 'Loading...';
    try {
        const resp = await fetch(`/api/config/${encodeURIComponent(config.filename)}`);
        if (!resp.ok) throw new Error('Failed to load config');
        const data = await resp.json();
        // Set fields from loaded file
        resetConfigTabsAndFields('edit', data);
    } catch (err) {
        document.getElementById('viewEditConfigData').value = 'Error loading configuration: ' + err.message;
    }
}


// --- Pairlist Upload & Conflict Validation Logic ---
function uploadPairlist() {
    const fileInput = document.getElementById('uploadPairlistFile');
    if (!fileInput.files.length) {
        showError('Please select a pairlist file to upload.');
        return;
    }
    const file = fileInput.files[0];
    const reader = new FileReader();
    reader.onload = async function(e) {
        let json;
        try {
            json = JSON.parse(e.target.result);
        } catch (err) {
            showError('Invalid JSON: ' + err.message);
            return;
        }
        // Validate structure: must be array or object with pair_whitelist
        let pairs = [];
        if (Array.isArray(json)) {
            pairs = json;
        } else if (json.pair_whitelist && Array.isArray(json.pair_whitelist)) {
            pairs = json.pair_whitelist;
        } else {
            showError('Invalid pairlist structure. Must be an array or object with pair_whitelist.');
            return;
        }
        // Check for fragmentation/nesting
        if (pairs.some(p => Array.isArray(p) || typeof p === 'object')) {
            showError('Pairlist contains nested arrays or objects. Only flat arrays of strings are allowed.');
            return;
        }
        // Check for duplicates
        const dupes = pairs.filter((v, i, a) => a.indexOf(v) !== i);
        if (dupes.length > 0) {
            showWarning('Duplicate pairs found: ' + [...new Set(dupes)].join(', '));
        }
        // Check for filename conflict (simulate by checking DOM or fetch)
        const name = file.name;
        let conflict = false;
        try {
            const resp = await fetch(`/api/pairlist/${encodeURIComponent(name)}`);
            if (resp.ok) conflict = true;
        } catch {}
        if (conflict) {
            showPairlistConflictModal(name, pairs);
        } else {
            saveUploadedPairlist(name, pairs);
        }
    };
    reader.readAsText(file);
}

function showPairlistConflictModal(name, pairs) {
    // Create or reuse a modal for conflict resolution
    let modal = document.getElementById('pairlistConflictModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'pairlistConflictModal';
        modal.className = 'modal fade';
        modal.tabIndex = -1;
        modal.innerHTML = `
        <div class="modal-dialog">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">Pairlist Conflict</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <p>A pairlist named <b>${name}</b> already exists. What would you like to do?</p>
              <ul>
                <li><b>Overwrite</b>: Replace the existing file.</li>
                <li><b>Append Unique</b>: Add only new pairs (no duplicates).</li>
                <li><b>Cancel</b>: Abort upload.</li>
              </ul>
            </div>
            <div class="modal-footer">
              <button id="overwritePairlistBtn" class="btn btn-danger">Overwrite</button>
              <button id="appendPairlistBtn" class="btn btn-primary">Append Unique</button>
              <button class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            </div>
          </div>
        </div>`;
        document.body.appendChild(modal);
    }
    // Attach event listeners
    let category = arguments.length > 2 ? arguments[2] : (document.getElementById('pairlistCategory') ? document.getElementById('pairlistCategory').value : 'custom');
    setTimeout(() => {
        document.getElementById('overwritePairlistBtn').onclick = function() {
            saveUploadedPairlist(name, pairs, true, category);
            bootstrap.Modal.getInstance(modal).hide();
        };
        document.getElementById('appendPairlistBtn').onclick = async function() {
            // Fetch existing, merge unique
            let existing = [];
            try {
                const resp = await fetch(`/api/pairlist/${encodeURIComponent(name)}`);
                if (resp.ok) {
                    const data = await resp.json();
                    if (Array.isArray(data)) existing = data;
                    else if (data.pair_whitelist) existing = data.pair_whitelist;
                }
            } catch {}
            const merged = Array.from(new Set([...existing, ...pairs]));
            saveUploadedPairlist(name, merged, true, category);
            bootstrap.Modal.getInstance(modal).hide();
        };
    }, 300);
    new bootstrap.Modal(modal).show();
}

async function saveUploadedPairlist(name, pairs, overwrite=false) {
    try {
        let category = arguments.length > 3 ? arguments[3] : (document.getElementById('pairlistCategory') ? document.getElementById('pairlistCategory').value : 'custom');
        const resp = await fetch(`/api/pairlist/${encodeURIComponent(name)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pair_whitelist: pairs, category })
        });
        const data = await resp.json();
        if (data.success) {
            showSuccess(`Pairlist "${name}" uploaded${overwrite ? ' (overwritten)' : ''} successfully.`);
            if (typeof refreshData === 'function') refreshData();
        } else {
            showError('Failed to upload pairlist: ' + (data.error || 'Unknown error'));
        }
    } catch (err) {
        showError('Error uploading pairlist: ' + err.message);
    }
}

// For legacy config upload, keep the old function (if needed)
function uploadConfig() {
    configModalMode = 'upload';
    currentConfigFile = null;
    document.getElementById('uploadConfigFile').value = '';
    document.getElementById('uploadConfigSection').style.display = '';
    document.getElementById('configEditorTabsContainer').style.display = 'none';
    document.getElementById('mainConfigNameRow').style.display = 'none';
    document.getElementById('mainConfigCategoryRow').style.display = 'none';
    document.getElementById('validateConfigBtn').classList.add('d-none');
    document.getElementById('saveConfigBtn').classList.add('d-none');
    document.getElementById('uploadConfigBtn').classList.remove('d-none');
    document.getElementById('viewEditConfigTitle').textContent = 'Upload Configuration';
    var modal = new bootstrap.Modal(document.getElementById('viewEditConfigModal'));
    modal.show();
}

// Optionally, attach uploadPairlist to a button:
// document.getElementById('uploadPairlistBtn').onclick = uploadPairlist;

window.cloneConfig = async function cloneConfig(filename) {
    configModalMode = 'clone';
    currentConfigFile = null;
    document.getElementById('viewEditConfigTitle').textContent = 'Clone Configuration';
    var nameField = document.getElementById('viewEditConfigName');
    try {
        const resp = await fetch(`/api/config/${encodeURIComponent(filename)}`);
        if (!resp.ok) throw new Error('Failed to load config');
        const config = await resp.json();
        // Always show the filename in the Configuration Name field, with _copy
        let baseName = config.filename ? config.filename.replace(/(\.json)?$/, '') : (config.name || '');
        if (nameField) {
            nameField.value = baseName + '_copy.json';
            nameField.readOnly = true;
        }
        document.getElementById('configCategory').value = config.category || 'custom';
        document.getElementById('viewEditConfigData').value = JSON.stringify(config, null, 2);
        resetConfigTabsAndFields('create', config);
    } catch (err) {
        document.getElementById('viewEditConfigData').value = 'Error loading configuration: ' + err.message;
    }
    document.getElementById('viewEditConfigData').readOnly = false;
    document.getElementById('visualStrategy').readOnly = false;
    document.getElementById('visualTimeframe').readOnly = false;
    document.getElementById('visualExchange').readOnly = false;
    document.getElementById('visualPairs').readOnly = false;
    document.getElementById('saveConfigBtn').classList.remove('d-none');
    document.getElementById('cancelEditConfigBtn').classList.remove('d-none');
    document.getElementById('editConfigBtn').classList.add('d-none');
    var modal = new bootstrap.Modal(document.getElementById('viewEditConfigModal'));
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
window.saveConfig = async function() {
    const name = document.getElementById('viewEditConfigName').value.trim();
    let configText = document.getElementById('viewEditConfigData').value;
    if (!name) {
        showError('Please enter a configuration name');
        return;
    }
    // If in visual mode, update JSON from visual settings first
    const visualTab = document.getElementById('visual-config-tab');
    if (visualTab && visualTab.classList.contains('active')) {
        // Visual tab is active, sync JSON
        if (typeof updateJSONFromVisual === 'function') updateJSONFromVisual();
        configText = document.getElementById('viewEditConfigData').value;
    }
    let data;
    try {
        data = JSON.parse(configText);
    } catch (error) {
        showError('Invalid JSON format: ' + error.message);
        return;
    }
    // Save to server (POST for new, PUT for edit)
    let method = 'POST';
    let url = '/api/configs';
    if (configModalMode === 'edit') {
        method = 'PUT';
        url = `/api/config/${encodeURIComponent(name)}`;
    }
    try {
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (result.success) {
            showSuccess(`Configuration "${name}" saved successfully`);
            bootstrap.Modal.getInstance(document.getElementById('viewEditConfigModal')).hide();
            setTimeout(() => refreshConfigs(), 500);
        } else {
            showError('Failed to save configuration: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        showError('Error saving configuration: ' + error.message);
    }
// FreqTrade Web Interface JavaScript

// Global variables

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
}

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
        currentTheme = savedTheme;
        applyTheme(currentTheme);
    }
    
    const autoRefresh = localStorage.getItem('freqtrade_auto_refresh');
    if (autoRefresh === 'true') {
        enableAutoRefresh();
    }
}

function saveUserPreferences() {
    localStorage.setItem('freqtrade_theme', currentTheme);
}

// Theme management
function toggleTheme() {
    currentTheme = currentTheme === 'light' ? 'dark' : 'light';
    applyTheme(currentTheme);
    saveUserPreferences();
}

function applyTheme(theme) {
    const body = document.body;
    const navbar = document.querySelector('.navbar');
    
    if (theme === 'dark') {
        body.classList.add('bg-dark-mode');
        if (navbar) {
            navbar.classList.remove('navbar-dark', 'bg-dark');
            navbar.classList.add('navbar-dark', 'bg-secondary');
        }
    } else {
        body.classList.remove('bg-dark-mode');
        if (navbar) {
            navbar.classList.remove('navbar-dark', 'bg-secondary');
            navbar.classList.add('navbar-dark', 'bg-dark');
        }
    }
}

// Tooltip initialization
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
async function refreshConfigs() {
    try {
        showLoadingSpinner(document.getElementById('configsTableBody'));
        const response = await fetchWithTimeout('/api/configs', {}, 10000);
        if (!response.ok) throw new Error('Failed to fetch configs');
        const data = await response.json();
        renderConfigsTable(data.configs || []);
        showSuccess('Configurations refreshed');
    } catch (err) {
        showError('Could not refresh configs: ' + err.message);
    }
}

function renderConfigsTable(configs) {
    const tbody = document.getElementById('configsTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (!configs.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">No configuration files found</td></tr>';
        return;
    }
        for (const config of configs) {
            if (!config.category) config.category = pairlistCategories.length ? pairlistCategories[0].name : 'Uncategorized';
            const tr = document.createElement('tr');
            tr.setAttribute('data-category', config.category.toLowerCase());
            const color = getCategoryColor(config.category);
            tr.innerHTML = `
                <td>${config.name || ''}</td>
                <td><span class="badge" style="background:${color};color:#fff;">${config.category.charAt(0).toUpperCase() + config.category.slice(1)}</span></td>
                <td>${config.strategy || '-'}</td>
                <td>${config.pair_count || '-'}</td>
                <td>
                    <div class="d-flex gap-2 flex-wrap">
                        <button class="btn btn-sm btn-light border text-primary d-flex align-items-center px-2 py-1" data-bs-toggle="modal" data-bs-target="#viewEditConfigModal" data-config='${JSON.stringify(config)}' onclick='editConfig(this)' title="View/Edit">
                            <i class="fas fa-eye me-1"></i> View/Edit
                        </button>
                        <button class="btn btn-sm btn-light border text-success d-flex align-items-center px-2 py-1" title="Clone" onclick="cloneConfig(this)" data-config='${JSON.stringify(config)}' data-bs-toggle="modal" data-bs-target="#viewEditConfigModal">
                            <i class="fas fa-clone me-1"></i> Clone
                        </button>
                        <button class="btn btn-sm btn-light border text-secondary d-flex align-items-center px-2 py-1" onclick="downloadConfig('${config.filename}')" title="Download">
                            <i class="fas fa-download me-1"></i> Download
                        </button>
                        <button class="btn btn-sm btn-light border text-danger d-flex align-items-center px-2 py-1" onclick="deleteConfig('${config.filename}')" title="Delete">
                            <i class="fas fa-trash me-1"></i> Delete
                        </button>
                    </div>
                </td>
            `;
        tbody.appendChild(tr);
    }
}

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
    toggleTheme,
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
