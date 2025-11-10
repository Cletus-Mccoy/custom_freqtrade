// Category management utility functions
export class CategoryManager {
    constructor() {
        this.categories = [];
        this.fileCategories = {};
    }

    async loadCategories() {
        try {
            const res = await fetch('/config/user_config.json');
            if (!res.ok) throw new Error('Failed to load categories');
            const userConfig = await res.json();
            
            if (userConfig?.pairlists?.categories) {
                this.categories = userConfig.pairlists.categories;
            } else {
                this.categories = [];
            }
            
            if (userConfig?.pairlists?.file_categories) {
                this.fileCategories = userConfig.pairlists.file_categories;
            } else {
                this.fileCategories = {};
            }
        } catch (err) {
            console.error('Error loading categories:', err);
            this.categories = [];
            this.fileCategories = {};
        }
    }

    getCategoryByName(name) {
        if (!this.categories || !Array.isArray(this.categories)) return null;
        return this.categories.find(cat => 
            cat.name.toLowerCase() === (name || '').toLowerCase()
        );
    }

    getCategoryColor(name) {
        const cat = this.getCategoryByName(name);
        return cat?.color || '#6c757d';
    }

    getFileCategory(filename) {
        if (this.fileCategories && typeof this.fileCategories === 'object' && 
            filename in this.fileCategories) {
            return this.fileCategories[filename];
        }
        return 'custom';
    }

    async saveCategories() {
        try {
            const resp = await fetch('/config/user_config.json', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    pairlist_categories: this.categories,
                    pairlist_file_categories: this.fileCategories 
                })
            });
            if (!resp.ok) throw new Error('Failed to save categories');
            return true;
        } catch (err) {
            console.error('Failed to save categories:', err);
            return false;
        }
    }

    renderCategoryFilterButtons(groupIds = ['categoryFilterGroup', 'categoryFilterGroupMobile']) {
        groupIds.forEach(groupId => {
            const group = document.getElementById(groupId);
            if (!group) return;
            
            group.innerHTML = '';
            
            // Add 'All' button
            const allBtn = document.createElement('button');
            allBtn.type = 'button';
            allBtn.className = 'btn category-filter-btn active';
            allBtn.setAttribute('data-category', 'all');
            allBtn.style.background = '#6c757d';
            allBtn.style.color = '#fff';
            allBtn.style.marginLeft = '2px';
            allBtn.textContent = 'All';
            group.appendChild(allBtn);
            
            // Add category buttons
            this.categories.forEach(cat => {
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

    setupCategoryFilter(groupId) {
        const group = document.getElementById(groupId);
        if (!group) return;

        group.addEventListener('click', (e) => {
            const btn = e.target.closest('.category-filter-btn');
            if (!btn) return;

            const category = btn.getAttribute('data-category');
            const items = document.querySelectorAll('[data-category]');
            
            // Update button states
            group.querySelectorAll('.category-filter-btn').forEach(b => 
                b.classList.toggle('active', b === btn)
            );
            
            // Filter items
            items.forEach(item => {
                if (category === 'all' || item.getAttribute('data-category') === category) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }
}