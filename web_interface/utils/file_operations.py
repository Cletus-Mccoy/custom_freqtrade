"""
File operation utilities for FreqTrade web interface.

Provides common file handling functions to eliminate duplication across routes.
"""

from pathlib import Path
from flask import send_file, jsonify
from typing import Tuple, Union, Any


def send_file_download(
    file_path: Path,
    filename: str,
    mimetype: str = 'application/json'
) -> Union[Tuple[dict, int], Any]:
    """
    Send file as downloadable attachment with validation and error handling.
    
    Args:
        file_path: Path object pointing to the file to download
        filename: Name to use for the downloaded file
        mimetype: MIME type for the file (default: 'application/json')
        
    Returns:
        Flask send_file response on success, or (error_dict, status_code) tuple on failure
        
    Examples:
        >>> send_file_download(Path('/data/config.json'), 'config.json')
        >>> send_file_download(Path('/data/strategy.py'), 'strategy.py', 'text/x-python')
    """
    try:
        # Validate file exists
        if not file_path.exists():
            resource_type = _infer_resource_type(filename)
            return jsonify({'error': f'{resource_type} not found'}), 404
        
        # Validate it's a file (not a directory)
        if not file_path.is_file():
            return jsonify({'error': 'Path is not a file'}), 400
            
        # Send file with proper headers
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype
        )
        
    except PermissionError as e:
        return jsonify({'error': f'Permission denied: {str(e)}'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _infer_resource_type(filename: str) -> str:
    """
    Infer resource type from filename for better error messages.
    
    Args:
        filename: Name of the file
        
    Returns:
        Human-readable resource type string
    """
    if filename.endswith('.py'):
        return 'Strategy'
    elif filename.startswith('config'):
        return 'Config'
    elif filename.endswith('.json'):
        return 'Pairlist'
    else:
        return 'File'
