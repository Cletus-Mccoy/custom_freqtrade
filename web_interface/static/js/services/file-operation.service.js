/**
 * Service for handling common file operations across different tabs
 */
class FileOperationService {
    /**
     * @param {string} type - The type of file ('pairlist', 'config', 'strategy')
     */
    constructor(type) {
        this.type = type;
        this.baseUrl = `/api/${type}`;
    }

    /**
     * Download a file
     * @param {string} filename - Name of the file to download
     * @returns {Promise} Promise that resolves when the download is complete
     */
    async downloadFile(filename) {
        try {
            const response = await fetch(`${this.baseUrl}/download/${filename}`);
            if (!response.ok) throw new Error(`Failed to download ${this.type}`);
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            
            if (typeof showNotification === 'function') {
                showNotification(`${this.type} "${filename}" downloaded.`, 'success');
            } else if (typeof showAlert === 'function') {
                showAlert('success', `${this.type} "${filename}" downloaded.`);
            }
        } catch (error) {
            if (typeof showNotification === 'function') {
                showNotification(`Failed to download ${this.type}.`, 'error');
            } else if (typeof showAlert === 'function') {
                showAlert('danger', `Failed to download ${this.type}.`);
            }
            throw error;
        }
    }

    /**
     * Upload a file
     * @param {File} file - The file to upload
     * @param {string} category - The category of the file
     * @returns {Promise} Promise that resolves when the upload is complete
     */
    async uploadFile(file, category = 'custom') {
        try {
            // Validate file extension
            const validExtensions = {
                pairlist: ['.json'],
                config: ['.json', '.conf', '.yaml', '.yml'],
                strategy: ['.py']
            };

            const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
            if (!validExtensions[this.type].includes(ext)) {
                throw new Error(`Only ${validExtensions[this.type].join(', ')} files are allowed.`);
            }

            // Read file content
            const content = await file.text();

            // Validate JSON for pairlist and config
            if (['pairlist', 'config'].includes(this.type) && ext === '.json') {
                JSON.parse(content); // Will throw if invalid JSON
            }

            // Upload file
            const response = await fetch(`${this.baseUrl}/${file.name}`, {
                method: 'PUT',
                headers: { 
                    'Content-Type': this.type === 'strategy' ? 'text/plain' : 'application/json'
                },
                body: content
            });

            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || `Failed to upload ${this.type}.`);
            }

            return data;
        } catch (error) {
            if (typeof showNotification === 'function') {
                showNotification(error.message, 'error');
            } else if (typeof showAlert === 'function') {
                showAlert('danger', error.message);
            }
            throw error;
        }
    }

    /**
     * Delete a file
     * @param {string} filename - Name of the file to delete
     * @returns {Promise} Promise that resolves when the delete is complete
     */
    async deleteFile(filename) {
        try {
            if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
                return false;
            }

            const response = await fetch(`${this.baseUrl}/${filename}`, {
                method: 'DELETE'
            });

            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || `Failed to delete ${this.type}.`);
            }

            if (typeof showNotification === 'function') {
                showNotification(`${this.type} "${filename}" deleted successfully!`, 'success');
            } else if (typeof showAlert === 'function') {
                showAlert('success', `${this.type} "${filename}" deleted successfully!`);
            }

            return true;
        } catch (error) {
            if (typeof showNotification === 'function') {
                showNotification(error.message, 'error');
            } else if (typeof showAlert === 'function') {
                showAlert('danger', error.message);
            }
            throw error;
        }
    }

    /**
     * Edit a file
     * @param {string} filename - Name of the file to edit
     * @param {string} content - New content for the file
     * @returns {Promise} Promise that resolves when the edit is complete
     */
    async editFile(filename, content) {
        try {
            // For config and pairlist, validate JSON
            if (['config', 'pairlist'].includes(this.type)) {
                try {
                    JSON.parse(content);
                } catch (e) {
                    throw new Error('Invalid JSON format.');
                }
            }

            const response = await fetch(`${this.baseUrl}/${filename}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': this.type === 'strategy' ? 'text/plain' : 'application/json'
                },
                body: content
            });

            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || `Failed to save ${this.type}.`);
            }

            if (typeof showNotification === 'function') {
                showNotification(`${this.type} "${filename}" saved successfully.`, 'success');
            } else if (typeof showAlert === 'function') {
                showAlert('success', `${this.type} "${filename}" saved successfully.`);
            }

            return data;
        } catch (error) {
            if (typeof showNotification === 'function') {
                showNotification(error.message, 'error');
            } else if (typeof showAlert === 'function') {
                showAlert('danger', error.message);
            }
            throw error;
        }
    }

    /**
     * Clone a file
     * @param {string} sourceFilename - Name of the file to clone
     * @param {string} newFilename - Name for the new file
     * @returns {Promise} Promise that resolves when the clone is complete
     */
    async cloneFile(sourceFilename, newFilename) {
        try {
            const response = await fetch(`${this.baseUrl}/${sourceFilename}`);
            if (!response.ok) {
                throw new Error(`Failed to load ${this.type} for cloning.`);
            }

            const content = await (this.type === 'strategy' ? response.text() : response.json());
            
            // Create new file with the content
            const saveResponse = await fetch(`${this.baseUrl}/${newFilename}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': this.type === 'strategy' ? 'text/plain' : 'application/json'
                },
                body: this.type === 'strategy' ? content : JSON.stringify(content)
            });

            const data = await saveResponse.json();
            if (!data.success) {
                throw new Error(data.error || `Failed to clone ${this.type}.`);
            }

            if (typeof showNotification === 'function') {
                showNotification(`${this.type} cloned successfully.`, 'success');
            } else if (typeof showAlert === 'function') {
                showAlert('success', `${this.type} cloned successfully.`);
            }

            return data;
        } catch (error) {
            if (typeof showNotification === 'function') {
                showNotification(error.message, 'error');
            } else if (typeof showAlert === 'function') {
                showAlert('danger', error.message);
            }
            throw error;
        }
    }
}

// Export the service
export default FileOperationService;