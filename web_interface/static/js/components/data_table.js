// data_table.js - Data table component functionality
export class DataTable {
    constructor(options = {}) {
        this.options = {
            tableId: '',
            categoryEnabled: false,
            mobileView: false,
            onAction: null,
            rowFormatter: null,
            mobileCardFormatter: null,
            ...options
        };
        
        this.tableBody = document.getElementById(this.options.tableId);
        this.mobileContainer = this.options.mobileView ? 
            document.getElementById(`${this.options.tableId}_mobile`) : null;
    }

    // Initialize the table
    init() {
        if (!this.tableBody) {
            console.error(`Table body with id "${this.options.tableId}" not found`);
            return;
        }
        this.setupEventListeners();
    }

    // Render table data
    render(data) {
        if (!Array.isArray(data)) {
            console.error('Data must be an array');
            return;
        }

        // Clear existing content
        this.tableBody.innerHTML = '';
        if (this.mobileContainer) {
            this.mobileContainer.innerHTML = '';
        }

        // Render desktop view
        data.forEach(item => {
            const row = this.createTableRow(item);
            this.tableBody.appendChild(row);

            // Render mobile card if enabled
            if (this.mobileContainer && this.options.mobileCardFormatter) {
                const card = this.createMobileCard(item);
                this.mobileContainer.appendChild(card);
            }
        });
    }

    // Create a table row
    createTableRow(item) {
        const row = document.createElement('tr');
        
        // Add category data attribute if enabled
        if (this.options.categoryEnabled && item.category) {
            row.setAttribute('data-category', item.category);
        }
        
        // Add custom class if specified
        if (this.options.rowClass) {
            row.className = this.options.rowClass;
        }

        // Use custom formatter if provided, otherwise use default
        if (this.options.rowFormatter) {
            row.innerHTML = this.options.rowFormatter(item);
        } else {
            row.innerHTML = this.defaultRowFormatter(item);
        }

        return row;
    }

    // Create a mobile card
    createMobileCard(item) {
        const card = document.createElement('div');
        card.className = 'card mb-3';
        
        // Add category data attribute if enabled
        if (this.options.categoryEnabled && item.category) {
            card.setAttribute('data-category', item.category);
        }

        card.innerHTML = this.options.mobileCardFormatter(item);
        return card;
    }

    // Default row formatter
    defaultRowFormatter(item) {
        return Object.values(item).map(value => 
            `<td>${this.formatValue(value)}</td>`
        ).join('');
    }

    // Format cell values
    formatValue(value) {
        if (value === null || value === undefined) {
            return '';
        }
        if (typeof value === 'object') {
            return JSON.stringify(value);
        }
        return String(value);
    }

    // Setup event listeners
    setupEventListeners() {
        if (this.options.onAction) {
            this.tableBody.addEventListener('click', (e) => {
                const actionButton = e.target.closest('[data-action]');
                if (actionButton) {
                    const action = actionButton.getAttribute('data-action');
                    const rowData = this.getRowData(actionButton.closest('tr'));
                    this.options.onAction(action, rowData);
                }
            });

            if (this.mobileContainer) {
                this.mobileContainer.addEventListener('click', (e) => {
                    const actionButton = e.target.closest('[data-action]');
                    if (actionButton) {
                        const action = actionButton.getAttribute('data-action');
                        const cardData = this.getCardData(actionButton.closest('.card'));
                        this.options.onAction(action, cardData);
                    }
                });
            }
        }
    }

    // Get data from a table row
    getRowData(row) {
        if (!row) return null;
        const cells = Array.from(row.cells);
        const data = {};
        cells.forEach((cell, index) => {
            data[`col${index}`] = cell.textContent.trim();
        });
        return data;
    }

    // Get data from a mobile card
    getCardData(card) {
        if (!card) return null;
        // Implementation depends on card structure
        return {
            // Extract relevant data from card
        };
    }

    // Update specific row
    updateRow(identifier, newData) {
        // Implementation for updating specific rows
    }

    // Filter table rows
    filter(filterFn) {
        const rows = Array.from(this.tableBody.querySelectorAll('tr'));
        rows.forEach(row => {
            const shouldShow = filterFn(this.getRowData(row));
            row.style.display = shouldShow ? '' : 'none';
        });

        if (this.mobileContainer) {
            const cards = Array.from(this.mobileContainer.querySelectorAll('.card'));
            cards.forEach(card => {
                const shouldShow = filterFn(this.getCardData(card));
                card.style.display = shouldShow ? '' : 'none';
            });
        }
    }
}