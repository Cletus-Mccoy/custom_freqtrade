"""
Strategy Resource Provider.

Concrete implementation of FileResourceProvider for managing strategy Python files.
"""

import datetime
from pathlib import Path
from typing import Dict, Any

from .base import FileResourceProvider


class StrategyProvider(FileResourceProvider):
    """
    Provider for strategy file management.
    
    Strategies are Python files containing trading strategy classes.
    Stored in: user_data/strategies/*.py
    """

    def __init__(self, base_path: Path, category_manager=None):
        """
        Initialize strategy provider.
        
        Args:
            base_path: Root path of the application (contains user_data/)
            category_manager: Optional CategoryManager instance
        """
        self.base_path = base_path
        super().__init__(category_manager)

    def _get_resource_path(self) -> Path:
        """Return the strategies directory path."""
        return self.base_path / "user_data" / "strategies"

    def _get_resource_type(self) -> str:
        """Return the resource type for CategoryManager."""
        return "strategy"

    def _get_file_extension(self) -> str:
        """Return the file extension for strategies."""
        return ".py"

    def _extract_metadata(self, file_path: Path, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract strategy-specific metadata.
        
        Args:
            file_path: Path to the strategy file
            data: Empty dict (Python files not parsed as structured data)
            
        Returns:
            Dictionary with strategy metadata:
            - modified: Last modification timestamp
            - type: Category/type from CategoryManager (for backward compatibility)
        """
        stat = file_path.stat()
        modified_time = datetime.datetime.fromtimestamp(stat.st_mtime)
        
        return {
            'modified': modified_time.strftime('%Y-%m-%d %H:%M'),
            'type': self.resource_type  # Alias for category (backward compatibility)
        }

    def _create_file_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create strategy file structure from input data.
        
        Args:
            data: Input data with 'content' field containing Python code
            
        Returns:
            Dictionary with 'content' field ready to be written to file
        """
        return {
            'content': data.get('content', '')
        }
