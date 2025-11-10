import FileOperationService from './file-operation.service.js';

/**
 * Service for handling configuration file operations
 */
export class ConfigService {
    constructor() {
        this.fileOperations = new FileOperationService('config');
    }

    /**
     * Get all configurations
     * @returns {Promise<Array>} Array of config objects
     */
    async getConfigs() {
        try {
            const response = await fetch('/api/configs');
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Failed to fetch configs');
            }
            return data.configs;
        } catch (error) {
            throw new Error(`Failed to fetch configs: ${error.message}`);
        }
    }

    /**
     * Get a specific config
     * @param {string} filename Name of the config to fetch
     */
    async getConfig(filename) {
        try {
            const response = await fetch(`/api/config/${filename}`);
            const data = await response.json();
            if (!data) {
                throw new Error('Invalid config data');
            }
            return data;
        } catch (error) {
            throw new Error(`Failed to fetch config: ${error.message}`);
        }
    }

    /**
     * Create a new config
     * @param {string} filename Name of the config to create
     * @param {object} config Configuration object
     * @param {string} category Category of the config
     */
    async createConfig(filename, config, category = 'custom') {
        if (typeof config === 'string') {
            config = JSON.parse(config);
        }
        config.category = category;
        return this.fileOperations.editFile(filename, JSON.stringify(config, null, 2));
    }

    /**
     * Update an existing config
     * @param {string} filename Name of the config to update
     * @param {object} config Configuration object
     * @param {string} category Category of the config
     */
    async updateConfig(filename, config, category = 'custom') {
        return this.createConfig(filename, config, category);
    }

    /**
     * Delete a config
     * @param {string} filename Name of the config to delete
     */
    async deleteConfig(filename) {
        return this.fileOperations.deleteFile(filename);
    }

    /**
     * Download a config
     * @param {string} filename Name of the config to download
     */
    async downloadConfig(filename) {
        return this.fileOperations.downloadFile(filename);
    }

    /**
     * Upload a config file
     * @param {File} file The file to upload
     * @param {string} category The category for the config
     */
    async uploadConfig(file, category = 'custom') {
        return this.fileOperations.uploadFile(file, category);
    }

    /**
     * Clone a config
     * @param {string} sourceFilename Name of the config to clone
     * @param {string} newFilename Name for the new config
     */
    async cloneConfig(sourceFilename, newFilename) {
        return this.fileOperations.cloneFile(sourceFilename, newFilename);
    }
}