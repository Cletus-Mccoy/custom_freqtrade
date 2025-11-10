// page_header.js - Header component functionality
export class PageHeader {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
    }

    // Refresh button handler
    static setupRefreshButton(buttonId, refreshCallback) {
        const button = document.getElementById(buttonId);
        if (button) {
            button.addEventListener('click', async () => {
                button.disabled = true;
                try {
                    await refreshCallback();
                } finally {
                    button.disabled = false;
                }
            });
        }
    }

    // Create button handler
    static setupCreateButton(buttonId, modalId) {
        const button = document.getElementById(buttonId);
        const modal = document.getElementById(modalId);
        if (button && modal) {
            button.addEventListener('click', () => {
                new bootstrap.Modal(modal).show();
            });
        }
    }

    // Upload button handler
    static setupUploadButton(buttonId, modalId) {
        const button = document.getElementById(buttonId);
        const modal = document.getElementById(modalId);
        if (button && modal) {
            button.addEventListener('click', () => {
                new bootstrap.Modal(modal).show();
            });
        }
    }
}