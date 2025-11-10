import { ConfigService } from '../services/config.service.js';

class ConfigsPage {
    constructor() {
        this.configService = new ConfigService();
        this.currentConfig = null;
        this.editMode = false;
        this.visualMode = 'easy'; // 'easy' or 'expert'
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Modal events
        document.getElementById('editConfigBtn')?.addEventListener('click', () => this.enableConfigEditing());
        document.getElementById('saveConfigBtn')?.addEventListener('click', () => this.saveConfig());
        document.getElementById('cancelEditConfigBtn')?.addEventListener('click', () => this.cancelEditConfig());
        document.getElementById('viewEditConfigName')?.addEventListener('input', () => this.checkDuplicateConfigName());

        // Visual/JSON tab switching
        document.getElementById('visual-config-tab')?.addEventListener('click', () => this.updateJsonFromVisual());
        document.getElementById('json-config-tab')?.addEventListener('click', () => this.updateVisualFromJson());

        // Easy/Expert mode switching
        document.getElementById('visualEasyBtn')?.addEventListener('click', () => this.setVisualMode('easy'));
        document.getElementById('visualExpertBtn')?.addEventListener('click', () => this.setVisualMode('expert'));

        // Visual fields form
        document.getElementById('visualConfigForm')?.addEventListener('input', () => this.updateJsonFromVisual());

        // JSON editor input
        document.getElementById('viewEditConfigData')?.addEventListener('input', () => {
            try {
                const jsonContent = document.getElementById('viewEditConfigData').value;
                JSON.parse(jsonContent); // Test if valid JSON
                this.updateVisualFromJson();
            } catch (error) {
                // Ignore JSON parse errors while typing
            }
        });

        // Category filter buttons
        const filterGroup = document.getElementById('configCategoryFilterGroup');
        if (filterGroup) {
            filterGroup.querySelectorAll('.config-category-filter-btn').forEach(btn => {
                btn.addEventListener('click', () => this.filterConfigs(btn.dataset.category));
            });
        }
    }

    /**
     * Set visual mode (easy/expert)
     */
    setVisualMode(mode) {
        this.visualMode = mode;
        const easyBtn = document.getElementById('visualEasyBtn');
        const expertBtn = document.getElementById('visualExpertBtn');

        if (mode === 'easy') {
            easyBtn.classList.add('btn-primary');
            easyBtn.classList.remove('btn-secondary');
            expertBtn.classList.remove('btn-primary');
            expertBtn.classList.add('btn-secondary');
        } else {
            expertBtn.classList.add('btn-primary');
            expertBtn.classList.remove('btn-secondary');
            easyBtn.classList.remove('btn-primary');
            easyBtn.classList.add('btn-secondary');
        }

        this.renderVisualConfigFields();
        this.updateJsonFromVisual();
    }

    /**
     * Get a value from a nested object using dot notation
     */
    getConfigValue(obj, key) {
        return key.split('.').reduce((o, i) => o?.[i], obj);
    }

    /**
     * Set a value in a nested object using dot notation
     */
    setConfigValue(obj, key, value) {
        const keys = key.split('.');
        const last = keys.pop();
        const parent = keys.reduce((o, i) => o[i] = o[i] || {}, obj);
        parent[last] = value;
        return obj;
    }

    /**
     * Update visual fields from JSON content
     */
    updateVisualFromJson() {
        try {
            const jsonContent = document.getElementById('viewEditConfigData').value;
            const config = JSON.parse(jsonContent);
            this.renderVisualConfigFields(config);
        } catch (error) {
            if (typeof showNotification === 'function') {
                showNotification('Invalid JSON format', 'error');
            } else {
                alert('Invalid JSON format');
            }
        }
    }

    /**
     * Update JSON content from visual fields
     */
    updateJsonFromVisual() {
        const form = document.getElementById('visualConfigForm');
        const config = {};

        // Collect values from form fields
        form.querySelectorAll('[data-config-field]').forEach(field => {
            const key = field.dataset.configField;
            let value = field.value;

            // Convert value types
            if (field.type === 'number') {
                value = Number(value);
            } else if (field.type === 'checkbox') {
                value = field.checked;
            } else if (value.toLowerCase() === 'true') {
                value = true;
            } else if (value.toLowerCase() === 'false') {
                value = false;
            }

            this.setConfigValue(config, key, value);
        });

        // Update JSON editor
        document.getElementById('viewEditConfigData').value = JSON.stringify(config, null, 2);
    }

