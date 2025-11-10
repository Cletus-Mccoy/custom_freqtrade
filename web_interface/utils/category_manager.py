"""
Category Manager for FreqTrade Web Interface.

Provides unified category management for file-based resources (pairlists, strategies, configs).
"""

import json
from pathlib import Path
from typing import Dict, List, Optional


class CategoryManager:
    """
    Manages resource categories for pairlists, strategies, and configs.
    
    Loads category configuration from user_config.json and provides methods
    to get/set categories for files. Falls back to heuristic categorization
    when no explicit mapping exists.
    """
    
    def __init__(self, config_path: Path):
        """
        Initialize CategoryManager with path to user_config.json.
        
        Args:
            config_path: Path to user_config.json file
        """
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """
        Load user configuration from JSON file.
        
        Creates default structure if file doesn't exist.
        
        Returns:
            Dictionary containing configuration
        """
        default_config = {
            "pairlists": {
                "categories": [
                    {"name": "custom", "color": "#198754"},
                    {"name": "freqai", "color": "#0dcaf0"},
                    {"name": "example", "color": "#ffc107"},
                    {"name": "test", "color": "#c757d3"}
                ],
                "file_categories": {}
            },
            "strategies": {
                "categories": [
                    {"name": "custom", "color": "#198754"},
                    {"name": "freqai", "color": "#0dcaf0"},
                    {"name": "example", "color": "#ffc107"},
                    {"name": "test", "color": "#c757d3"}
                ],
                "file_categories": {}
            },
            "configs": {
                "categories": [
                    {"name": "custom", "color": "#198754"},
                    {"name": "live", "color": "#dc3545"},
                    {"name": "dry-run", "color": "#0dcaf0"},
                    {"name": "backtest", "color": "#ffc107"},
                    {"name": "example", "color": "#6c757d"}
                ],
                "file_categories": {}
            },
            "global_settings": {
                "cloudflare": {}
            }
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Ensure all resource types have the required structure
                for resource_type in ['pairlists', 'strategies', 'configs']:
                    if resource_type not in config:
                        config[resource_type] = default_config[resource_type]
                    else:
                        # Ensure categories and file_categories keys exist
                        if 'categories' not in config[resource_type]:
                            config[resource_type]['categories'] = default_config[resource_type]['categories']
                        if 'file_categories' not in config[resource_type]:
                            config[resource_type]['file_categories'] = {}
                
                return config
            except Exception as e:
                print(f"Error loading config from {self.config_path}: {e}")
                return default_config
        else:
            # Create config file with defaults
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    
    def _save_config(self) -> bool:
        """
        Save current configuration to JSON file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config to {self.config_path}: {e}")
            return False
    
    def get_categories(self, resource_type: str) -> List[Dict[str, str]]:
        """
        Get category definitions for a resource type.
        
        Args:
            resource_type: Type of resource ('pairlist', 'strategy', 'config')
        
        Returns:
            List of category dicts with 'name' and 'color' keys
        """
        # Normalize resource_type (remove trailing 's' if present)
        resource_key = resource_type.rstrip('s') + 's' if not resource_type.endswith('s') else resource_type
        
        # Handle alternative naming (pairlist vs pairlists)
        if resource_key == 'pairlists':
            resource_key = 'pairlists'
        elif resource_key == 'strategys':
            resource_key = 'strategies'
        elif resource_key == 'configs':
            resource_key = 'configs'
        
        return self.config.get(resource_key, {}).get('categories', [])
    
    def get_file_category(self, resource_type: str, filename: str) -> str:
        """
        Get category for a specific file.
        
        First checks explicit file_categories mapping, then falls back to heuristics.
        
        Args:
            resource_type: Type of resource ('pairlist', 'strategy', 'config')
            filename: Name of the file
        
        Returns:
            Category name string
        """
        # Normalize resource_type
        resource_key = resource_type.rstrip('s') + 's' if not resource_type.endswith('s') else resource_type
        if resource_key == 'strategys':
            resource_key = 'strategies'
        
        # Check explicit mapping first
        file_categories = self.config.get(resource_key, {}).get('file_categories', {})
        if filename in file_categories:
            return file_categories[filename]
        
        # Fall back to heuristic
        return self._heuristic_category(resource_type, filename)
    
    def set_file_category(self, resource_type: str, filename: str, category: str) -> bool:
        """
        Assign category to a file.
        
        Args:
            resource_type: Type of resource ('pairlist', 'strategy', 'config')
            filename: Name of the file
            category: Category to assign
        
        Returns:
            True if successful, False otherwise
        """
        # Normalize resource_type
        resource_key = resource_type.rstrip('s') + 's' if not resource_type.endswith('s') else resource_type
        if resource_key == 'strategys':
            resource_key = 'strategies'
        
        # Ensure structure exists
        if resource_key not in self.config:
            self.config[resource_key] = {'categories': [], 'file_categories': {}}
        if 'file_categories' not in self.config[resource_key]:
            self.config[resource_key]['file_categories'] = {}
        
        # Set category
        self.config[resource_key]['file_categories'][filename] = category
        
        # Save config
        return self._save_config()
    
    def _heuristic_category(self, resource_type: str, filename: str) -> str:
        """
        Determine category based on filename heuristics.
        
        Args:
            resource_type: Type of resource ('pairlist', 'strategy', 'config')
            filename: Name of the file
        
        Returns:
            Category name string
        """
        filename_lower = filename.lower()
        
        # Common patterns across all resource types
        if 'test' in filename_lower:
            return 'test'
        
        # Resource-specific heuristics
        if resource_type in ['pairlist', 'pairlists']:
            if 'freqai' in filename_lower or 'freq_ai' in filename_lower:
                return 'freqai'
            elif 'example' in filename_lower or 'sample' in filename_lower:
                return 'example'
            else:
                return 'custom'
        
        elif resource_type in ['strategy', 'strategies']:
            if 'freqai' in filename_lower or 'freq_ai' in filename_lower:
                return 'freqai'
            elif 'example' in filename_lower or 'sample' in filename_lower:
                return 'example'
            else:
                return 'custom'
        
        elif resource_type in ['config', 'configs']:
            if 'live' in filename_lower or 'production' in filename_lower:
                return 'live'
            elif 'dry' in filename_lower or 'dryrun' in filename_lower or 'dry-run' in filename_lower:
                return 'dry-run'
            elif 'backtest' in filename_lower or 'back_test' in filename_lower:
                return 'backtest'
            elif 'example' in filename_lower or 'sample' in filename_lower:
                return 'example'
            else:
                return 'custom'
        
        # Default fallback
        return 'custom'
