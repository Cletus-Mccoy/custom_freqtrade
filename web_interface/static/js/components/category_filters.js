// category_filters.js - Category filtering functionality
export class CategoryFilters {
    constructor(options = {}) {
        this.options = {
            idPrefix: '',
            defaultColor: '#6c757d',
            categories: [],
            onCategoryChange: null,
            ...options
        };
        this.categories = this.options.categories;
        this.fileCategories = {};
    }

    // Initialize category filters
    init() {
        // Use provided categories if available
        if (this.options.categories) {
            this.categories = this.options.categories;
        }
        this.renderFilterButtons();
        this.setupEventListeners();
    }

    // Render category filter buttons
    renderFilterButtons() {
        const filterGroups = [
            document.getElementById(`${this.options.idPrefix}CategoryFilterGroup`),
            document.getElementById(`${this.options.idPrefix}CategoryFilterGroupMobile`)
        ];

        filterGroups.forEach(group => {
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
                btn.style.background = cat.color || this.options.defaultColor;
                btn.style.color = '#fff';
                btn.style.marginLeft = '2px';
                btn.textContent = cat.name;
                group.appendChild(btn);
            });
        });

        this.setupFilterHandlers();
    }

    // Set up click handlers for filter buttons
    setupFilterHandlers() {
        const groups = [
            document.getElementById(`${this.options.idPrefix}CategoryFilterGroup`),
            document.getElementById(`${this.options.idPrefix}CategoryFilterGroupMobile`)
        ];

        groups.forEach(group => {
            if (!group) return;
            
            group.addEventListener('click', (e) => {
                if (e.target.classList.contains('category-filter-btn')) {
                    const category = e.target.getAttribute('data-category');
                    this.filterByCategory(category);
                    
                    // Update active state
                    group.querySelectorAll('.category-filter-btn').forEach(btn => {
                        btn.classList.toggle('active', btn.getAttribute('data-category') === category);
                    });
                }
            });
        });
    }

    // Filter items by category
    filterByCategory(category) {
        const items = document.querySelectorAll('.pairlist-row, .pairlist-card');
        items.forEach(item => {
            if (category === 'all' || item.getAttribute('data-category') === category) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    }

    // Get category color by name
    getCategoryColor(name) {
        const category = this.categories.find(cat => 
            cat.name.toLowerCase() === (name || '').toLowerCase()
        );
        return category ? category.color : this.options.defaultColor;
    }

    // Setup event listeners
    setupEventListeners() {
        // Add any additional event listeners here
    }
}