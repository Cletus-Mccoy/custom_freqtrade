"""
Config Resource Provider.

Concrete implementation of FileResourceProvider for managing configuration JSON files.
"""

import datetime
from pathlib import Path
from typing import Dict, Any, List

from .base import FileResourceProvider


class ConfigProvider(FileResourceProvider):
    """
    Provider for config file management.
    
    Configs are JSON files containing FreqTrade bot configuration.
    Stored in: user_data/config*.json and user_data/configs/config*.json
    
    Note: This provider searches multiple directories to maintain backward compatibility.
    """

    def __init__(self, base_path: Path, category_manager=None):
        """
        Initialize config provider.
        
        Args:
            base_path: Root path of the application (contains user_data/)
            category_manager: Optional CategoryManager instance
        """
        self.base_path = base_path
        self.user_data_path = base_path / "user_data"
        self.configs_path = self.user_data_path / "configs"
        super().__init__(category_manager)

    def _get_resource_path(self) -> Path:
        """
        Return the primary configs directory path.
        
        Note: list_files() is overridden to search both locations.
        """
        return self.configs_path

    def _get_resource_type(self) -> str:
        """Return the resource type for CategoryManager."""
        return "config"

    def _get_file_extension(self) -> str:
        """Return the file extension for configs."""
        return ".json"

    def _extract_metadata(self, file_path: Path, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract config-specific metadata.
        
        Args:
            file_path: Path to the config file
            data: Parsed JSON content
            
        Returns:
            Dictionary with config metadata:
            - strategy: Strategy name
            - trading_mode: Trading mode (spot, futures, etc.)
            - timeframe: Trading timeframe
            - dry_run: Whether running in dry-run mode
            - freqai_enabled: Whether FreqAI is enabled
            - modified: Last modification timestamp
            - location: Which directory the file is in
        """
        stat = file_path.stat()
        modified_time = datetime.datetime.fromtimestamp(stat.st_mtime)
        
        # Determine location (configs/ or user_data/)
        if self.configs_path in file_path.parents:
            location = 'configs'
        else:
            location = 'user_data'
        
        return {
            'strategy': data.get('strategy', 'Unknown'),
            'trading_mode': data.get('trading_mode', 'spot'),
            'timeframe': data.get('timeframe', '5m'),
            'dry_run': data.get('dry_run', True),
            'freqai_enabled': data.get('freqai', {}).get('enabled', False),
            'modified': modified_time.strftime('%Y-%m-%d %H:%M'),
            'location': location
        }

    def _create_file_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create config file structure from input data.
        
        Args:
            data: Input data containing config fields
            
        Returns:
            Dictionary ready to be written as JSON config file
        """
        # Return data as-is for configs (they contain full FreqTrade config structure)
        # Remove internal fields that shouldn't be in the file
        file_data = {k: v for k, v in data.items() 
                    if k not in ['category', 'location']}
        return file_data

    def list_files(self) -> List[Dict[str, Any]]:
        """
        Override to search both configs/ and user_data/ directories.
        
        Returns:
            List of config files from both locations, de-duplicated by filename
        """
        from ..logger import get_logger
        logger = get_logger(__name__)
        
        # Get categories for color lookup
        categories = {cat['name']: cat.get('color', '#6c757d')
                     for cat in self.category_manager.get_categories(self.resource_type)}
        
        configs = []
        processed_files = set()  # Track to avoid duplicates
        
        # Search both directories
        search_paths = [
            (self.configs_path, 'configs'),
            (self.user_data_path, 'user_data')
        ]
        
        for search_path, location in search_paths:
            if not search_path.exists():
                continue
                
            # Only match config*.json files
            pattern = "config*.json" if location == 'user_data' else "*.json"
            
            for file_path in search_path.glob(pattern):
                # Skip if already processed or not a file
                if file_path.name in processed_files or not file_path.is_file():
                    continue
                
                # Skip non-config files in configs directory
                if location == 'configs' and not file_path.name.startswith('config'):
                    continue
                
                # Skip system files
                if file_path.name.startswith('__'):
                    continue
                
                processed_files.add(file_path.name)
                
                try:
                    # Read and parse file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = self._parse_json(f)
                    
                    # Get category and color
                    category = self.category_manager.get_file_category(self.resource_type, file_path.name)
                    color = categories.get(category, '#6c757d')
                    
                    # Build config entry
                    config = {
                        'name': file_path.name,
                        'filename': file_path.name,
                        'path': str(file_path),
                        'category': category,
                        'color': color
                    }
                    
                    # Add metadata
                    config.update(self._extract_metadata(file_path, data))
                    
                    configs.append(config)
                    
                except Exception as e:
                    logger.error(f"Error reading {self.resource_type} {file_path}: {e}")
        
        return sorted(configs, key=lambda x: x['name'])
    
    def _parse_json(self, file_handle):
        """Helper to parse JSON with error handling."""
        import json
        return json.load(file_handle)
