"""
File Resource Provider Base Classes.

Provides unified abstraction for file-based resource management (pairlists, strategies, configs).
Reduces code duplication by extracting common patterns into base classes.
"""

import json
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..category_manager import category_manager
from ..logger import logger


class FileResourceProvider(ABC):
    """
    Abstract base class for file-based resource providers.

    Provides common functionality for listing, reading, writing, and managing
    file-based resources (pairlists, strategies, configs) with unified category handling.

    Subclasses must implement:
    - _get_resource_path(): Return the directory path for this resource type
    - _extract_metadata(file_path, data): Extract resource-specific metadata
    - _create_file_data(data): Create file content from input data
    - _get_file_extension(): Return file extension (e.g., '.json', '.py')
    - _get_resource_type(): Return resource type string for CategoryManager
    """

    def __init__(self):
        """Initialize provider with resource-specific paths."""
        self.resource_path = self._get_resource_path()
        self.resource_type = self._get_resource_type()

    @abstractmethod
    def _get_resource_path(self) -> Path:
        """Return the directory path where resource files are stored."""
        pass

    @abstractmethod
    def _get_resource_type(self) -> str:
        """Return the resource type string for CategoryManager (e.g., 'pairlist', 'strategy', 'config')."""
        pass

    @abstractmethod
    def _get_file_extension(self) -> str:
        """Return the file extension for this resource type (e.g., '.json', '.py')."""
        pass

    @abstractmethod
    def _extract_metadata(self, file_path: Path, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract resource-specific metadata from file data.

        Args:
            file_path: Path to the file
            data: Parsed file content

        Returns:
            Dictionary with resource-specific metadata fields
        """
        pass

    @abstractmethod
    def _create_file_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create file content structure from input data.

        Args:
            data: Input data from frontend/API

        Returns:
            Dictionary ready to be written to file
        """
        pass

    def list_files(self) -> List[Dict[str, Any]]:
        """
        List all available resource files with metadata and category information.

        Returns:
            List of dictionaries containing file information:
            - name: Display name
            - filename: Actual filename
            - path: Full file path
            - category: Category name from CategoryManager
            - color: Category color from CategoryManager
            - Plus resource-specific metadata from _extract_metadata()
        """
        # Get categories from CategoryManager for color lookup
        categories = {cat['name']: cat.get('color', '#6c757d')
                     for cat in category_manager.get_categories(self.resource_type)}

        resources = []
        if self.resource_path.exists():
            for file_path in self.resource_path.glob(f"*{self._get_file_extension()}"):
                try:
                    # Skip system files (like __init__.py for strategies)
                    if file_path.name.startswith('__'):
                        continue

                    # Read and parse file content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        if self._get_file_extension() == '.py':
                            # For Python files, we don't parse them as JSON
                            data = {}
                        else:
                            data = json.load(f)

                    # Get category from CategoryManager
                    category = category_manager.get_file_category(self.resource_type, file_path.name)
                    color = categories.get(category, '#6c757d')

                    # Build resource entry
                    resource = {
                        'name': file_path.stem,
                        'filename': file_path.name,
                        'path': str(file_path),
                        'category': category,
                        'color': color
                    }

                    # Add resource-specific metadata
                    resource.update(self._extract_metadata(file_path, data))

                    resources.append(resource)

                except Exception as e:
                    logger.error(f"Error reading {self.resource_type} {file_path}: {e}")

        return sorted(resources, key=lambda x: x['name'])

    def get_file(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Get the content of a specific resource file.

        Args:
            filename: Name of the file to read

        Returns:
            File content as dictionary, or None if file not found/error
        """
        try:
            file_path = self.resource_path / filename
            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                if self._get_file_extension() == '.py':
                    # Return raw content for Python files
                    return {'content': f.read()}
                else:
                    return json.load(f)

        except Exception as e:
            logger.error(f"Error getting {self.resource_type} content {filename}: {e}")
            return None

    def save_file(self, filename: str, data: Dict[str, Any]) -> bool:
        """
        Create or update a resource file.

        Args:
            filename: Name of the file to save
            data: Data to write to the file

        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self.resource_path / filename

            # Create directory if it doesn't exist
            self.resource_path.mkdir(parents=True, exist_ok=True)

            # Create file content structure
            file_data = self._create_file_data(data)

            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                if self._get_file_extension() == '.py':
                    # Write raw content for Python files
                    f.write(file_data.get('content', ''))
                else:
                    json.dump(file_data, f, indent=4)

            # Update category in CategoryManager if provided
            if 'category' in data:
                category_manager.set_file_category(self.resource_type, filename, data['category'])

            return True

        except Exception as e:
            logger.error(f"Error saving {self.resource_type} file {filename}: {e}")
            return False

    def delete_file(self, filename: str) -> bool:
        """
        Delete a resource file.

        Args:
            filename: Name of the file to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self.resource_path / filename
            if file_path.exists():
                file_path.unlink()
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting {self.resource_type} file {filename}: {e}")
            return False

    def clone_file(self, source_filename: str, target_filename: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Clone a resource file with optional modifications.

        Args:
            source_filename: Name of the source file
            target_filename: Name of the target file
            data: Optional data to modify in the cloned file

        Returns:
            True if successful, False otherwise
        """
        try:
            source_path = self.resource_path / source_filename
            target_path = self.resource_path / target_filename

            if not source_path.exists():
                return False

            # Create directory if it doesn't exist
            self.resource_path.mkdir(parents=True, exist_ok=True)

            if self._get_file_extension() == '.py':
                # For Python files, copy directly
                shutil.copy2(source_path, target_path)
                if data and 'content' in data:
                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write(data['content'])
            else:
                # For JSON files, load, modify, and save
                with open(source_path, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)

                # Apply modifications if provided
                if data:
                    file_data.update(data)

                with open(target_path, 'w', encoding='utf-8') as f:
                    json.dump(file_data, f, indent=4)

            # Set category for cloned file if provided
            if data and 'category' in data:
                category_manager.set_file_category(self.resource_type, target_filename, data['category'])

            return True

        except Exception as e:
            logger.error(f"Error cloning {self.resource_type} file {source_filename} to {target_filename}: {e}")
            return False