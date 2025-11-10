import FileOperationService from './file-operation.service.js';

/**
 * Service for handling strategy file operations
 */
export class StrategyService {
    constructor() {
        this.fileOperations = new FileOperationService('strategy');
    }

    /**
     * Get all strategies
     * @returns {Promise<Array>} Array of strategy objects
     */
    async getStrategies() {
        try {
            const response = await fetch('/api/strategies');
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Failed to fetch strategies');
            }
            return data.strategies;
        } catch (error) {
            throw new Error(`Failed to fetch strategies: ${error.message}`);
        }
    }

    /**
     * Get a specific strategy
     * @param {string} filename Name of the strategy to fetch
     */
    async getStrategy(filename) {
        try {
            const response = await fetch(`/api/strategy/${filename}`);
            const data = await response.text();
            if (!data) {
                throw new Error('Invalid strategy data');
            }
            return data;
        } catch (error) {
            throw new Error(`Failed to fetch strategy: ${error.message}`);
        }
    }

    /**
     * Create a new strategy
     * @param {string} filename Name of the strategy to create
     * @param {string} code Python code for the strategy
     * @param {string} category Category of the strategy
     */
    async createStrategy(filename, code, category = 'custom') {
        return this.fileOperations.editFile(filename, code);
    }

    /**
     * Update an existing strategy
     * @param {string} filename Name of the strategy to update
     * @param {string} code Python code for the strategy
     * @param {string} category Category of the strategy
     */
    async updateStrategy(filename, code, category = 'custom') {
        return this.fileOperations.editFile(filename, code);
    }

    /**
     * Delete a strategy
     * @param {string} filename Name of the strategy to delete
     */
    async deleteStrategy(filename) {
        return this.fileOperations.deleteFile(filename);
    }

    /**
     * Download a strategy
     * @param {string} filename Name of the strategy to download
     */
    async downloadStrategy(filename) {
        return this.fileOperations.downloadFile(filename);
    }

    /**
     * Upload a strategy file
     * @param {File} file The file to upload
     * @param {string} category The category for the strategy
     */
    async uploadStrategy(file, category = 'custom') {
        return this.fileOperations.uploadFile(file, category);
    }

    /**
     * Clone a strategy
     * @param {string} sourceFilename Name of the strategy to clone
     * @param {string} newFilename Name for the new strategy
     */
    async cloneStrategy(sourceFilename, newFilename) {
        return this.fileOperations.cloneFile(sourceFilename, newFilename);
    }

    /**
     * Test a strategy with optional backtesting
     * @param {string} filename Name of the strategy to test
     * @param {object} options Test options (timeframe, stake amount, etc)
     */
    async testStrategy(filename, options = {}) {
        try {
            const response = await fetch(`/api/strategy/${filename}/test`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(options)
            });
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Failed to test strategy');
            }
            return data.results;
        } catch (error) {
            throw new Error(`Failed to test strategy: ${error.message}`);
        }
    }
}