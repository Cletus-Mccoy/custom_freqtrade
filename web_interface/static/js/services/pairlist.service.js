import FileOperationService from './file-operation.service.js';

/**
 * Service for handling pairlist-related operations
 */
export class PairlistService {
    constructor() {
        this.fileOperations = new FileOperationService('pairlist');
    }

    /**
     * Get all pairlists
     * @returns {Promise<Array>} Array of pairlist objects
     */
    async getPairlists() {
        try {
            const response = await fetch('/api/pairlists');
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Failed to fetch pairlists');
            }
            return data.pairlists;
        } catch (error) {
            throw new Error(`Failed to fetch pairlists: ${error.message}`);
        }
    }

    /**
     * Get a specific pairlist
     * @param {string} filename Name of the pairlist to fetch
     */
    async getPairlist(filename) {
        try {
            const response = await fetch(`/api/pairlist/${filename}`);
            const data = await response.json();
            if (!data) {
                throw new Error('Invalid pairlist data');
            }
            return data;
        } catch (error) {
            throw new Error(`Failed to fetch pairlist: ${error.message}`);
        }
    }

    /**
     * Create a new pairlist
     * @param {string} filename Name of the pairlist to create
     * @param {Array} pairs Array of pairs to include
     * @param {string} category Category of the pairlist
     */
    async createPairlist(filename, pairs, category = 'custom') {
        return this.fileOperations.editFile(filename, JSON.stringify({ 
            pair_whitelist: pairs, 
            category 
        }, null, 2));
    }

    /**
     * Update an existing pairlist
     * @param {string} filename Name of the pairlist to update
     * @param {Array} pairs Array of pairs to include
     * @param {string} category Category of the pairlist
     */
    async updatePairlist(filename, pairs, category = 'custom') {
        return this.createPairlist(filename, pairs, category);
    }

    /**
     * Delete a pairlist
     * @param {string} filename Name of the pairlist to delete
     */
    async deletePairlist(filename) {
        return this.fileOperations.deleteFile(filename);
    }

    /**
     * Download a pairlist
     * @param {string} filename Name of the pairlist to download
     */
    async downloadPairlist(filename) {
        return this.fileOperations.downloadFile(filename);
    }

    /**
     * Upload a pairlist file
     * @param {File} file The file to upload
     * @param {string} category The category for the pairlist
     */
    async uploadPairlist(file, category = 'custom') {
        return this.fileOperations.uploadFile(file, category);
    }

    /**
     * Clone a pairlist
     * @param {string} sourceFilename Name of the pairlist to clone
     * @param {string} newFilename Name for the new pairlist
     */
    async clonePairlist(sourceFilename, newFilename) {
        return this.fileOperations.cloneFile(sourceFilename, newFilename);
    }
}