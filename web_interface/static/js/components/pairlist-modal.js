import { PairlistService } from '../services/pairlist.service.js';
import { CategoryManager } from '../services/category.service.js';
import { PairChipsManager } from './pair-chips.js';

export class PairlistModal {
    constructor(options = {}) {
        this.modalId = options.modalId;
        this.modal = document.getElementById(this.modalId);
        this.pairChips = new PairChipsManager({
            containerId: options.pairChipsId,
            warningId: options.warningId,
            onChange: options.onPairsChange
        });
        this.currentFile = null;
        this.originalPairs = [];
        this.onSuccess = options.onSuccess || (() => {});
        this.categoryManager = new CategoryManager();
        this.setupEventListeners();
        this.setupCategoryPicker();
    }

    setupEventListeners() {
        if (!this.modal) return;

        // JSON validation on input
        const jsonEditor = this.modal.querySelector('.json-editor');
        if (jsonEditor) {
            jsonEditor.addEventListener('input', () => this.validateJson(jsonEditor.value));
        }

        // Tab switching
        const jsonTab = this.modal.querySelector('.json-tab');
        const visualTab = this.modal.querySelector('.visual-tab');
        if (jsonTab && visualTab) {
            jsonTab.addEventListener('shown.bs.tab', () => this.syncToJson());
            visualTab.addEventListener('shown.bs.tab', () => this.syncFromJson());
        }

        // Add pair input
        const addPairInput = this.modal.querySelector('.add-pair-input');
        if (addPairInput) {
            addPairInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const pair = addPairInput.value.trim();
                    if (pair) {
                        this.pairChips.addPair(pair);
                        addPairInput.value = '';
                    }
                }
            });
        }

        this.modal.addEventListener('shown.bs.modal', () => {
            this.pairChips.setReadOnly(false);
            this.pairChips.focus();
            this.updateCategoryPicker();
        });

        this.modal.addEventListener('hide.bs.modal', () => {
            this.resetModal();
        });
    }

    validateJson(jsonString) {
        try {
            const obj = JSON.parse(jsonString);
            if (!Array.isArray(obj.pair_whitelist)) {
                throw new Error('pair_whitelist must be an array');
            }
            this.setValidationMessage('');
            this.pairChips.setPairs(obj.pair_whitelist, true);
            return true;
        } catch (e) {
            this.setValidationMessage(`Invalid JSON: ${e.message}`);
            return false;
        }
    }

    setValidationMessage(message) {
        const msgElement = this.modal.querySelector('.json-validation-msg');
        if (msgElement) {
            msgElement.textContent = message;
            msgElement.style.display = message ? 'block' : 'none';
        }
    }

    syncToJson() {
        const jsonEditor = this.modal.querySelector('.json-editor');
        if (jsonEditor) {
            const pairs = this.pairChips.getPairs();
            jsonEditor.value = JSON.stringify({ pair_whitelist: pairs }, null, 2);
        }
    }

    syncFromJson() {
        const jsonEditor = this.modal.querySelector('.json-editor');
        if (jsonEditor && this.validateJson(jsonEditor.value)) {
            const obj = JSON.parse(jsonEditor.value);
            this.pairChips.setPairs(obj.pair_whitelist, true);
        }
    }

    getSelectedCategory() {
        const categorySelect = this.modal.querySelector('#categorySelect');
        return categorySelect ? categorySelect.value || 'custom' : 'custom';
    }

    async setupCategoryPicker() {
        await this.categoryManager.loadCategories();
        this.categorySelect = this.modal.querySelector('#categorySelect');
        if (!this.categorySelect) return;
        
        // Clear existing options
        this.categorySelect.innerHTML = '';
        
        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = 'custom';
        defaultOption.textContent = 'Custom';
        this.categorySelect.appendChild(defaultOption);
        
        // Add category options
        this.categoryManager.categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category.name;
            option.textContent = category.name;
            option.style.backgroundColor = category.color || '#6c757d';
            option.style.color = '#fff';
            this.categorySelect.appendChild(option);
        });
    }

    updateCategoryPicker() {
        if (!this.categorySelect) return;

        // Reset to default value
        this.categorySelect.value = 'custom';

        if (this.currentFile) {
            // Get the category for the current file
            const category = this.categoryManager.getFileCategory(this.currentFile);
            if (category) {
                this.categorySelect.value = category;
            }
        }
    }

    show() {
        if (this.modal) {
            const bsModal = new bootstrap.Modal(this.modal);
            bsModal.show();
        }
    }

    hide() {
        if (this.modal) {
            const bsModal = bootstrap.Modal.getInstance(this.modal);
            if (bsModal) bsModal.hide();
        }
    }
}

export class ViewEditPairlistModal extends PairlistModal {
    constructor() {
        super({
            modalId: 'viewEditPairlistModal',
            pairChipsId: 'pairChipsContainer',
            warningId: 'pairlistDuplicateWarning'
        });
        this.editMode = false;
    }

    async loadPairlist(filename) {
        try {
            const data = await PairlistService.getPairlist(filename);
            this.currentFile = filename;
            this.originalPairs = [...(data.pair_whitelist || data.pairs || [])];
            this.pairChips.setPairs(this.originalPairs, false);
            this.syncToJson();
            this.setEditMode(false);
            this.modal.querySelector('#viewEditPairlistTitle').textContent = `Pairlist: ${filename}`;
            this.modal.querySelector('#viewEditPairlistName').value = filename;
            
            // Update category picker
            await this.setupCategoryPicker();
            this.updateCategoryPicker();
            
            this.show();
        } catch (error) {
            console.error(error);
            alert(error.message);
        }
    }

    setEditMode(enabled) {
        this.editMode = enabled;
        this.modal.querySelector('#editPairlistBtn').classList.toggle('d-none', enabled);
        this.modal.querySelector('#savePairlistBtn').classList.toggle('d-none', !enabled);
        this.modal.querySelector('#cancelEditPairlistBtn').classList.toggle('d-none', !enabled);
        this.modal.querySelector('#addPairInput').classList.toggle('d-none', !enabled);
        this.modal.querySelector('#jsonPairlistEditor').readOnly = !enabled;
        this.pairChips.setEditable(enabled);
    }

    async save() {
        try {
            const pairs = this.pairChips.getPairs();
            const category = this.getSelectedCategory();
            await PairlistService.updatePairlist(this.currentFile, pairs, category);
            this.hide();
            this.onSuccess();
        } catch (error) {
            console.error(error);
            alert(error.message);
        }
    }

    cancel() {
        this.pairChips.setPairs(this.originalPairs, false);
        this.setEditMode(false);
        this.syncToJson();
        this.setValidationMessage('');
    }
}

export class CreatePairlistModal extends PairlistModal {
    constructor() {
        super({
            modalId: 'createPairlistModal',
            pairChipsId: 'createPairChipsContainer',
            warningId: 'createPairlistDuplicateWarning'
        });
    }

    async save() {
        try {
            const filename = this.modal.querySelector('#pairlistName').value.trim();
            if (!filename.endsWith('.json')) {
                throw new Error('Pairlist filename must end with .json');
            }
            const pairs = this.pairChips.getPairs();
            const category = this.getSelectedCategory();
            await PairlistService.createPairlist(filename, pairs, category);
            this.hide();
            this.onSuccess();
        } catch (error) {
            console.error(error);
            alert(error.message);
        }
    }
}