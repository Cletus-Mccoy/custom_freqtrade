import { DataTable } from '../components/data_table.js';
import { CategoryFilters } from '../components/category_filters.js';
import { PairlistService } from '../services/pairlist.service.js';
import { ViewEditPairlistModal } from '../components/pairlist-modal.js';
import { CategoryManager } from '../services/category.service.js';

export class PairlistsPage {
    constructor() {
        this.pairlistService = new PairlistService();
        this.viewEditModal = new ViewEditPairlistModal();
        this.categoryManager = new CategoryManager();
        
        // Set success callbacks
        this.viewEditModal.onSuccess = () => this.refreshData();
        
        // Initialize page
        this.init();
    }

    async init() {
        // Initialize categories first
        await this.categoryManager.loadCategories();
        
        // Setup the UI elements after categories are loaded
        this.categoryManager.renderCategoryFilterButtons();
        this.setupEventListeners();
        
        // Initial data load
        await this.refreshData();
    }

    setupEventListeners() {
        // Initialize category filters with the loaded categories
        const categoryFilters = new CategoryFilters({
            idPrefix: 'pairlist',
            categories: this.categoryManager.categories,
            onCategoryChange: (category) => this.handleCategoryFilter(category)
        });
        categoryFilters.init();

        // Initialize data table with category support
        this.dataTable = new DataTable({
            tableId: 'pairlistsTableBody',
            categoryEnabled: true,
            mobileView: true,
            onAction: (action, data) => this.handleTableAction(action, data),
            categoryManager: this.categoryManager
        });
        this.dataTable.init();

        // Reload button
        document.getElementById('reloadPairlistsBtn')?.addEventListener('click', 
            () => this.refreshData()
        );
    }

    handleTableAction(action, data) {
        // Add handler for category changes
        document.getElementById('managePairlistCategoriesBtn')?.addEventListener('click', 
            () => this.handleManageCategories()
        );
    }
    
    handleCategoryFilter(category) {
        if (this.dataTable) {
            this.dataTable.filterByCategory(category);
        }
    }

    handleTableAction(action, data) {
        switch(action) {
            case 'view':
                this.viewEditModal.loadPairlist(data.filename);
                break;
            case 'clone':
                this.clonePairlist(data.filename);
                break;
            case 'download':
                this.pairlistService.downloadPairlist(data.filename);
                break;
            case 'delete':
                this.confirmDeletePairlist(data.filename);
                break;
        }
    }

    async refreshData() {
        try {
            const pairlists = await this.pairlistService.getPairlists();
            this.renderPairlists(pairlists);
        } catch (error) {
            console.error(error);
            if (typeof showNotification === 'function') {
                showNotification(error.message, 'error');
            } else {
                alert(error.message);
            }
        }
    }

    async clonePairlist(filename) {
        try {
            const newName = filename.replace('.json', '') + '_copy.json';
            await this.pairlistService.clonePairlist(filename, newName);
            await this.refreshData();
        } catch (error) {
            console.error(error);
            if (typeof showNotification === 'function') {
                showNotification(error.message, 'error');
            } else {
                alert(error.message);
            }
        }
    }

    async confirmDeletePairlist(filename) {
        const confirmed = confirm(`Are you sure you want to delete ${filename}?`);
        if (confirmed) {
            try {
                await this.pairlistService.deletePairlist(filename);
                await this.refreshData();
            } catch (error) {
                console.error(error);
                if (typeof showNotification === 'function') {
                    showNotification(error.message, 'error');
                } else {
                    alert(error.message);
                }
            }
        }
    }

    renderPairlists(pairlists) {
        const tbody = document.getElementById('pairlistsTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';
        pairlists.forEach(pairlist => {
            const tr = document.createElement('tr');
            tr.setAttribute('data-category', pairlist.category);
            
            tr.innerHTML = `
                <td><strong>${pairlist.name}</strong></td>
                <td>${this.categoryManager.renderBadge(pairlist.category)}</td>
                <td><span class="badge bg-primary">${pairlist.pairs_count}</span></td>
                <td><code>${pairlist.filename}</code></td>
                <td>${pairlist.created || 'Unknown'}</td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-primary" data-action="view">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-success" data-action="clone">
                            <i class="fas fa-copy"></i>
                        </button>
                        <button class="btn btn-info" data-action="download">
                            <i class="fas fa-download"></i>
                        </button>
                        <button class="btn btn-danger" data-action="delete">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            `;

            // Add event listeners to action buttons
            tr.querySelectorAll('[data-action]').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.handleTableAction(btn.dataset.action, pairlist);
                });
            });

            tbody.appendChild(tr);
        });
    }
}

// Initialize the page when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.pairlistsPage = new PairlistsPage();
    window.pairlistsPage.refreshData(); // Initial load
});