    /**
     * Filter configs by category
     */
    filterConfigs(category) {
        const items = document.querySelectorAll('[data-category]');
        items.forEach(item => {
            const itemCategory = item.dataset.category.toLowerCase();
            if (category === 'all' || itemCategory === category.toLowerCase()) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    }

    /**
     * Render visual configuration fields
     */
    renderVisualConfigFields(configObj = {}) {
        const form = document.getElementById('visualConfigForm');
        if (!form) return;

        const fields = this.visualMode === 'easy' ? this.getEasyModeFields() : this.getExpertModeFields();
        
        form.innerHTML = fields.map(field => {
            const value = this.getConfigValue(configObj, field.key) ?? field.default;
            return this.renderConfigField(field, value);
        }).join('\n');
    }

    /**
     * Get field definitions for easy mode
     */
    getEasyModeFields() {
        return [
            { key: 'max_open_trades', label: 'Max Open Trades', type: 'number', default: 3 },
            { key: 'stake_currency', label: 'Stake Currency', type: 'text', default: 'USDT' },
            { key: 'stake_amount', label: 'Stake Amount', type: 'text', default: 'unlimited' },
            { key: 'timeframe', label: 'Timeframe', type: 'select', options: ['1m', '5m', '15m', '1h', '4h', '1d'], default: '5m' },
            { key: 'dry_run', label: 'Dry Run', type: 'checkbox', default: true },
            { key: 'exchange.name', label: 'Exchange', type: 'select', options: ['binance', 'kucoin', 'huobi'], default: 'binance' }
        ];
    }

    /**
     * Get field definitions for expert mode
     */
    getExpertModeFields() {
        return [
            ...this.getEasyModeFields(),
            { key: 'tradable_balance_ratio', label: 'Tradable Balance Ratio', type: 'number', step: '0.01', default: 0.99 },
            { key: 'cancel_open_orders_on_exit', label: 'Cancel Open Orders on Exit', type: 'checkbox', default: false },
            { key: 'trading_mode', label: 'Trading Mode', type: 'select', options: ['spot', 'futures'], default: 'spot' },
            { key: 'margin_mode', label: 'Margin Mode', type: 'select', options: ['none', 'cross', 'isolated'], default: 'none' },
            { key: 'unfilledtimeout.entry', label: 'Entry Timeout (minutes)', type: 'number', default: 10 },
            { key: 'unfilledtimeout.exit', label: 'Exit Timeout (minutes)', type: 'number', default: 10 },
            { key: 'entry_pricing.price_side', label: 'Entry Price Side', type: 'select', options: ['same', 'other'], default: 'same' },
            { key: 'exit_pricing.price_side', label: 'Exit Price Side', type: 'select', options: ['same', 'other'], default: 'same' }
        ];
    }

    /**
     * Render a single configuration field
     */
    renderConfigField(field, value) {
        const id = field.key.replace(/\./g, '-');
        let input;

        switch (field.type) {
            case 'select':
                input = `
                    <select class="form-control" id="${id}" data-config-field="${field.key}" ${this.editMode ? '' : 'disabled'}>
                        ${field.options.map(opt => `
                            <option value="${opt}" ${opt === value ? 'selected' : ''}>${opt}</option>
                        `).join('')}
                    </select>`;
                break;

            case 'checkbox':
                input = `
                    <div class="form-check">
                        <input type="checkbox" class="form-check-input" id="${id}" data-config-field="${field.key}"
                            ${value ? 'checked' : ''} ${this.editMode ? '' : 'disabled'}>
                    </div>`;
                break;

            default:
                input = `
                    <input type="${field.type}" class="form-control" id="${id}" data-config-field="${field.key}"
                        value="${value}" ${field.step ? `step="${field.step}"` : ''} ${this.editMode ? '' : 'disabled'}>`;
        }

        return `
            <div class="mb-3">
                <label for="${id}" class="form-label">${field.label}</label>
                ${input}
            </div>`;
    }

    /**
     * Enable editing mode for config
     */
    enableConfigEditing() {
        this.editMode = true;
        document.getElementById('viewEditConfigData').readOnly = false;
        document.getElementById('editConfigBtn').classList.add('d-none');
        document.getElementById('saveConfigBtn').classList.remove('d-none');
        document.getElementById('cancelEditConfigBtn').classList.remove('d-none');

        // Enable visual fields
        const form = document.getElementById('visualConfigForm');
        if (form) {
            form.querySelectorAll('input, select').forEach(field => field.disabled = false);
        }
    }

    /**
     * Cancel config editing
     */
    cancelEditConfig() {
        this.editMode = false;
        document.getElementById('viewEditConfigData').readOnly = true;
        document.getElementById('editConfigBtn').classList.remove('d-none');
        document.getElementById('saveConfigBtn').classList.add('d-none');
        document.getElementById('cancelEditConfigBtn').classList.add('d-none');

        // Disable visual fields
        const form = document.getElementById('visualConfigForm');
        if (form) {
            form.querySelectorAll('input, select').forEach(field => field.disabled = true);
        }
    }

    /**
     * Check for duplicate config names
     */
    async checkDuplicateConfigName() {
        const nameField = document.getElementById('viewEditConfigName');
        const saveBtn = document.getElementById('saveConfigBtn');
        const validationMsg = document.getElementById('configJsonValidationMsg');

        if (!nameField || !saveBtn) return;

        const name = nameField.value.trim();
        if (!name) {
            validationMsg.textContent = 'Configuration name is required.';
            validationMsg.style.display = 'block';
            saveBtn.disabled = true;
            return;
        }

        try {
            const configs = await this.configService.getConfigs();
            const isDuplicate = configs.some(config => 
                config.filename.toLowerCase() === (name + '.json').toLowerCase() &&
                config.filename !== this.currentConfig
            );

            if (isDuplicate) {
                validationMsg.textContent = 'A configuration with this name already exists.';
                validationMsg.style.display = 'block';
                saveBtn.disabled = true;
            } else {
                validationMsg.style.display = 'none';
                saveBtn.disabled = false;
            }
        } catch (error) {
            console.error('Error checking for duplicate names:', error);
        }
    }

    /**
     * Save config changes
     */
    async saveConfig() {
        const nameField = document.getElementById('viewEditConfigName');
        const contentField = document.getElementById('viewEditConfigData');
        const validationMsg = document.getElementById('configJsonValidationMsg');

        try {
            const content = contentField.value;
            JSON.parse(content); // Validate JSON

            const name = nameField.value.trim();
            if (!name) {
                throw new Error('Configuration name is required.');
            }

            const filename = name.endsWith('.json') ? name : name + '.json';
            await this.configService.updateConfig(filename, content);
            
            // Close modal and wait before reloading
            const modalEl = document.getElementById('viewEditConfigModal');
            if (modalEl) {
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) {
                    modal.hide();
                    // Wait for modal to close before reloading
                    modalEl.addEventListener('hidden.bs.modal', () => {
                        window.location.reload();
                    }, { once: true });
                }
            }
        } catch (error) {
            validationMsg.textContent = error.message;
            validationMsg.style.display = 'block';
        }
    }

    /**
     * View or edit a config
     */
    async viewEditConfig(filename) {
        try {
            this.currentConfig = filename;
            const config = await this.configService.getConfig(filename);
            
            document.getElementById('viewEditConfigTitle').textContent = 'View/Edit Configuration';
            document.getElementById('viewEditConfigName').value = filename.replace('.json', '');
            document.getElementById('viewEditConfigData').value = JSON.stringify(config, null, 2);
            
            // Reset edit state
            this.cancelEditConfig();

            // Update visual fields
            this.renderVisualConfigFields(config);
            
            const modal = new bootstrap.Modal(document.getElementById('viewEditConfigModal'));
            modal.show();
        } catch (error) {
            if (typeof showNotification === 'function') {
                showNotification(error.message, 'error');
            } else {
                alert(error.message);
            }
        }
    }

    /**
     * Create a new config
     */
    createConfig() {
        this.currentConfig = null;
        document.getElementById('viewEditConfigTitle').textContent = 'Create Configuration';
        document.getElementById('viewEditConfigName').value = '';

        const defaultConfig = {
            "max_open_trades": 3,
            "stake_currency": "USDT",
            "stake_amount": "unlimited",
            "tradable_balance_ratio": 0.99,
            "timeframe": "5m",
            "dry_run": true,
            "cancel_open_orders_on_exit": false,
            "trading_mode": "spot",
            "margin_mode": "none",
            "unfilledtimeout": {
                "entry": 10,
                "exit": 10,
                "exit_timeout_count": 0,
                "unit": "minutes"
            },
            "entry_pricing": {
                "price_side": "same",
                "use_order_book": true,
                "order_book_top": 1,
                "price_last_balance": 0.0,
                "check_depth_of_market": {
                    "enabled": false,
                    "bids_to_ask_delta": 1
                }
            },
            "exit_pricing": {
                "price_side": "same",
                "use_order_book": true,
                "order_book_top": 1
            },
            "exchange": {
                "name": "binance",
                "key": "",
                "secret": "",
                "pair_whitelist": [],
                "ccxt_config": {},
                "ccxt_async_config": {},
                "pair_blacklist": []
            }
        };

        document.getElementById('viewEditConfigData').value = JSON.stringify(defaultConfig, null, 2);

        // Enable editing for new configs
        this.editMode = true;
        document.getElementById('viewEditConfigData').readOnly = false;
        document.getElementById('viewEditConfigName').readOnly = false;
        document.getElementById('editConfigBtn').classList.add('d-none');
        document.getElementById('saveConfigBtn').classList.remove('d-none');
        document.getElementById('cancelEditConfigBtn').classList.remove('d-none');

        // Update visual fields
        this.renderVisualConfigFields(defaultConfig);

        const modal = new bootstrap.Modal(document.getElementById('viewEditConfigModal'));
        modal.show();
    }

    /**
     * Clone an existing config
     */
    async cloneConfig(filename) {
        try {
            const newName = filename.replace('.json', '') + '_copy.json';
            await this.configService.cloneConfig(filename, newName);
            window.location.reload();
        } catch (error) {
            if (typeof showNotification === 'function') {
                showNotification(error.message, 'error');
            } else {
                alert(error.message);
            }
        }
    }

    /**
     * Delete a config
     */
    async deleteConfig(filename) {
        try {
            await this.configService.deleteConfig(filename);
            window.location.reload();
        } catch (error) {
            if (typeof showNotification === 'function') {
                showNotification(error.message, 'error');
            } else {
                alert(error.message);
            }
        }
    }

    /**
     * Download a config
     */
    downloadConfig(filename) {
        this.configService.downloadConfig(filename).catch(error => {
            if (typeof showNotification === 'function') {
                showNotification(error.message, 'error');
            } else {
                alert(error.message);
            }
        });
    }

    /**
     * Handle config file upload
     */
    async handleUpload() {
        const fileInput = document.getElementById('uploadConfigFile');
        const category = document.getElementById('uploadConfigCategory')?.value || 'custom';

        if (!fileInput?.files.length) {
            if (typeof showNotification === 'function') {
                showNotification('Please select a file to upload.', 'error');
            } else {
                alert('Please select a file to upload.');
            }
            return;
        }

        try {
            await this.configService.uploadConfig(fileInput.files[0], category);
            
            // Close modal and wait before reloading
            const modalEl = document.getElementById('uploadConfigModal');
            if (modalEl) {
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) {
                    modal.hide();
                    // Wait for modal to close before reloading
                    modalEl.addEventListener('hidden.bs.modal', () => {
                        window.location.reload();
                    }, { once: true });
                }
            }
        } catch (error) {
            if (typeof showNotification === 'function') {
                showNotification(error.message, 'error');
            } else {
                alert(error.message);
            }
        }
    }
}

// Initialize the page
document.addEventListener('DOMContentLoaded', () => {
    const configsPage = new ConfigsPage();

    // Expose necessary functions to the global scope for inline event handlers
    window.viewEditConfig = (filename) => configsPage.viewEditConfig(filename);
    window.createConfig = () => configsPage.createConfig();
    window.cloneConfig = (filename) => configsPage.cloneConfig(filename);
    window.deleteConfig = (filename) => configsPage.deleteConfig(filename);
    window.downloadConfig = (filename) => configsPage.downloadConfig(filename);
    window.submitUploadConfig = () => configsPage.handleUpload();
});