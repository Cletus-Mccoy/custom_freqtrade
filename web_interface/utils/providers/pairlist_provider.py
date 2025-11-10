"""
Pairlist Resource Provider.

Concrete implementation of FileResourceProvider for managing pairlist JSON files.
"""

import json
from pathlib import Path
from typing import Dict, Any

from .base import FileResourceProvider


class PairlistProvider(FileResourceProvider):
    """
    Provider for pairlist file management.
    
    Pairlists are JSON files containing a 'pair_whitelist' array of trading pairs.
    Stored in: user_data/pairlists/*.json
    """

    def __init__(self, base_path: Path, category_manager=None):
        """
        Initialize pairlist provider.
        
        Args:
            base_path: Root path of the application (contains user_data/)
            category_manager: Optional CategoryManager instance
        """
        self.base_path = base_path
        super().__init__(category_manager)

    def _get_resource_path(self) -> Path:
        """Return the pairlists directory path."""
        return self.base_path / "user_data" / "pairlists"

    def _get_resource_type(self) -> str:
        """Return the resource type for CategoryManager."""
        return "pairlist"

    def _get_file_extension(self) -> str:
        """Return the file extension for pairlists."""
        return ".json"

    def _extract_metadata(self, file_path: Path, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract pairlist-specific metadata.
        
        Args:
            file_path: Path to the pairlist file
            data: Parsed JSON content
            
        Returns:
            Dictionary with pairlist metadata:
            - pairs_count: Number of pairs in the whitelist
        """
        return {
            'pairs_count': len(data.get('pair_whitelist', []))
        }

    def _create_file_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create pairlist file structure from input data.
        
        Args:
            data: Input data with 'pairs' or 'pair_whitelist' field
            
        Returns:
            Dictionary ready to be written as JSON with 'pair_whitelist' field
        """
        # Accept either 'pairs' (from frontend) or 'pair_whitelist' (standard format)
        pairs = data.get('pairs', data.get('pair_whitelist', []))
        
        return {
            'pair_whitelist': pairs
        }
