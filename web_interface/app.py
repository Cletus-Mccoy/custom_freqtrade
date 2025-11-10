# --- Imports ---
import threading
import os
import subprocess
import datetime
import yaml
import warnings
import shutil
import traceback
import subprocess
import shutil
import tempfile
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
import docker
from utils.category_manager import CategoryManager
from utils.file_operations import send_file_download
from utils.logger import get_logger
from werkzeug.utils import secure_filename
from flask import abort

# Suppress cryptography deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="cryptography")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="paramiko")

# --- Configuration ---
BASE_PATH = Path(__file__).parent.parent
USER_DATA_PATH = BASE_PATH / "user_data"
PAIRLISTS_PATH = USER_DATA_PATH / "pairlists"
STRATEGIES_PATH = USER_DATA_PATH / "strategies"
CONFIGS_PATH = USER_DATA_PATH
SETTINGS_PATH = USER_DATA_PATH / "settings.json"

# --- Category Manager ---
category_manager = CategoryManager(BASE_PATH / "web_interface" / "config" / "user_config.json")

# --- Feature Flags ---
USE_PROVIDER_ABSTRACTION = os.getenv('USE_PROVIDER_ABSTRACTION', 'false').lower() == 'true'

# --- Resource Providers (New Abstraction Layer) ---
if USE_PROVIDER_ABSTRACTION:
    from utils.providers import PairlistProvider, StrategyProvider, ConfigProvider
    
    pairlist_provider = PairlistProvider(BASE_PATH, category_manager)
    strategy_provider = StrategyProvider(BASE_PATH, category_manager)
    config_provider = ConfigProvider(BASE_PATH, category_manager)
    
    logger = get_logger(__name__)
    logger.info("✓ Provider abstraction enabled - using new provider layer")
else:
    logger = get_logger(__name__)
    logger.info("○ Provider abstraction disabled - using legacy code paths")

# --- Flask App Initialization ---
app = Flask(__name__)
app.secret_key = 'freqtrade_web_interface_2025'

# --- Logger Setup ---
logger = get_logger(__name__)

# Register custom Jinja2 filters
def merge_filter(dict1, dict2):
    """Merge two dictionaries in Jinja2 templates"""
    result = dict1.copy()
    result.update(dict2)
    return result

app.jinja_env.filters['merge'] = merge_filter



import json
import os
FTA_APIKEYS_PATH = BASE_PATH / "user_data" / "ftapikeys"
FTA_APIKEYS_PATH.mkdir(parents=True, exist_ok=True)

def get_apikey_dir(key_name):
    safe_name = secure_filename(key_name)
    return FTA_APIKEYS_PATH / safe_name

def get_apikey_file(key_name):
    return get_apikey_dir(key_name) / "exchange_secrets.json"

@app.route('/api/ftapikeys', methods=['GET'])
def list_ft_apikeys():
    keys = []
    for d in FTA_APIKEYS_PATH.iterdir():
        if d.is_dir():
            f = d / "exchange_secrets.json"
            if f.exists():
                try:
                    with open(f, 'r') as fh:
                        data = json.load(fh)
                        keys.append({
                            "key_name": d.name,
                            "exchange": data.get("exchange", {}).get("name", "")
                        })
                except Exception:
                    continue
    return jsonify({"success": True, "keys": keys})

@app.route('/api/ftapikeys', methods=['POST'])
def save_ft_apikey():
    data = request.get_json(force=True)
    key_name = data.get("key_name", "").strip()
    exchange = data.get("exchange", "").strip()
    api_key = data.get("api_key", "").strip()
    api_secret = data.get("api_secret", "").strip()
    if not key_name or not exchange or not api_key or not api_secret:
        return jsonify({"success": False, "error": "All fields required."}), 400
    apikey_dir = get_apikey_dir(key_name)
    apikey_dir.mkdir(parents=True, exist_ok=True)
    apikey_file = apikey_dir / "exchange_secrets.json"
    # Freqtrade expects keys under 'exchange' section
    content = {
        "exchange": {
            "name": exchange,
            "key": api_key,
            "secret": api_secret
        }
    }
    try:
        with open(apikey_file, 'w') as f:
            json.dump(content, f, indent=2)
        os.chmod(apikey_file, 0o600)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": True})

@app.route('/api/ftapikeys/<key_name>', methods=['DELETE'])
def delete_ft_apikey(key_name):
    apikey_dir = get_apikey_dir(key_name)
    apikey_file = apikey_dir / "exchange_secrets.json"
    try:
        if apikey_file.exists():
            apikey_file.unlink()
        # Optionally remove the directory if empty
        if apikey_dir.exists() and not any(apikey_dir.iterdir()):
            apikey_dir.rmdir()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": True})

# --- Settings Management ---

# Unified settings loader: always use user_config.json with nested structure
def load_settings():
    config_path = BASE_PATH / 'web_interface' / 'config' / 'user_config.json'
    default_settings = {
        'global_settings': {}
    }
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        if 'global_settings' in config.get('global_settings', {}):
            del config['global_settings']
        
        # Ensure global_settings exists
        if 'global_settings' not in config:
            config['global_settings'] = {}
        
        return config
    
    return default_settings


def save_settings(settings):
    config_path = BASE_PATH / 'web_interface' / 'config' / 'user_config.json'
    with open(config_path, 'w') as f:
        json.dump(settings, f, indent=2)

# --- Global Options Menu ---
@app.route('/options', methods=['GET', 'POST'])
def options():
    """Global Options Menu"""
    config_path = BASE_PATH / 'web_interface' / 'config' / 'user_config.json'
    
    if request.method == 'POST':
        data = request.get_json(force=True, silent=True) or {}
        # Remove cloudflare section if present
        if 'global_settings' in data and 'cloudflare' in data.get('global_settings', {}):
            del data['global_settings']['cloudflare']
        
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
        return jsonify({"success": True, "settings": data})
    
    # GET: return current settings without cloudflare
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
        # Remove cloudflare section if it exists
        if 'global_settings' in config and 'cloudflare' in config.get('global_settings', {}):
            del config['global_settings']['cloudflare']
        return jsonify(config)
    
    return jsonify({"global_settings": {}})

# Log startup information
logger.info("="*50)
logger.info("FreqTrade Web Interface Starting")
logger.info("="*50)
with app.app_context():
    logger.info("Registered routes:")
    for rule in app.url_map.iter_rules():
        logger.debug(f"  {rule}")


# Docker client initialization
docker_client = None

def init_docker_client():
    """Initialize Docker client with improved Windows Docker Desktop support"""
    global docker_client
    
    connection_methods = [
        # Method 1: Default environment (best for most cases)
        {
            'name': 'Default Environment',
            'method': lambda: docker.from_env()
        },
        
        # Method 2: Windows Docker Desktop named pipe (primary Windows method)
        {
            'name': 'Windows Named Pipe (Primary)',
            'method': lambda: docker.DockerClient(base_url='npipe:////./pipe/docker_engine')
        },
        
        # Method 3: TCP connection
        {
            'name': 'TCP Connection',
            'method': lambda: docker.DockerClient(base_url='tcp://localhost:2375')
        },
        
        # Method 3: Windows Docker Desktop named pipe (primary Windows method)
        {
            'name': 'Windows Named Pipe (Primary)',
            'method': lambda: docker.DockerClient(base_url='npipe:////./pipe/docker_engine')
        },
        
        # Method 4: Windows Docker Desktop named pipe (engine)
        {
            'name': 'Windows Named Pipe (Engine)', 
            'method': lambda: docker.DockerClient(base_url='npipe:////./pipe/docker_engine')
        },
        
        # Method 5: Windows Docker Desktop named pipe (alternative format)
        {
            'name': 'Windows Named Pipe (Alternative)', 
            'method': lambda: docker.DockerClient(base_url='npipe://./pipe/docker_engine')
        },
        
        # Method 6: Unix socket (for WSL/Linux)
        {
            'name': 'Unix Socket',
            'method': lambda: docker.DockerClient(base_url='unix://var/run/docker.sock')
        }
    ]
    
    for i, conn_config in enumerate(connection_methods, 1):
        try:
            logger.info(f"Attempting Docker connection method {i}: {conn_config['name']}")
            client = conn_config['method']()
            
            # Test the connection with timeout
            client.ping()
            
            # Additional test - try to get Docker info
            info = client.info()
            
            docker_client = client
            logger.info(f"Docker client connected successfully using {conn_config['name']}")
            logger.info(f"Docker version: {info.get('ServerVersion', 'Unknown')}")
            logger.info("All Docker features are available")
            return True
            
        except Exception as e:
            logger.warning(f"{conn_config['name']} failed: {str(e)}")
            continue
    
    logger.error("All Docker connection methods failed")
    logger.error("Please ensure Docker Desktop is running and accessible")
    logger.warning("You can still use the web interface for configuration management")
    logger.info("To fix Docker connection:")
    logger.info("  1. Start Docker Desktop")
    logger.info("  2. Ensure Docker is running (check system tray)")
    logger.info("  3. Restart this application")
    return False


# Try to initialize Docker client
docker_connected = init_docker_client()

def check_docker_status():
    """Check if Docker is available and return status info"""
    global docker_client
    try:
        if docker_client is None:
            return {
                'connected': False,
                'error': 'Docker client not initialized',
                'suggestions': [
                    'Start Docker Desktop',
                    'Ensure Docker is running',
                    'Restart this application'
                ]
            }
        
        # Test connection
        docker_client.ping()
        info = docker_client.info()
        
        return {
            'connected': True,
            'version': info.get('ServerVersion', 'Unknown'),
            'containers_running': info.get('ContainersRunning', 0),
            'containers_total': info.get('Containers', 0),
            'images_count': info.get('Images', 0)
        }
    except Exception as e:
        return {
            'connected': False,
            'error': str(e),
            'suggestions': [
                'Check if Docker Desktop is running',
                'Restart Docker Desktop',
                'Check Docker Desktop settings'
            ]
        }

def reconnect_docker():
    """Attempt to reconnect to Docker"""
    return init_docker_client()

class FreqTradeManager:
    def save_docker_compose(self, compose_data):
        """Save the docker-compose.yml file with the given data."""
        try:
            with open(self.docker_compose_path, 'w') as f:
                yaml.dump(compose_data, f, default_flow_style=False, sort_keys=False)
            return True
        except Exception as e:
            logger.error(f"Error saving docker-compose.yml: {e}")
            return False

    def add_general_docker_service(self, service_name, service_config):
        """Add a service with a given config to docker-compose.yml."""
        try:
            compose_data = self.load_docker_compose()
            if not compose_data:
                compose_data = {
                    'version': '3.8',
                    'services': {},
                    'networks': {}
                }
            if 'services' not in compose_data:
                compose_data['services'] = {}
            if service_name in compose_data['services']:
                logger.info(f"Service {service_name} already exists")
                return False
            compose_data['services'][service_name] = service_config
            # Ensure network exists
            if 'networks' not in compose_data:
                compose_data['networks'] = {}
            if 'freqtrade_network' not in compose_data['networks']:
                compose_data['networks']['freqtrade_network'] = {'driver': 'bridge'}
            return self.save_docker_compose(compose_data)
        except Exception as e:
            logger.error(f"Error adding general docker service: {e}")
            return False
    def __init__(self):
        self.base_path = BASE_PATH
        self.user_data_path = USER_DATA_PATH
        self.pairlists_path = PAIRLISTS_PATH
        self.strategies_path = STRATEGIES_PATH
        self.configs_path = CONFIGS_PATH
        self.docker_compose_path = BASE_PATH / "docker-compose.yml"
        
    def get_available_pairlists(self):
        """Get all available pairlist files, using CategoryManager for unified category handling"""
        # Get categories from CategoryManager
        categories = {cat['name']: cat.get('color', '#6c757d') 
                     for cat in category_manager.get_categories('pairlist')}
        
        pairlists = []
        if self.pairlists_path.exists():
            for file in self.pairlists_path.glob("*.json"):
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                    # Get category from CategoryManager
                    category = category_manager.get_file_category('pairlist', file.name)
                    color = categories.get(category, '#6c757d')
                    pairlists.append({
                        'name': file.name,
                        'filename': file.name,
                        'path': str(file),
                        'pairs_count': len(data.get('pair_whitelist', [])),
                        'category': category,
                        'color': color
                    })
                except Exception as e:
                    logger.error(f"Error reading pairlist {file}: {e}")
        return sorted(pairlists, key=lambda x: x['name'])
    
    def get_pairlist_content(self, filename):
        """Get the content of a specific pairlist file"""
        try:
            pairlist_path = self.pairlists_path / filename
            if not pairlist_path.exists():
                return None
                
            with open(pairlist_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error getting pairlist content {filename}: {e}")
            return None

    def update_pairlist_file(self, filename, data):
        """Update or create a pairlist file"""
        try:
            pairlist_path = self.pairlists_path / filename
            pairlist_data = {
                'pair_whitelist': data.get('pairs', [])
            }
            
            # Create pairlists directory if it doesn't exist
            self.pairlists_path.mkdir(parents=True, exist_ok=True)
            
            with open(pairlist_path, 'w') as f:
                json.dump(pairlist_data, f, indent=4)
                
            # Update category in user_config.json if provided
            if 'category' in data:
                self._update_pairlist_category(filename, data['category'])
            
            return True
        except Exception as e:
            logger.error(f"Error updating pairlist file {filename}: {e}")
            return False

    def delete_pairlist_file(self, filename):
        """Delete a pairlist file"""
        try:
            pairlist_path = self.pairlists_path / filename
            if not pairlist_path.exists():
                return False
                
            pairlist_path.unlink()
            
            # Remove from user_config.json categories if present
            self._update_pairlist_category(filename, None)
            
            return True
        except Exception as e:
            logger.error(f"Error deleting pairlist file {filename}: {e}")
            return False

    def clone_pairlist_file(self, filename, new_name):
        """Clone a pairlist file"""
        try:
            source_path = self.pairlists_path / filename
            if not source_path.exists():
                return False

            # Read source file
            with open(source_path, 'r') as f:
                pairlist_data = json.load(f)
            
            # Create new file
            target_path = self.pairlists_path / new_name
            with open(target_path, 'w') as f:
                json.dump(pairlist_data, f, indent=4)
            
            # Copy category if exists
            config_path = BASE_PATH / 'web_interface' / 'config' / 'user_config.json'
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                pairlists_section = config.get('pairlists', {})
                file_categories = pairlists_section.get('file_categories', {})
                if filename in file_categories:
                    self._update_pairlist_category(new_name, file_categories[filename])
            
            return True
        except Exception as e:
            logger.error(f"Error cloning pairlist file {filename}: {e}")
            return False

    def _update_pairlist_category(self, filename, category):
        """Update or remove pairlist category in user_config.json"""
        try:
            config_path = BASE_PATH / 'web_interface' / 'config' / 'user_config.json'
            config = {}
            
            # Load existing config
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # Ensure pairlists section exists
            if 'pairlists' not in config:
                config['pairlists'] = {}
            if 'file_categories' not in config['pairlists']:
                config['pairlists']['file_categories'] = {}
            
            if category is None:
                # Remove category
                config['pairlists']['file_categories'].pop(filename, None)
            else:
                # Update category
                config['pairlists']['file_categories'][filename] = category
            
            # Save config
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            
            return True
        except Exception as e:
            logger.error(f"Error updating pairlist category: {e}")
            return False
    
    def get_available_strategies(self):
        """Get all available strategy files, using CategoryManager for unified category handling"""
        strategies = []
        if self.strategies_path.exists():
            for file in self.strategies_path.glob("*.py"):
                if not file.name.startswith('__'):
                    strategies.append({
                        'name': file.stem,
                        'filename': file.name,
                        'path': str(file),
                        'modified': datetime.datetime.fromtimestamp(file.stat().st_mtime).strftime('%Y-%m-%d %H:%M'),
                        'type': category_manager.get_file_category('strategy', file.name)
                    })
        return sorted(strategies, key=lambda x: x['name'])
    
    def get_available_configs(self):
        """Get all available config files from both configs and user_data directories"""
        configs = []
        processed_files = set()  # Track processed files to avoid duplicates
        
        # Check configs directory first
        for file in self.configs_path.glob("*.json"):
            if file.is_file() and file.name.startswith('config') and file.name not in processed_files:
                processed_files.add(file.name)
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                    configs.append({
                        'name': file.name,
                        'filename': file.name,
                        'path': str(file),
                        'strategy': data.get('strategy', 'Unknown'),
                        'trading_mode': data.get('trading_mode', 'spot'),
                        'timeframe': data.get('timeframe', '5m'),
                        'dry_run': data.get('dry_run', True),
                        'freqai_enabled': data.get('freqai', {}).get('enabled', False),
                        'modified': datetime.datetime.fromtimestamp(file.stat().st_mtime).strftime('%Y-%m-%d %H:%M'),
                        'location': 'configs',
                        'category': category_manager.get_file_category('config', file.name)
                    })
                except Exception as e:
                    logger.error(f"Error reading config {file}: {e}")
        
        # Check user_data directory for additional config files
        for file in self.user_data_path.glob("config*.json"):
            if file.is_file() and file.name not in processed_files:
                processed_files.add(file.name)
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                    configs.append({
                        'name': file.name,
                        'filename': file.name,
                        'path': str(file),
                        'strategy': data.get('strategy', 'Unknown'),
                        'trading_mode': data.get('trading_mode', 'spot'),
                        'timeframe': data.get('timeframe', '5m'),
                        'dry_run': data.get('dry_run', True),
                        'freqai_enabled': data.get('freqai', {}).get('enabled', False),
                        'modified': datetime.datetime.fromtimestamp(file.stat().st_mtime).strftime('%Y-%m-%d %H:%M'),
                        'location': 'user_data',
                        'category': category_manager.get_file_category('config', file.name)
                    })
                except Exception as e:
                    logger.error(f"Error reading config {file}: {e}")
        
        return sorted(configs, key=lambda x: x['name'])
    
    def get_docker_containers(self):
        """Get FreqTrade Docker containers"""
        containers = []
        if docker_client:
            try:
                all_containers = docker_client.containers.list(all=True)
                for container in all_containers:
                    name_lower = container.name.lower()
                    if 'freqtrade' in name_lower:
                        containers.append({
                            'name': container.name,
                            'id': container.short_id,
                            'status': container.status,
                            'image': container.image.tags[0] if container.image.tags else 'unknown',
                            'created': container.attrs['Created'],
                            'ports': container.ports
                        })
            except Exception as e:
                logger.error(f"Error getting containers: {e}")
        return containers
    
    def find_config_file(self, filename):
        """Find a config file in either configs or user_data directory"""
        # First check configs directory
        config_file = self.configs_path / filename
        if config_file.exists():
            return config_file
            
        # Then check user_data directory
        user_data_file = self.user_data_path / filename
        if user_data_file.exists():
            return user_data_file
            
        return None

    def resolve_docker_path_to_local(self, docker_path, service_config):
        """Resolve Docker container path to local filesystem path using volume mappings"""
        try:
            logger.debug(f"resolve_docker_path_to_local: docker_path={docker_path}")
            logger.debug(f"resolve_docker_path_to_local: service_config has volumes: {'volumes' in service_config}")
            
            if not docker_path or 'volumes' not in service_config:
                logger.debug(f"resolve_docker_path_to_local: Early return - docker_path={bool(docker_path)}, has_volumes={'volumes' in service_config}")
                return None
            
            volumes = service_config['volumes']
            logger.debug(f"resolve_docker_path_to_local: volumes={volumes}")
            if not isinstance(volumes, list):
                return None
            
            for volume in volumes:
                logger.debug(f"resolve_docker_path_to_local: checking volume={volume}")
                if isinstance(volume, str) and ':' in volume:
                    # Handle volume format: "local_path:container_path" or "local_path:container_path:options"
                    parts = volume.split(':')
                    logger.debug(f"resolve_docker_path_to_local: volume parts={parts}")
                    if len(parts) >= 2:
                        local_path = parts[0]
                        container_path = parts[1]
                        logger.debug(f"resolve_docker_path_to_local: local_path={local_path}, container_path={container_path}")
                        
                        # Check if docker_path starts with the container path
                        if docker_path.startswith(container_path):
                            logger.debug(f"resolve_docker_path_to_local: MATCH found for {docker_path} with {container_path}")
                            # Replace container path with local path
                            relative_path = docker_path[len(container_path):].lstrip('/')
                            logger.debug(f"resolve_docker_path_to_local: relative_path={relative_path}")
                            
                            # Convert to absolute local path
                            if local_path.startswith('./'):
                                # Relative to base path
                                local_base = self.base_path / local_path[2:]
                            elif local_path.startswith('/'):
                                # Absolute path
                                local_base = Path(local_path)
                            else:
                                # Relative to base path
                                local_base = self.base_path / local_path
                            
                            logger.debug(f"resolve_docker_path_to_local: local_base={local_base}")
                            
                            if relative_path:
                                resolved_path = local_base / relative_path
                            else:
                                resolved_path = local_base
                            
                            logger.debug(f"resolve_docker_path_to_local: resolved_path={resolved_path}, exists={resolved_path.exists()}")
                            return resolved_path
            
            return None
            
        except Exception as e:
            logger.error(f"Error resolving Docker path {docker_path}: {e}")
            return None

    def find_config_file_in_service(self, config_file, service_config):
        """Find config file using Docker volume mappings from service configuration"""
        try:
            # First try to resolve using Docker volume mappings
            if config_file.startswith('/freqtrade/'):
                resolved_path = self.resolve_docker_path_to_local(config_file, service_config)
                if resolved_path and resolved_path.exists():
                    return resolved_path
            
            # Extract just filename if it's a full path
            if '/' in config_file:
                config_filename = config_file.split('/')[-1]
            else:
                config_filename = config_file
            
            # Fallback to original logic
            return self.find_config_file(config_filename)
            
        except Exception as e:
            logger.error(f"Error finding config file {config_file}: {e}")
            return None

    def find_strategy_file_in_service(self, strategy_name, service_config):
        """Find strategy file using Docker volume mappings from service configuration"""
        try:
            if not strategy_name or strategy_name == 'Unknown':
                return None
            
            # Try to resolve strategy path using Docker volume mappings
            strategy_docker_path = f"/freqtrade/user_data/strategies/{strategy_name}.py"
            resolved_path = self.resolve_docker_path_to_local(strategy_docker_path, service_config)
            
            if resolved_path and resolved_path.exists():
                return resolved_path
            
            # Fallback to original logic
            strategy_file = f"{strategy_name}.py"
            strategy_path = self.strategies_path / strategy_file
            
            if strategy_path.exists():
                return strategy_path
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding strategy file {strategy_name}: {e}")
            return None

    def create_config_from_template(self, template_config, strategy, pairlist, container_name):
        """Create a new config file from template"""
        try:
            logger.info(f"Creating config from template: {template_config}")
            
            # Validate inputs
            if not all([template_config, strategy, pairlist, container_name]):
                raise ValueError("All parameters are required")
            
            # Find template config file using helper method
            template_path = self.find_config_file(template_config)
            if not template_path:
                raise FileNotFoundError(f"Template config file '{template_config}' not found in configs or user_data directories")
            
            logger.info(f"Found template at: {template_path}")
            
            # Load template
            with open(template_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Validate pairlist file
            pairlist_path = self.pairlists_path / pairlist
            if not pairlist_path.exists():
                raise FileNotFoundError(f"Pairlist file '{pairlist}' not found")
            
            # Load pairlist
            with open(pairlist_path, 'r', encoding='utf-8') as f:
                pairlist_data = json.load(f)
            
            if 'pair_whitelist' not in pairlist_data:
                raise ValueError(f"Pairlist file '{pairlist}' missing pair_whitelist")
            
            logger.info(f"Loaded pairlist with {len(pairlist_data['pair_whitelist'])} pairs")
            
            # Update config
            config_data['strategy'] = strategy
            
            # Ensure exchange section exists
            if 'exchange' not in config_data:
                config_data['exchange'] = {}
            
            config_data['exchange']['pair_whitelist'] = pairlist_data['pair_whitelist']
            if 'pair_blacklist' in pairlist_data:
                config_data['exchange']['pair_blacklist'] = pairlist_data['pair_blacklist']
            
            # Update FreqAI correlation pairs if FreqAI is enabled
            if config_data.get('freqai', {}).get('enabled'):
                if 'feature_parameters' not in config_data['freqai']:
                    config_data['freqai']['feature_parameters'] = {}
                config_data['freqai']['feature_parameters']['include_corr_pairlist'] = pairlist_data['pair_whitelist']
                logger.info("Updated FreqAI correlation pairs")
            
            # Update bot name
            config_data['bot_name'] = container_name
            
            # Ensure API configuration exists for container management
            if 'api_server' not in config_data:
                config_data['api_server'] = {}
            
            config_data['api_server']['enabled'] = True
            config_data['api_server']['listen_ip_address'] = '0.0.0.0'
            config_data['api_server']['listen_port'] = 8080
            config_data['api_server']['verbosity'] = 'error'
            config_data['api_server']['enable_openapi'] = True
            config_data['api_server']['jwt_secret_key'] = f"jwt-secret-{container_name}"
            config_data['api_server']['ws_token'] = f"ws-token-{container_name}"
            config_data['api_server']['CORS_origins'] = ['*']
            
            # Save new config
            new_config_path = self.configs_path / f"config_{container_name}.json"
            logger.info(f"Saving config to: {new_config_path}")
            
            with open(new_config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            
            logger.info(f"Config created successfully: {new_config_path}")
            return str(new_config_path)
            
        except Exception as e:
            logger.error(f"Error creating config from template: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Error creating config: {e}")

    def create_custom_config(self, custom_config, strategy, pairlist, container_name):
        """Create a new config file from custom settings"""
        try:
            logger.info(f"Creating custom config for container: {container_name}")
            
            # Validate inputs
            if not all([custom_config, strategy, pairlist, container_name]):
                raise ValueError("All parameters are required")
            
            # Validate pairlist file
            pairlist_path = self.pairlists_path / pairlist
            if not pairlist_path.exists():
                raise FileNotFoundError(f"Pairlist file '{pairlist}' not found")
            
            # Load pairlist
            with open(pairlist_path, 'r', encoding='utf-8') as f:
                pairlist_data = json.load(f)
            
            if 'pair_whitelist' not in pairlist_data:
                raise ValueError(f"Pairlist file '{pairlist}' missing pair_whitelist")
            
            logger.info(f"Loaded pairlist with {len(pairlist_data['pair_whitelist'])} pairs")
            
            # Build config structure with validation
            config_data = {
                "$schema": "https://schema.freqtrade.io/schema.json",
                "trading_mode": custom_config.get('trading_mode', 'spot'),
                "max_open_trades": int(custom_config.get('max_open_trades', 5)),
                "stake_currency": custom_config.get('stake_currency', 'USDT'),
                "stake_amount": float(custom_config.get('stake_amount', 200)),
                "tradable_balance_ratio": 0.99,
                "fiat_display_currency": "USD",
                "dry_run": bool(custom_config.get('dry_run', True)),
                "timeframe": custom_config.get('timeframe', '5m'),
                "dry_run_wallet": 1000,
                "cancel_open_orders_on_exit": True,
                "bot_name": container_name,
                "unfilledtimeout": {
                    "entry": int(custom_config.get('entry_timeout', 10)),
                    "exit": int(custom_config.get('exit_timeout', 30))
                },
                "exchange": {
                    "name": custom_config.get('exchange', 'binance'),
                    "key": "",
                    "secret": "",
                    "ccxt_config": {},
                    "ccxt_async_config": {},
                    "pair_whitelist": pairlist_data['pair_whitelist'],
                    "pair_blacklist": pairlist_data.get('pair_blacklist', [])
                },
                "entry_pricing": {
                    "price_side": "same",
                    "use_order_book": True,
                    "order_book_top": 1,
                    "price_last_balance": 0.0,
                    "check_depth_of_market": {
                        "enabled": False,
                        "bids_to_ask_delta": 1
                    }
                },
                "exit_pricing": {
                    "price_side": "same",
                    "use_order_book": True,
                    "order_book_top": 1
                },
                "pairlists": [
                    {
                        "method": "StaticPairList"
                    }
                ],
                "protections": [
                    {
                        "method": "CooldownPeriod",
                        "stop_duration_candles": 5
                    },
                    {
                        "method": "MaxDrawdown",
                        "lookback_period_candles": 24,
                        "trade_limit": 20,
                        "stop_duration_candles": 4,
                        "max_allowed_drawdown": 0.2
                    },
                    {
                        "method": "StoplossGuard",
                        "lookback_period_candles": 24,
                        "trade_limit": 4,
                        "stop_duration_candles": 2,
                        "only_per_pair": False
                    },
                    {
                        "method": "LowProfitPairs",
                        "lookback_period_candles": 6,
                        "trade_limit": 2,
                        "stop_duration_candles": 60,
                        "required_profit": 0.02
                    }
                ],
                "api_server": {
                    "enabled": True,
                    "listen_ip_address": "0.0.0.0",
                    "listen_port": 8080,
                    "verbosity": "error",
                    "enable_openapi": True,
                    "jwt_secret_key": f"jwt-secret-{container_name}",
                    "ws_token": f"ws-token-{container_name}",
                    "CORS_origins": ["*"]
                },
                "strategy": strategy,
                "strategy_path": "user_data/strategies/",
                "db_url": f"sqlite:///tradesv3_{container_name}.sqlite",
                "initial_state": "running",
                "force_entry_enable": False,
                "internals": {
                    "process_throttle_secs": 5
                }
            }
            
            # Add margin mode for futures
            if custom_config.get('trading_mode') == 'futures':
                config_data['margin_mode'] = 'isolated'
            
            # Add stoploss if provided
            if 'stoploss' in custom_config:
                config_data['stoploss'] = float(custom_config['stoploss']) / 100
            
            # Add minimal ROI if provided
            if 'minimal_roi' in custom_config:
                config_data['minimal_roi'] = {
                    "0": float(custom_config['minimal_roi']) / 100
                }
            
            # Add FreqAI settings if enabled
            if custom_config.get('freqai_enabled'):
                freqai_settings = custom_config.get('freqai_settings', {})
                config_data['freqai'] = {
                    "enabled": True,
                    "purge_old_models": 2,
                    "train_period_days": freqai_settings.get('train_period_days', 30),
                    "backtest_period_days": freqai_settings.get('backtest_period_days', 7),
                    "live_retrain_hours": freqai_settings.get('live_retrain_hours', 24),
                    "expiration_hours": 1,
                    "identifier": f"freqai_{container_name}",
                    "feature_parameters": {
                        "include_timeframes": ["5m", "15m", "4h"],
                        "include_corr_pairlist": pairlist_data['pair_whitelist'][:10],  # Limit correlation pairs
                        "label_period_candles": 24,
                        "include_shifted_candles": 2,
                        "DI_threshold": 0.9,
                        "weight_factor": 0.9,
                        "principal_component_analysis": False,
                        "use_SVM_to_remove_outliers": True,
                        "svm_params": {
                            "shuffle": True,
                            "nu": 0.1
                        },
                        "use_DBSCAN_to_remove_outliers": False,
                        "indicator_max_period_candles": 20,
                        "indicator_periods_candles": [10, 20]
                    },
                    "data_split_parameters": {
                        "test_size": 0.33,
                        "shuffle": False
                    },
                    "model_training_parameters": {
                        "n_estimators": 800,
                        "learning_rate": 0.02,
                        "task_type": "CPU"
                    }
                }
                
                # Set model type
                model_type = freqai_settings.get('model_type', 'LightGBM')
                if model_type == 'CatBoost':
                    config_data['freqai']['model_training_parameters']['task_type'] = 'CPU'
                    config_data['freqai']['model_training_parameters']['thread_count'] = -1
                
                logger.info(f"Added FreqAI configuration with model: {model_type}")
            
            # Save new config
            new_config_path = self.configs_path / f"config_{container_name}.json"
            logger.info(f"Saving custom config to: {new_config_path}")
            
            with open(new_config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            
            logger.info(f"Custom config created successfully: {new_config_path}")
            return str(new_config_path)
            
        except Exception as e:
            logger.error(f"Error creating custom config: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Error creating custom config: {e}")

    def load_docker_compose(self):
        """Load docker-compose.yml file"""
        try:
            if self.docker_compose_path.exists():
                with open(self.docker_compose_path, 'r') as f:
                    return yaml.safe_load(f)
            return None
        except Exception as e:
            logger.error(f"Error loading docker-compose.yml: {e}")
            return None
    
    
    def get_docker_services(self):
        """Get all services from docker-compose.yml"""
        compose_data = self.load_docker_compose()
        if compose_data and 'services' in compose_data:
            return list(compose_data['services'].keys())
        return []
    
    def get_docker_services_detailed(self):
        """Get detailed information about all services from docker-compose.yml"""
        compose_data = self.load_docker_compose()
        services_dict = {}
        
        if compose_data and 'services' in compose_data:
            for service_name, service_config in compose_data['services'].items():
                # Extract service information
                service_info = {
                    'name': service_name,
                    'image': service_config.get('image', 'Unknown'),
                    'container_name': service_config.get('container_name', service_name),
                    'restart': service_config.get('restart', 'no'),
                    'ports': service_config.get('ports', []),
                    'environment': service_config.get('environment', []),
                    'volumes': service_config.get('volumes', []),
                    'command': service_config.get('command', []),
                    'networks': service_config.get('networks', []),
                    'status': self.get_service_status(service_name)
                }
                
                # Extract strategy and config from environment or command
                strategy = 'Unknown'
                config_file = 'Unknown'
                
                # Check environment variables
                for env in service_info['environment']:
                    if isinstance(env, str):
                        if env.startswith('FREQTRADE_STRATEGY='):
                            strategy = env.split('=', 1)[1]
                        elif env.startswith('FREQTRADE_CONFIG_FILE='):
                            config_file = env.split('=', 1)[1]
                
                # Check command arguments
                if isinstance(service_info['command'], list):
                    for i, arg in enumerate(service_info['command']):
                        if arg == '--strategy' and i + 1 < len(service_info['command']):
                            strategy = service_info['command'][i + 1]
                        elif arg == '--config' and i + 1 < len(service_info['command']):
                            config_file = service_info['command'][i + 1]
                elif isinstance(service_info['command'], str):
                    command_str = service_info['command']
                    # Handle shell commands that contain freqtrade
                    if 'freqtrade' in command_str:
                        # Extract strategy from --strategy parameter
                        if '--strategy ' in command_str:
                            parts = command_str.split('--strategy ')
                            if len(parts) > 1:
                                strategy_part = parts[1].split()[0]  # Get first word after --strategy
                                strategy = strategy_part
                        
                        # Extract config from --config parameter
                        if '--config ' in command_str:
                            parts = command_str.split('--config ')
                            if len(parts) > 1:
                                config_part = parts[1].split()[0]  # Get first word after --config
                                config_file = config_part  # Keep full Docker path for consistency
                
                service_info['strategy'] = strategy
                service_info['config_file'] = config_file
                
                # Add comprehensive validation checks
                service_info['port_consistency'] = self.validate_port_consistency(service_name, service_config, config_file)
                service_info['strategy_validation'] = self.validate_strategy_availability(service_name, service_config, strategy)
                service_info['config_validation'] = self.validate_config_file(service_name, service_config, config_file)
                
                services_dict[service_name] = service_info
        
        return services_dict
    
    def validate_port_consistency(self, service_name, service_config, config_file):
        """Validate that container ports match API server ports in config and check for port conflicts"""
        try:
            # Extract container port from service config
            container_port = 8080  # Default FreqTrade API port
            host_port = None
            
            if 'ports' in service_config and service_config['ports']:
                ports = service_config['ports']
                
                if isinstance(ports, list) and len(ports) > 0:
                    port_mapping = ports[0] # Take first port mapping
                    
                    if ':' in str(port_mapping):
                        parts = str(port_mapping).split(':')
                        
                        # Handle different port mapping formats:
                        # Format 1: "8080:8080" (2 parts)
                        # Format 2: "0.0.0.0:8080:8080" (3 parts)
                        # Format 3: "127.0.0.1:8080:8080" (3 parts)
                        if len(parts) == 2:
                            try:
                                host_port = int(parts[0])
                                container_port = int(parts[1])
                            except ValueError:
                                container_port = 8080
                        elif len(parts) == 3:
                            # Format: "IP:HOST_PORT:CONTAINER_PORT"
                            try:
                                host_port = int(parts[1])  # Middle part is the host port
                                container_port = int(parts[2])  # Last part is the container port
                            except ValueError:
                                host_port = None
                                container_port = 8080
                        else:
                            container_port = 8080
            
            # Check for port conflicts with other services
            port_conflicts = self._check_port_conflicts(service_name, host_port)
            
            # Try to find and read the config file using Docker volume mappings
            config_api_port = 8080  # Default
            config_missing = True
            
            if config_file and config_file != 'Unknown':
                config_path = self.find_config_file_in_service(config_file, service_config)
                if config_path and config_path.exists():
                    config_missing = False
                    try:
                        with open(config_path, 'r') as f:
                            config_data = json.load(f)
                        
                        # Check API server configuration
                        if 'api_server' in config_data:
                            config_api_port = config_data['api_server'].get('listen_port', 8080)
                    except Exception as e:
                        logger.error(f"Error reading config {config_file}: {e}")
            
            # Determine overall consistency
            port_match = container_port == config_api_port
            has_conflicts = len(port_conflicts) > 0
            
            # Build result message
            messages = []
            if not port_match:
                messages.append(f'Container port {container_port} != Config port {config_api_port}')
            if has_conflicts:
                conflict_services = ', '.join(port_conflicts)
                messages.append(f'Host port {host_port} conflicts with: {conflict_services}')
            if config_missing:
                messages.append('Config file not found')
            
            if not messages:
                messages.append('All checks passed')
            
            result = {
                'success': True,
                'consistent': port_match and not has_conflicts and not config_missing,
                'container_port': container_port,
                'config_port': config_api_port,
                'host_port': host_port,
                'port_conflicts': port_conflicts,
                'config_missing': config_missing,
                'message': '; '.join(messages)
            }
            
            return result
            
        except Exception as e:
            logger.error(f" Exception validating port consistency for {service_name}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'consistent': False,
                'container_port': 'unknown',
                'config_port': 'unknown',
                'host_port': 'unknown',
                'port_conflicts': [],
                'config_missing': True,
                'message': f'Validation error: {e}'
            }
    
    def _check_port_conflicts(self, current_service_name, host_port):
        """Check if the host port conflicts with other services"""
        if not host_port:
            return []
        
        conflicts = []
        try:
            compose_data = self.load_docker_compose()
            if compose_data and 'services' in compose_data:
                for service_name, service_config in compose_data['services'].items():
                    if service_name == current_service_name:
                        continue
                    
                    if 'ports' in service_config and service_config['ports']:
                        ports = service_config['ports']
                        if isinstance(ports, list):
                            for port_mapping in ports:
                                if ':' in str(port_mapping):
                                    parts = str(port_mapping).split(':')
                                    try:
                                        other_host_port = None
                                        if len(parts) == 2:
                                            # Format: "host_port:container_port"
                                            other_host_port = int(parts[0])
                                        elif len(parts) == 3:
                                            # Format: "ip:host_port:container_port"
                                            other_host_port = int(parts[1])
                                        
                                        if other_host_port and other_host_port == host_port:
                                            conflicts.append(service_name)
                                    except (ValueError, IndexError):
                                        continue
        except Exception as e:
            logger.error(f"Error checking port conflicts: {e}")
        
        return conflicts
    
    def check_strategy_consistency(self, service_name, service_config):
        """Check for strategy name consistency between command and environment"""
        try:
            command_strategy = 'Unknown'
            env_strategy = 'Unknown'
            
            # Extract strategy from command
            if 'command' in service_config:
                command = service_config['command']
                if isinstance(command, list):
                    for i, arg in enumerate(command):
                        if arg == '--strategy' and i + 1 < len(command):
                            command_strategy = command[i + 1]
                            break
            
            # Extract strategy from environment
            if 'environment' in service_config:
                env_vars = service_config['environment']
                if isinstance(env_vars, list):
                    for env_var in env_vars:
                        if isinstance(env_var, str) and 'FREQTRADE_STRATEGY=' in env_var:
                            env_strategy = env_var.split('FREQTRADE_STRATEGY=')[1]
                            break
            
            # Check for mismatch
            has_mismatch = False
            mismatch_details = None
            
            if command_strategy != 'Unknown' and env_strategy != 'Unknown':
                if command_strategy != env_strategy:
                    has_mismatch = True
                    mismatch_details = {
                        'command_strategy': command_strategy,
                        'env_strategy': env_strategy,
                        'message': f'Strategy mismatch: command uses "{command_strategy}" but environment uses "{env_strategy}"'
                    }
            
            return {
                'has_mismatch': has_mismatch,
                'command_strategy': command_strategy,
                'env_strategy': env_strategy,
                'details': mismatch_details
            }
            
        except Exception as e:
            return {
                'has_mismatch': False,
                'command_strategy': 'Unknown',
                'env_strategy': 'Unknown',
                'details': {'error': str(e)}
            }
    
    def check_config_consistency(self, service_name, service_config):
        """Check for config file consistency between command and environment"""
        try:
            command_config = 'Unknown'
            env_config = 'Unknown'
            
            # Extract config from command
            if 'command' in service_config:
                command = service_config['command']
                if isinstance(command, list):
                    for i, arg in enumerate(command):
                        if arg == '--config' and i + 1 < len(command):
                            config_part = command[i + 1]
                            command_config = config_part.replace('/freqtrade/user_data/', '')
                            break
            
            # Extract config from environment
            if 'environment' in service_config:
                env_vars = service_config['environment']
                if isinstance(env_vars, list):
                    for env_var in env_vars:
                        if isinstance(env_var, str) and 'FREQTRADE_CONFIG_FILE=' in env_var:
                            config_part = env_var.split('FREQTRADE_CONFIG_FILE=')[1]
                            env_config = config_part.replace('/freqtrade/user_data/', '')
                            break
            
            # Check for mismatch
            has_mismatch = False
            mismatch_details = None
            
            if command_config != 'Unknown' and env_config != 'Unknown':
                if command_config != env_config:
                    has_mismatch = True
                    mismatch_details = {
                        'command_config': command_config,
                        'env_config': env_config,
                        'message': f'Config mismatch: command uses "{command_config}" but environment uses "{env_config}"'
                    }
            
            return {
                'has_mismatch': has_mismatch,
                'command_config': command_config,
                'env_config': env_config,
                'details': mismatch_details
            }
            
        except Exception as e:
            return {
                'has_mismatch': False,
                'command_config': 'Unknown',
                'env_config': 'Unknown',
                'details': {'error': str(e)}
            }
    
    def validate_strategy_availability(self, service_name, service_config, strategy_name):
        """Validate that the strategy file exists and is properly configured"""
        try:
            if not strategy_name or strategy_name == 'Unknown':
                return {
                    'success': True,
                    'valid': False,
                    'strategy_found': False,
                    'strategy_path': None,
                    'syntax_valid': False,
                    'class_found': False,
                    'priority': 'warning',
                    'message': 'No strategy specified'
                }
            
            # Check for strategy consistency between command and environment
            consistency_check = self.check_strategy_consistency(service_name, service_config)
            inconsistency_message = None
            
            if consistency_check['has_mismatch']:
                inconsistency_message = consistency_check['details']['message']
            
            # Find strategy file using Docker volume mappings
            strategy_path = self.find_strategy_file_in_service(strategy_name, service_config)
            
            if not strategy_path or not strategy_path.exists():
                # Check if there's a similar strategy name available
                similar_strategies = []
                if self.strategies_path.exists():
                    strategy_files = [f.stem for f in self.strategies_path.glob('*.py') if f.is_file() and not f.name.startswith('__')]
                    similar_strategies = [s for s in strategy_files if strategy_name.lower() in s.lower() or s.lower() in strategy_name.lower()]
                
                error_msg = f'Strategy file "{strategy_name}.py" not found'
                if similar_strategies:
                    error_msg += f'. Similar strategies found: {", ".join(similar_strategies)}'
                if inconsistency_message:
                    error_msg = f'{inconsistency_message}. {error_msg}'
                
                return {
                    'success': True,
                    'valid': False,
                    'strategy_found': False,
                    'strategy_path': str(strategy_path) if strategy_path else None,
                    'syntax_valid': False,
                    'class_found': False,
                    'priority': 'error',
                    'message': error_msg,
                    'similar_strategies': similar_strategies,
                    'has_mismatch': inconsistency_message is not None,
                    'consistency_check': consistency_check
                }
            
            # Check if file is readable
            try:
                with open(strategy_path, 'r', encoding='utf-8') as f:
                    strategy_content = f.read()
            except Exception as e:
                error_msg = f'Cannot read strategy file: {e}'
                if inconsistency_message:
                    error_msg = f'{inconsistency_message}. {error_msg}'
                return {
                    'success': True,
                    'valid': False,
                    'strategy_found': True,
                    'strategy_path': str(strategy_path),
                    'syntax_valid': False,
                    'class_found': False,
                    'priority': 'error',
                    'message': error_msg,
                    'has_mismatch': inconsistency_message is not None,
                    'consistency_check': consistency_check
                }
            
            # Basic syntax validation
            syntax_valid = True
            syntax_errors = []
            try:
                compile(strategy_content, strategy_path, 'exec')
            except SyntaxError as e:
                syntax_valid = False
                syntax_errors.append(f"Line {e.lineno}: {e.msg}")
            except Exception as e:
                syntax_valid = False
                syntax_errors.append(f"Compilation error: {e}")
            
            # Check for strategy class
            class_found = False
            class_errors = []
            
            if syntax_valid:
                # Look for class definition
                import re
                class_pattern = rf'class\s+{re.escape(strategy_name)}\s*\([^)]*IStrategy[^)]*\)'
                base_class_pattern = r'class\s+\w+\s*\([^)]*IStrategy[^)]*\)'
                
                if re.search(class_pattern, strategy_content):
                    class_found = True
                elif re.search(base_class_pattern, strategy_content):
                    # Found a strategy class but wrong name
                    class_errors.append(f"Strategy class name doesn't match file name '{strategy_name}'")
                else:
                    class_errors.append("No IStrategy-based class found")
                
                # Check for required methods
                if class_found:
                    required_methods = ['populate_indicators', 'populate_entry_trend', 'populate_exit_trend']
                    missing_methods = []
                    
                    for method in required_methods:
                        if f'def {method}(' not in strategy_content:
                            missing_methods.append(method)
                    
                    if missing_methods:
                        class_errors.append(f"Missing required methods: {', '.join(missing_methods)}")
            
            # Determine overall validity - include inconsistency check
            is_valid = syntax_valid and class_found and not class_errors and not inconsistency_message
            
            # Build message
            messages = []
            if inconsistency_message:
                messages.append(inconsistency_message)
            if not syntax_valid:
                messages.extend([f"Syntax error: {err}" for err in syntax_errors])
            if class_errors:
                messages.extend(class_errors)
            
            if not messages:
                messages = ['Strategy validation passed']
            
            # Determine priority - inconsistency is error level
            if inconsistency_message or not syntax_valid:
                priority = 'error'
            elif class_errors:
                priority = 'warning'
            else:
                priority = 'success'
            
            return {
                'success': True,
                'valid': is_valid,
                'strategy_found': True,
                'strategy_path': str(strategy_path),
                'syntax_valid': syntax_valid,
                'class_found': class_found,
                'priority': priority,
                'message': '; '.join(messages),
                'has_mismatch': inconsistency_message is not None,
                'consistency_check': consistency_check
            }
            
        except Exception as e:
            return {
                'success': False,
                'valid': False,
                'strategy_found': False,
                'strategy_path': None,
                'syntax_valid': False,
                'class_found': False,
                'priority': 'error',
                'message': f'Strategy validation error: {e}',
                'has_mismatch': False
            }
    
    def validate_config_file(self, service_name, service_config, config_file):
        """Validate that the config file exists and has proper structure"""
        try:
            if not config_file or config_file == 'Unknown':
                return {
                    'success': True,
                    'valid': False,
                    'config_found': False,
                    'config_path': None,
                    'json_valid': False,
                    'structure_valid': False,
                    'api_configured': False,
                    'priority': 'warning',
                    'message': 'No config file specified'
                }
            
            logger.debug(f"{service_name}: validate_config_file called with config_file: {config_file}")
            
            # Check for config consistency between command and environment
            consistency_check = self.check_config_consistency(service_name, service_config)
            inconsistency_message = None
            
            if consistency_check['has_mismatch']:
                inconsistency_message = consistency_check['details']['message']
            
            # Find config file using Docker volume mappings with full Docker path
            config_path = self.find_config_file_in_service(config_file, service_config)
            logger.debug(f"{service_name}: find_config_file_in_service returned: {config_path}")
            
            if not config_path:
                # Also try with just the filename as fallback
                if '/' in config_file:
                    config_filename = config_file.split('/')[-1]
                    config_path = self.find_config_file_in_service(config_filename, service_config)
                    logger.debug(f"{service_name}: Fallback with filename {config_filename}: {config_path}")
            
            if not config_path:
                error_msg = f'Config file "{config_file}" not found'
                if inconsistency_message:
                    error_msg = f'{inconsistency_message}. {error_msg}'
                
                return {
                    'success': True,
                    'valid': False,
                    'config_found': False,
                    'config_path': config_file,
                    'json_valid': False,
                    'structure_valid': False,
                    'api_configured': False,
                    'priority': 'error',
                    'message': error_msg,
                    'has_mismatch': inconsistency_message is not None,
                    'consistency_check': consistency_check
                }
            
            # Read and parse config
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            except json.JSONDecodeError as e:
                error_msg = f'Invalid JSON syntax: {e}'
                if inconsistency_message:
                    error_msg = f'{inconsistency_message}. {error_msg}'
                return {
                    'success': True,
                    'valid': False,
                    'config_found': True,
                    'config_path': str(config_path),
                    'json_valid': False,
                    'structure_valid': False,
                    'api_configured': False,
                    'priority': 'error',
                    'message': error_msg,
                    'has_mismatch': inconsistency_message is not None,
                    'consistency_check': consistency_check
                }
            except Exception as e:
                error_msg = f'Cannot read config file: {e}'
                if inconsistency_message:
                    error_msg = f'{inconsistency_message}. {error_msg}'
                return {
                    'success': True,
                    'valid': False,
                    'config_found': True,
                    'config_path': str(config_path),
                    'json_valid': False,
                    'structure_valid': False,
                    'api_configured': False,
                    'priority': 'error',
                    'message': error_msg,
                    'has_mismatch': inconsistency_message is not None,
                    'consistency_check': consistency_check
                }
            
            # Validate config structure
            structure_errors = []
            required_fields = ['max_open_trades', 'stake_currency', 'stake_amount', 'dry_run', 'timeframe']
            
            for field in required_fields:
                if field not in config_data:
                    structure_errors.append(f"Missing required field: {field}")
            
            # Check exchange configuration
            if 'exchange' not in config_data:
                structure_errors.append("Missing 'exchange' configuration")
            else:
                exchange_config = config_data['exchange']
                if 'name' not in exchange_config:
                    structure_errors.append("Exchange name not specified")
                if 'pair_whitelist' not in exchange_config or not exchange_config['pair_whitelist']:
                    structure_errors.append("No trading pairs specified")
            
            # Check API server configuration
            api_configured = False
            api_errors = []
            
            if 'api_server' in config_data:
                api_config = config_data['api_server']
                if api_config.get('enabled', False):
                    api_configured = True
                    if 'listen_port' not in api_config:
                        api_errors.append("API server enabled but no port specified")
                    if 'listen_ip_address' not in api_config:
                        api_errors.append("API server enabled but no IP specified")
                else:
                    api_errors.append("API server is disabled")
            else:
                api_errors.append("No API server configuration found")
            
            # Check strategy configuration
            strategy_errors = []
            if 'strategy' not in config_data:
                strategy_errors.append("No strategy specified in config")
            
            # Check for common configuration issues
            warning_messages = []
            
            if config_data.get('dry_run', True) == False:
                warning_messages.append("Live trading enabled (dry_run=false)")
            
            if config_data.get('max_open_trades', 0) > 20:
                warning_messages.append(f"High max_open_trades: {config_data['max_open_trades']}")
            
            if config_data.get('stake_amount', 0) > 1000:
                warning_messages.append(f"High stake_amount: {config_data['stake_amount']}")
            
            # Determine overall validity
            structure_valid = len(structure_errors) == 0
            has_warnings = len(api_errors) > 0 or len(strategy_errors) > 0 or len(warning_messages) > 0
            
            # Determine overall validity - include inconsistency check
            overall_valid = structure_valid and not inconsistency_message
            
            # Build message
            messages = []
            if inconsistency_message:
                messages.append(inconsistency_message)
            if structure_errors:
                messages.extend([f"Structure error: {err}" for err in structure_errors])
            if api_errors:
                messages.extend([f"API issue: {err}" for err in api_errors])
            if strategy_errors:
                messages.extend([f"Strategy issue: {err}" for err in strategy_errors])
            if warning_messages:
                messages.extend([f"Warning: {warn}" for warn in warning_messages])
            
            if not messages:
                messages = ['Config validation passed']
            
            # Determine priority - inconsistency is error level
            if inconsistency_message or structure_errors:
                priority = 'error'
            elif api_errors or strategy_errors:
                priority = 'warning'
            elif warning_messages:
                priority = 'info'
            else:
                priority = 'success'
            
            return {
                'success': True,
                'valid': overall_valid,
                'config_found': True,
                'config_path': str(config_path),
                'json_valid': True,
                'structure_valid': structure_valid,
                'api_configured': api_configured,
                'priority': priority,
                'message': '; '.join(messages),
                'has_mismatch': inconsistency_message is not None,
                'consistency_check': consistency_check
            }
            
        except Exception as e:
            return {
                'success': False,
                'valid': False,
                'config_found': False,
                'config_path': None,
                'json_valid': False,
                'structure_valid': False,
                'api_configured': False,
                'priority': 'error',
                'message': f'Config validation error: {e}',
                'has_mismatch': False
            }
    
    def get_docker_compose_content(self):
        """Get the raw docker-compose.yml content"""
        try:
            with open(self.docker_compose_path, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading docker-compose.yml: {e}")
            return "# Error reading docker-compose.yml"
    
    def add_docker_service(self, service_name, strategy, config_file, pairlist_file, external_api_port=8081):
        """Add a new service to docker-compose.yml"""
        try:
            logger.info(f"Adding Docker service: {service_name}")
            compose_data = self.load_docker_compose()
            if not compose_data:
                # Create basic structure if file doesn't exist
                compose_data = {
                    'version': '3.8',
                    'services': {},
                    'networks': {}
                }
            
            # Ensure services key exists
            if 'services' not in compose_data:
                compose_data['services'] = {}
                
            # Check if service already exists
            if service_name in compose_data['services']:
                logger.info(f"Service {service_name} already exists")
                return False
            
            # Create service configuration
            service_config = {
                'image': 'freqtradeorg/freqtrade:stable',
                'container_name': service_name,
                'restart': 'unless-stopped',
                'volumes': [
                    './user_data:/freqtrade/user_data',
                    './ichiv1/user_data:/freqtrade/ichiv1_data:ro'
                ],
                'command': [
                    'trade',
                    '--config', f'/freqtrade/user_data/{config_file}',
                    '--strategy-path', '/freqtrade/user_data/strategies',
                    '--strategy', strategy
                ],
                'environment': [
                    f'FREQTRADE_CONFIG_FILE=/freqtrade/user_data/{config_file}',
                    f'FREQTRADE_STRATEGY={strategy}',
                    f'FREQTRADE_PAIRLIST={pairlist_file}'
                ],
                'ports': [f'{external_api_port}:8080'],
                'networks': ['freqtrade_network']
            }
            
            # Add service to compose
            compose_data['services'][service_name] = service_config
            
            # Ensure network exists
            if 'networks' not in compose_data:
                compose_data['networks'] = {}
            if 'freqtrade_network' not in compose_data['networks']:
                compose_data['networks']['freqtrade_network'] = {
                    'driver': 'bridge'
                }
            
            # Save updated compose file
            success = self.save_docker_compose(compose_data)
            logger.info(f"Docker service addition result: {success}")
            return success
            
        except Exception as e:
            logger.error(f"Error adding Docker service: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    
    def start_docker_service(self, service_name):
        """Start a specific Docker service using docker compose up -d"""
        try:
            import subprocess
            import os
            
            # Change to the directory containing docker-compose.yml
            original_dir = os.getcwd()
            os.chdir(self.base_path)
            
            try:
                # Try newer docker compose syntax first (Docker Desktop v2+)
                try:
                    result = subprocess.run(
                        ['docker', 'compose', 'up', '-d', service_name],
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minutes timeout
                    )
                    
                    if result.returncode == 0:
                        logger.info(f"Successfully started service: {service_name} (using 'docker compose')")
                        return True
                    else:
                        logger.error(f"Failed with 'docker compose': {result.stderr}")
                        # Fall back to older syntax
                        raise subprocess.CalledProcessError(result.returncode, ['docker', 'compose'])
                        
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Try older docker-compose syntax as fallback
                    result = subprocess.run(
                        ['docker-compose', 'up', '-d', service_name],
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minutes timeout
                    )
                    
                    if result.returncode == 0:
                        logger.info(f"Successfully started service: {service_name} (using 'docker-compose')")
                        return True
                    else:
                        logger.error(f"Failed to start service {service_name}: {result.stderr}")
                        return False
                    
            finally:
                # Always restore original directory
                os.chdir(original_dir)
                
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout starting service: {service_name}")
            return False
        except Exception as e:
            logger.error(f"Error starting Docker service: {e}")
            return False
    
    def stop_docker_service(self, service_name):
        """Stop a specific Docker service"""
        try:
            logger.info(f"Stopping Docker service: {service_name}")
            os.chdir(self.docker_compose_path.parent)
            
            # Try modern Docker Compose syntax first
            try:
                result = subprocess.run(
                    ['docker', 'compose', 'stop', service_name],
                    capture_output=True,
                    text=True,
                    timeout=120  # 2 minutes timeout
                )
                
                if result.returncode == 0:
                    logger.info(f"Successfully stopped service: {service_name} (using 'docker compose')")
                    return True
                else:
                    logger.error(f"Failed to stop service {service_name} with 'docker compose': {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout stopping service {service_name} with 'docker compose'")
            except Exception as e:
                logger.error(f"Error with 'docker compose' stop: {e}")
            
            # Fallback to legacy syntax
            try:
                result = subprocess.run(
                    ['docker-compose', 'stop', service_name],
                    capture_output=True,
                    text=True,
                    timeout=120  # 2 minutes timeout
                )
                
                if result.returncode == 0:
                    logger.info(f"Successfully stopped service: {service_name} (using 'docker-compose')")
                    return True
                else:
                    logger.error(f"Failed to stop service {service_name} with 'docker-compose': {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout stopping service {service_name} with 'docker-compose'")
                
        except Exception as e:
            logger.error(f"Error stopping Docker service: {e}")
            return False
    
    def restart_docker_service(self, service_name):
        """Restart a specific Docker service"""
        try:
            logger.info(f"Restarting Docker service: {service_name}")
            os.chdir(self.docker_compose_path.parent)
            
            # Try modern Docker Compose syntax first
            try:
                result = subprocess.run(
                    ['docker', 'compose', 'restart', service_name],
                    capture_output=True,
                    text=True,
                    timeout=180  # 3 minutes timeout
                )
                
                if result.returncode == 0:
                    logger.info(f"Successfully restarted service: {service_name} (using 'docker compose')")
                    return True
                else:
                    logger.error(f"Failed to restart service {service_name} with 'docker compose': {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout restarting service {service_name} with 'docker compose'")
            except Exception as e:
                logger.error(f"Error with 'docker compose' restart: {e}")
            
            # Fallback to legacy syntax
            try:
                result = subprocess.run(
                    ['docker-compose', 'restart', service_name],
                    capture_output=True,
                    text=True,
                    timeout=180  # 3 minutes timeout
                )
                
                if result.returncode == 0:
                    logger.info(f"Successfully restarted service: {service_name} (using 'docker-compose')")
                    return True
                else:
                    logger.error(f"Failed to restart service {service_name} with 'docker-compose': {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout restarting service {service_name} with 'docker-compose'")
                
        except Exception as e:
            logger.error(f"Error restarting Docker service: {e}")
            return False
    
    def start_all_docker_services(self):
        """Start all Docker services"""
        try:
            logger.info("Starting all Docker services...")
            os.chdir(self.docker_compose_path.parent)
            
            # Try modern Docker Compose syntax first
            try:
                result = subprocess.run(
                    ['docker', 'compose', 'up', '-d'],
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minutes timeout
                )
                
                if result.returncode == 0:
                    logger.info("Successfully started all services (using 'docker compose')")
                    return True
                else:
                    logger.error(f"Failed to start all services with 'docker compose': {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.warning("Timeout starting all services with 'docker compose'")
            except Exception as e:
                logger.error(f"Error with 'docker compose' up: {e}")
            
            # Fallback to legacy syntax
            try:
                result = subprocess.run(
                    ['docker-compose', 'up', '-d'],
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minutes timeout
                )
                
                if result.returncode == 0:
                    logger.info("Successfully started all services (using 'docker-compose')")
                    return True
                else:
                    logger.error(f"Failed to start all services with 'docker-compose': {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.warning("Timeout starting all services with 'docker-compose'")
                
        except Exception as e:
            logger.error(f"Error starting all Docker services: {e}")
            return False
    
    def stop_all_docker_services(self):
        """Stop all Docker services"""
        try:
            logger.info("Stopping all Docker services...")
            os.chdir(self.docker_compose_path.parent)
            
            # Try modern Docker Compose syntax first
            try:
                result = subprocess.run(
                    ['docker', 'compose', 'down'],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes timeout
                )
                
                if result.returncode == 0:
                    logger.info("Successfully stopped all services (using 'docker compose')")
                    return True
                else:
                    logger.error(f"Failed to stop all services with 'docker compose': {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.warning("Timeout stopping all services with 'docker compose'")
            except Exception as e:
                logger.error(f"Error with 'docker compose' down: {e}")
            
            # Fallback to legacy syntax
            try:
                result = subprocess.run(
                    ['docker-compose', 'down'],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes timeout
                )
                
                if result.returncode == 0:
                    logger.info("Successfully stopped all services (using 'docker-compose')")
                    return True
                else:
                    logger.error(f"Failed to stop all services with 'docker-compose': {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.warning("Timeout stopping all services with 'docker-compose'")
                
        except Exception as e:
            logger.error(f"Error stopping all Docker services: {e}")
            return False
    
    def get_service_status(self, service_name):
        """Get the status of a specific Docker service"""
        try:
            os.chdir(self.docker_compose_path.parent)
            
            # Try modern Docker Compose syntax first
            try:
                result = subprocess.run(
                    ['docker', 'compose', 'ps', service_name],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    if service_name in output:
                        if "Up" in output:
                            return "running"
                        elif "Exit" in output:
                            return "stopped"
                        else:
                            return "unknown"
                    # If not found in compose, try direct container check
                    return self._check_container_directly(service_name)
            except Exception as e:
                logger.error(f"Error with 'docker compose' ps: {e}")
            
            # Fallback to legacy syntax
            try:
                result = subprocess.run(
                    ['docker-compose', 'ps', service_name],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    if service_name in output:
                        if "Up" in output:
                            return "running"
                        elif "Exit" in output:
                            return "stopped"
                        else:
                            return "unknown"
                    # If not found in compose, try direct container check
                    return self._check_container_directly(service_name)
            except Exception:
                pass
                
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            
        # Final fallback: check for container directly
        return self._check_container_directly(service_name)
    
    def _check_container_directly(self, service_name):
        """Check container status directly using docker ps, fallback for when compose fails"""
        try:
            # Get the container name from service config
            compose_data = self.load_docker_compose()
            container_name = service_name  # Default to service name
            
            if compose_data and 'services' in compose_data and service_name in compose_data['services']:
                service_config = compose_data['services'][service_name]
                container_name = service_config.get('container_name', service_name)
            
            # Check for container by name
            result = subprocess.run(
                ['docker', 'ps', '-a', '--filter', f'name={container_name}', '--format', 'table {{.Names}}\t{{.Status}}'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                lines = output.split('\n')[1:]  # Skip header
                for line in lines:
                    if line and container_name in line:
                        if 'Up' in line:
                            return "running"
                        elif 'Exited' in line:
                            return "stopped"
                        else:
                            return "unknown"
            
            # Also try checking by service name if container name didn't work
            if container_name != service_name:
                result = subprocess.run(
                    ['docker', 'ps', '-a', '--filter', f'name={service_name}', '--format', 'table {{.Names}}\t{{.Status}}'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    lines = output.split('\n')[1:]  # Skip header
                    for line in lines:
                        if line and service_name in line:
                            if 'Up' in line:
                                return "running"
                            elif 'Exited' in line:
                                return "stopped"
                            else:
                                return "unknown"
            
            return "not_found"
            
        except Exception as e:
            logger.error(f"Error checking container directly: {e}")
            return "unknown"
    
    def validate_docker_compose_yaml(self, yaml_content):
        """Validate Docker Compose YAML content"""
        try:
            yaml_data = yaml.safe_load(yaml_content)
            
            # Basic validation checks
            if not isinstance(yaml_data, dict):
                return False, "YAML content must be a dictionary"
            
            if 'services' not in yaml_data:
                return False, "Docker Compose file must contain 'services' section"
            
            if not isinstance(yaml_data['services'], dict):
                return False, "'services' section must be a dictionary"
            
            # Check each service has required fields
            for service_name, service_config in yaml_data['services'].items():
                if not isinstance(service_config, dict):
                    return False, f"Service '{service_name}' configuration must be a dictionary"
            
            return True, "Valid Docker Compose YAML"
            
        except yaml.YAMLError as e:
            return False, f"YAML syntax error: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def rationalize_docker_compose_yaml(self, yaml_content):
        """Rationalize and fix common YAML issues in Docker Compose files"""
        try:
            # Parse the YAML
            yaml_data = yaml.safe_load(yaml_content)
            issues_found = []
            issues_fixed = []
            
            if not isinstance(yaml_data, dict):
                return False, "YAML content must be a dictionary", [], []
            
            # Remove deprecated version field if present
            if 'version' in yaml_data:
                del yaml_data['version']
                issues_fixed.append("Removed deprecated 'version' field")
            
            # Ensure required sections exist
            if 'services' not in yaml_data:
                yaml_data['services'] = {}
                issues_fixed.append("Added missing 'services' section")
            
            if 'networks' not in yaml_data:
                yaml_data['networks'] = {}
                issues_fixed.append("Added missing 'networks' section")
            
            # Add default network if missing
            if 'freqtrade_network' not in yaml_data['networks']:
                yaml_data['networks']['freqtrade_network'] = {'driver': 'bridge'}
                issues_fixed.append("Added default 'freqtrade_network'")
            
            # Rationalize each service
            for service_name, service_config in yaml_data['services'].items():
                if not isinstance(service_config, dict):
                    issues_found.append(f"Service '{service_name}' has invalid configuration structure")
                    continue
                
                # Fix command formatting
                if 'command' in service_config:
                    command = service_config['command']
                    if isinstance(command, str):
                        # Convert multiline string commands to arrays
                        if '\n' in command or '\\' in command:
                            # Split on newlines and remove line continuations
                            command_parts = [line.strip().rstrip('\\') for line in command.split('\n') if line.strip()]
                            if len(command_parts) > 1:
                                service_config['command'] = [part for part in ' '.join(command_parts).split() if part]
                                issues_fixed.append(f"Service '{service_name}': Fixed multiline command formatting")
                
                # Ensure essential fields exist
                if 'image' not in service_config:
                    service_config['image'] = 'freqtradeorg/freqtrade:stable'
                    issues_fixed.append(f"Service '{service_name}': Added default image")
                
                if 'restart' not in service_config:
                    service_config['restart'] = 'unless-stopped'
                    issues_fixed.append(f"Service '{service_name}': Added default restart policy")
                
                # Fix networks formatting
                if 'networks' in service_config:
                    networks = service_config['networks']
                    if isinstance(networks, str):
                        service_config['networks'] = [networks]
                        issues_fixed.append(f"Service '{service_name}': Converted networks string to list")
                    elif not isinstance(networks, list):
                        service_config['networks'] = ['freqtrade_network']
                        issues_fixed.append(f"Service '{service_name}': Fixed networks format")
                else:
                    service_config['networks'] = ['freqtrade_network']
                    issues_fixed.append(f"Service '{service_name}': Added default network")
                
                # Fix ports formatting and validate
                if 'ports' in service_config:
                    ports = service_config['ports']
                    if isinstance(ports, str):
                        service_config['ports'] = [ports]
                        issues_fixed.append(f"Service '{service_name}': Converted ports string to list")
                    elif isinstance(ports, list):
                        # Validate port mappings
                        for i, port in enumerate(ports):
                            if isinstance(port, str):
                                # Check for valid port format
                                if ':' not in port:
                                    issues_found.append(f"Service '{service_name}': Invalid port format '{port}' (should be host:container)")
                                else:
                                    # Validate port numbers
                                    parts = port.split(':')
                                    if len(parts) == 2:
                                        try:
                                            host_port = int(parts[0]) if parts[0] != '0.0.0.0' else int(parts[1])
                                            container_port = int(parts[1])
                                            if not (1 <= host_port <= 65535) or not (1 <= container_port <= 65535):
                                                issues_found.append(f"Service '{service_name}': Port numbers out of valid range (1-65535)")
                                        except ValueError:
                                            issues_found.append(f"Service '{service_name}': Invalid port numbers in '{port}'")
                                    elif len(parts) == 3:
                                        # Format: ip:host:container
                                        try:
                                            host_port = int(parts[1])
                                            container_port = int(parts[2])
                                            if not (1 <= host_port <= 65535) or not (1 <= container_port <= 65535):
                                                issues_found.append(f"Service '{service_name}': Port numbers out of valid range (1-65535)")
                                        except ValueError:
                                            issues_found.append(f"Service '{service_name}': Invalid port numbers in '{port}'")
                
                # Fix volumes formatting
                if 'volumes' in service_config:
                    volumes = service_config['volumes']
                    if isinstance(volumes, str):
                        service_config['volumes'] = [volumes]
                        issues_fixed.append(f"Service '{service_name}': Converted volumes string to list")
                
                # Fix environment formatting
                if 'environment' in service_config:
                    environment = service_config['environment']
                    if isinstance(environment, str):
                        service_config['environment'] = [environment]
                        issues_fixed.append(f"Service '{service_name}': Converted environment string to list")
                
                # Check for container_name consistency
                if 'container_name' in service_config:
                    container_name = service_config['container_name']
                    if container_name != service_name and not container_name.startswith(service_name):
                        issues_found.append(f"Service '{service_name}': Container name '{container_name}' doesn't match service name")
            
            # Generate clean YAML output
            yaml_output = yaml.dump(yaml_data, default_flow_style=False, sort_keys=False, 
                                  allow_unicode=True, indent=2, width=120)
            
            return True, yaml_output, issues_found, issues_fixed
            
        except yaml.YAMLError as e:
            return False, f"YAML syntax error: {str(e)}", [], []
        except Exception as e:
            return False, f"Rationalization error: {str(e)}", [], []

    def fix_docker_compose_formatting(self):
        """Fix formatting issues in docker-compose.yml"""
        try:
            compose_data = self.load_docker_compose()
            if not compose_data:
                return False
            
            # Remove version as it's not supported in newer Docker Compose
            if 'version' in compose_data:
                del compose_data['version']
            
            # Ensure services section exists
            if 'services' not in compose_data:
                compose_data['services'] = {}
                
            # Ensure networks section exists
            if 'networks' not in compose_data:
                compose_data['networks'] = {}
                
            # Add default network if missing
            if 'freqtrade_network' not in compose_data['networks']:
                compose_data['networks']['freqtrade_network'] = {'driver': 'bridge'}
            
            # Fix service configurations
            for service_name, service_config in compose_data['services'].items():
                # Fix command formatting - handle multiline commands
                if 'command' in service_config:
                    command = service_config['command']
                    if isinstance(command, str):
                        # Clean up multiline command strings
                        if '\n' in command or '&&' in command:
                            # Convert to proper multiline YAML format
                            command = command.strip()
                            # Remove extra quotes and formatting artifacts
                            command = command.replace("'-c \"", "").replace("'\"", "").replace("\"'", "")
                            command = command.replace("''", "'")
                            # Split long commands into multiple lines for readability
                            if len(command) > 100:
                                # Use YAML literal block scalar for long commands
                                service_config['command'] = command
                            else:
                                service_config['command'] = command
                
                # Ensure required fields exist
                if 'image' not in service_config:
                    service_config['image'] = 'freqtradeorg/freqtrade:stable'
                
                if 'restart' not in service_config:
                    service_config['restart'] = 'unless-stopped'
                
                # Ensure networks is a list
                if 'networks' in service_config:
                    if isinstance(service_config['networks'], str):
                        service_config['networks'] = [service_config['networks']]
                    elif not isinstance(service_config['networks'], list):
                        service_config['networks'] = ['freqtrade_network']
                else:
                    service_config['networks'] = ['freqtrade_network']
                
                # Fix ports formatting
                if 'ports' in service_config and isinstance(service_config['ports'], str):
                    service_config['ports'] = [service_config['ports']]
                
                # Fix volumes formatting  
                if 'volumes' in service_config and isinstance(service_config['volumes'], str):
                    service_config['volumes'] = [service_config['volumes']]
                
                # Fix environment formatting
                if 'environment' in service_config and isinstance(service_config['environment'], str):
                    service_config['environment'] = [service_config['environment']]
            
            # Rewrite the file with proper formatting
            return self.save_docker_compose(compose_data)
            
        except Exception as e:
            logger.error(f"Error fixing Docker Compose formatting: {e}")
            return False


manager = FreqTradeManager()

@app.route('/')
def index():
    """Main dashboard"""
    containers = manager.get_docker_containers()
    settings = load_settings()
    return render_template('index.html', containers=containers, settings=settings)

# Register missing routes for navigation endpoints
@app.route('/services')
def services():
    """Docker services management page"""
    services = manager.get_docker_services_detailed()
    compose_yaml = manager.get_docker_compose_content()
    logger.debug(f"Services route called")
    logger.debug(f"services data length: {len(str(services)) if services else 0}")
    logger.debug(f"compose_yaml length: {len(compose_yaml) if compose_yaml else 0}")
    if compose_yaml:
        logger.debug(f"compose_yaml preview: {compose_yaml[:100]}...")
    settings = load_settings()
    return render_template('services.html', services=services, compose_yaml=compose_yaml, settings=settings)

@app.route('/pairlists')
def pairlists():
    """Pairlist management page"""
    try:
        pairlists = manager.get_available_pairlists()
        if not isinstance(pairlists, list):
            pairlists = []
        settings = load_settings()
        for pairlist in pairlists:
            pairlist['pairs_count'] = len(pairlist.get('pairs', [])) if isinstance(pairlist.get('pairs'), list) else 0
            if 'category' not in pairlist:
                pairlist['category'] = 'custom'
        return render_template('pairlists.html', pairlists=pairlists, settings=settings)
    except Exception as e:
        logger.error(f"Error in pairlists route: {str(e)}")
        flash('Failed to load pairlists. Please check the server logs.', 'error')
        return render_template('pairlists.html', pairlists=[], settings=load_settings())

@app.route('/strategies')
def strategies():
    """Strategy management page"""
    strategies = manager.get_available_strategies()
    settings = load_settings()
    return render_template('strategies.html', strategies=strategies, settings=settings)

@app.route('/configs')
def configs():
    """Config management page"""
    configs = manager.get_available_configs()
    settings = load_settings()
    return render_template('configs.html', configs=configs, settings=settings)

@app.route('/containers')
def containers():
    """Running containers page (different from services)"""
    containers = manager.get_docker_containers()
    settings = load_settings()
    return render_template('containers.html', containers=containers, settings=settings)

@app.route('/api/container/<action>/<container_name>', methods=['POST'])
def container_action(action, container_name):
    """Perform action on container"""
    if not docker_client:
        return jsonify({'error': 'Docker not available'}), 500
    
    try:
        container = docker_client.containers.get(container_name)
        
        if action == 'start':
            container.start()
            return jsonify({'success': True, 'message': f'Container {container_name} started'})
        elif action == 'stop':
            container.stop()
            return jsonify({'success': True, 'message': f'Container {container_name} stopped'})
        elif action == 'restart':
            container.restart()
            return jsonify({'success': True, 'message': f'Container {container_name} restarted'})
        elif action == 'remove':
            container.remove(force=True)
            return jsonify({'success': True, 'message': f'Container {container_name} removed'})
        else:
            return jsonify({'error': 'Invalid action'}), 400
            
    # except docker.errors.NotFound:
    #     return jsonify({'error': f'Container {container_name} not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/container/logs/<container_name>')
def container_logs(container_name):
    """Get container logs"""
    if not docker_client:
        return jsonify({'error': 'Docker not available'}), 500
    
    try:
        container = docker_client.containers.get(container_name)
        logs = container.logs(tail=100).decode('utf-8')
        return jsonify({'logs': logs})
    # except docker.errors.NotFound:
    #     return jsonify({'error': f'Container {container_name} not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pairlist/<filename>')
def get_pairlist(filename):
    """Get pairlist details"""
    try:
        pairlist_path = manager.pairlists_path / filename
        with open(pairlist_path, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- API: Update (PUT) and Delete (DELETE) Pairlist ---
from flask import make_response

# --- API: Get all pairlists as JSON for AJAX refresh ---
@app.route('/api/pairlists', methods=['GET'])
def api_get_pairlists():
    """Return all pairlists as JSON for AJAX refresh"""
    try:
        if USE_PROVIDER_ABSTRACTION:
            # New provider-based implementation
            pairlists = pairlist_provider.list_files()
        else:
            # Legacy implementation
            pairlists = manager.get_available_pairlists()
        return jsonify({"success": True, "pairlists": pairlists})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/pairlist/<filename>', methods=['GET'])
def get_pairlist_api(filename):
    """Get a specific pairlist file"""
    try:
        if USE_PROVIDER_ABSTRACTION:
            # New provider-based implementation
            pairlist = pairlist_provider.get_file(filename)
        else:
            # Legacy implementation
            pairlist = manager.get_pairlist_content(filename)
        
        if not pairlist:
            return jsonify({'error': 'Pairlist not found'}), 404
        return jsonify(pairlist)
    except Exception as e:
        logger.error(f"Error getting pairlist {filename}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/pairlist/<filename>', methods=['PUT'])
def update_pairlist_api(filename):
    """Create or update a pairlist file"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Get required fields
        pairs = data.get('pairs', [])
        if not isinstance(pairs, list):
            return jsonify({'error': 'Pairs must be a list'}), 400
            
        # Extract optional fields
        category = data.get('category', 'custom')
        
        # Update pairlist file
        if USE_PROVIDER_ABSTRACTION:
            # New provider-based implementation
            result = pairlist_provider.save_file(filename, {
                'pairs': pairs,
                'category': category
            })
        else:
            # Legacy implementation
            result = manager.update_pairlist_file(filename, {
                'pairs': pairs,
                'category': category
            })
        
        if result:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to update pairlist'}), 500
    except Exception as e:
        logger.error(f"Error updating pairlist {filename}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/pairlist/<filename>', methods=['DELETE'])
def delete_pairlist_api(filename):
    """Delete a pairlist file"""
    try:
        if USE_PROVIDER_ABSTRACTION:
            # New provider-based implementation
            result = pairlist_provider.delete_file(filename)
        else:
            # Legacy implementation
            result = manager.delete_pairlist_file(filename)
        
        if result:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to delete pairlist'}), 500
    except Exception as e:
        logger.error(f"Error deleting pairlist {filename}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/pairlist/<filename>/clone', methods=['POST'])
def clone_pairlist_api(filename):
    """Clone a pairlist file"""
    try:
        new_name = request.args.get('new_name')
        if not new_name:
            return jsonify({'error': 'New name not provided'}), 400
        
        if USE_PROVIDER_ABSTRACTION:
            # New provider-based implementation
            result = pairlist_provider.clone_file(filename, new_name)
        else:
            # Legacy implementation
            result = manager.clone_pairlist_file(filename, new_name)
        
        if result:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to clone pairlist'}), 500
    except Exception as e:
        logger.error(f"Error cloning pairlist {filename}: {str(e)}")
        return jsonify({'error': str(e)}), 500
        # Ensure directory exists
        pairlist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pairlist_path, 'w') as f:
            json.dump(data, f, indent=4)
        # Update user_config.json with category mapping (new nested format)
        if category:
            config_path = BASE_PATH / 'web_interface' / 'config' / 'user_config.json'
            config = {}
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as cf:
                    try:
                        config = json.load(cf)
                    except Exception:
                        config = {}
            if 'pairlists' not in config:
                config['pairlists'] = {}
            if 'file_categories' not in config['pairlists']:
                config['pairlists']['file_categories'] = {}
            config['pairlists']['file_categories'][filename] = category
            with open(config_path, 'w', encoding='utf-8') as cf:
                json.dump(config, cf, indent=2)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pairlist/<filename>', methods=['DELETE'])
def delete_pairlist(filename):
    """Delete a pairlist file"""
    try:
        pairlist_path = manager.pairlists_path / filename
        if not pairlist_path.exists():
            return jsonify({'error': 'Pairlist not found'}), 404
        os.remove(pairlist_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500





# --- Config Download Endpoint ---
@app.route('/api/config/download/<filename>')
def download_config(filename):
    """Download a config file as attachment"""
    return send_file_download(manager.configs_path / filename, filename, 'application/json')

@app.route('/api/pairlist/download/<filename>')
def download_pairlist(filename):
    """Download a pairlist file as attachment"""
    return send_file_download(PAIRLISTS_PATH / filename, filename, 'application/json')

# --- Strategy Download Endpoint ---
@app.route('/api/strategy/download/<filename>')
def download_strategy(filename):
    """Download a strategy file as attachment"""
    return send_file_download(STRATEGIES_PATH / filename, filename, 'text/x-python')

@app.route('/api/config/<filename>')
def get_config(filename):
    """Get config details"""
    try:
        config_path = manager.find_config_file(filename)
        if not config_path or not config_path.exists():
            return jsonify({'error': 'Config not found'}), 404
        with open(config_path, 'r') as f:
            data = json.load(f)
        # Remove sensitive data
        if 'exchange' in data and 'key' in data['exchange']:
            data['exchange']['key'] = '***HIDDEN***'
        if 'exchange' in data and 'secret' in data['exchange']:
            data['exchange']['secret'] = '***HIDDEN***'
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Configs API ---
@app.route('/api/configs', methods=['GET'])
def list_configs():
    """List all config files"""
    try:
        configs = manager.get_available_configs()
        return jsonify({'success': True, 'configs': configs})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/configs', methods=['POST'])
def create_config():
    """Create a new config file"""
    try:
        data = request.get_json()
        name = data.get('name') or data.get('bot_name') or data.get('filename')
        if not name:
            return jsonify({'success': False, 'error': 'Missing config name'}), 400
        if not name.endswith('.json'):
            name = f"{name}.json"
        config_path = manager.configs_path / name
        if config_path.exists():
            return jsonify({'success': False, 'error': 'Config already exists'}), 409
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return jsonify({'success': True, 'filename': name})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/<filename>', methods=['PUT'])
def update_or_create_config(filename):
    """Update an existing config file or create a new one if it does not exist"""
    try:
        config_path = manager.configs_path / filename
        data = request.get_json()
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return jsonify({'success': True, 'created': not config_path.exists()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/<filename>', methods=['DELETE'])
def delete_config(filename):
    """Delete a config file"""
    try:
        config_path = manager.configs_path / filename
        if not config_path.exists():
            return jsonify({'success': False, 'error': 'Config not found'}), 404
        os.remove(config_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config/upload', methods=['POST'])
def upload_config():
    """Upload a config file"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        file = request.files['file']
        if not file.filename or not file.filename.endswith('.json'):
            return jsonify({'success': False, 'error': 'Only .json files allowed'}), 400
        config_path = manager.configs_path / file.filename
        if config_path.exists():
            return jsonify({'success': False, 'error': 'Config already exists'}), 409
        file.save(config_path)
        return jsonify({'success': True, 'filename': file.filename})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# --- User Config Endpoints for Category Settings (grouped with config routes) ---
@app.route('/config/user_config.json', methods=['GET'])
def get_user_config():
    config_path = Path(__file__).parent / 'config' / 'user_config.json'
    if not config_path.exists():
        # Return a default config with NEW nested structure
        data = {
            "pairlists": {
                "categories": [],
                "file_categories": {}
            },
            "strategies": {
                "categories": [],
                "file_categories": {}
            },
            "configs": {
                "categories": [],
                "file_categories": {}
            },
            "global_settings": {}
        }
    else:
        with open(config_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except Exception:
                logger.error("Failed to parse user_config.json, returning default structure")
                data = {
                    "pairlists": {
                        "categories": [],
                        "file_categories": {}
                    },
                    "strategies": {
                        "categories": [],
                        "file_categories": {}
                    },
                    "configs": {
                        "categories": [],
                        "file_categories": {}
                    },
                    "global_settings": {}
                }

    # Ensure all required sections exist
    if "pairlists" not in data:
        data["pairlists"] = {"categories": [], "file_categories": {}}
    if "strategies" not in data:
        data["strategies"] = {"categories": [], "file_categories": {}}
    if "configs" not in data:
        data["configs"] = {"categories": [], "file_categories": {}}
    if "global_settings" not in data:
        data["global_settings"] = {}
    
    return jsonify(data)

@app.route('/config/user_config.json', methods=['PUT'])
def save_user_config():
    """Save user configuration with NEW nested format"""
    config_path = Path(__file__).parent / 'config' / 'user_config.json'
    try:
        data = request.get_json(force=True)
        
        # Ensure the new nested structure exists
        if 'pairlists' not in data:
            data['pairlists'] = {}
        if 'categories' not in data['pairlists']:
            data['pairlists']['categories'] = []
        if 'file_categories' not in data['pairlists']:
            data['pairlists']['file_categories'] = {}
        
        if 'strategies' not in data:
            data['strategies'] = {'categories': [], 'file_categories': {}}
        if 'configs' not in data:
            data['configs'] = {'categories': [], 'file_categories': {}}
        if 'global_settings' not in data:
            data['global_settings'] = {}
        
        # Save the full nested structure
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info("User config saved successfully")
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error saving user config: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/docker-compose/update', methods=['POST'])
def update_docker_compose():
    """Update docker-compose.yml with new service"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        service_name = data.get('service_name')
        strategy = data.get('strategy')
        config_file = data.get('config_file')
        pairlist_file = data.get('pairlist_file')
        
        # Use global manager instead of creating new instance
        
        # Check if service already exists
        existing_services = manager.get_docker_services()
        if service_name in existing_services:
            return jsonify({
                'error': f'Service {service_name} already exists in docker-compose.yml'
            }), 400
        
        # Add the service
        success = manager.add_docker_service(
            service_name, strategy, config_file, pairlist_file, 
            (data.get('external_api_port', 8081) if data else 8081)
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Successfully added {service_name} to docker-compose.yml',
                'service_name': service_name
            })
        else:
            return jsonify({
                'error': 'Failed to update docker-compose.yml'
            }), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/docker-compose/add-service', methods=['POST'])
def add_docker_service():
    """Add a service to docker-compose.yml"""
    try:
        data = request.get_json()
        service_name = data.get('service_name')
        service_config = data.get('service_config')
        
        if not service_name or not service_config:
            return jsonify({'error': 'service_name and service_config are required'}), 400
        
        # Use global manager to add the service
        success = manager.add_general_docker_service(service_name, service_config)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Successfully added {service_name} to docker-compose.yml'
            })
        else:
            return jsonify({
                'error': f'Failed to add {service_name} to docker-compose.yml'
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/docker/services', methods=['GET'])
def get_docker_services():
    """Get all Docker services from docker-compose.yml"""
    try:
        services = manager.get_docker_services_detailed()
        return jsonify({
            'success': True,
            'services': services
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/docker/containers', methods=['GET'])
def get_docker_containers():
    """Get all Docker containers"""
    try:
        containers = manager.get_docker_containers()
        return jsonify({
            'success': True,
            'containers': containers
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/docker/compose', methods=['GET'])
def get_docker_compose_content():
    """Get Docker Compose content for the editor"""
    try:
        content = manager.get_docker_compose_content()
        return jsonify({
            'success': True,
            'content': content
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/docker/validate', methods=['POST'])
def validate_docker_compose():
    """Validate Docker Compose YAML content"""
    try:
        data = request.get_json()
        content = data.get('content', '')
        
        valid, message = manager.validate_docker_compose_yaml(content)
        
        return jsonify({
            'valid': valid,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'valid': False,
            'message': str(e)
        }), 500

@app.route('/api/docker/reconnect', methods=['POST'])
def docker_reconnect():
    """Attempt to reconnect to Docker"""
    try:
        if init_docker_client():
            return jsonify({
                'success': True,
                'message': 'Docker client reconnected successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to reconnect to Docker'
            }), 503
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error reconnecting to Docker: {str(e)}'
        }), 500

@app.route('/api/docker/fix-formatting', methods=['POST'])
def fix_docker_compose_formatting():
    """Fix Docker Compose formatting issues"""
    try:
        success = manager.fix_docker_compose_formatting()
        if success:
            return jsonify({
                'success': True,
                'message': 'Docker Compose formatting fixed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to fix Docker Compose formatting'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500




@app.route('/api/docker/networks/<network_name>', methods=['GET'])
def get_network_config(network_name):
    """Get configuration for a specific network"""
    try:
        global docker_client
        if docker_client:
            try:
                network = docker_client.networks.get(network_name)
                network_config = {
                    'name': network.name,
                    'driver': network.attrs.get('Driver', 'bridge'),
                    'internal': network.attrs.get('Internal', False),
                    'attachable': network.attrs.get('Attachable', False),
                    'ipam': network.attrs.get('IPAM', {}),
                    'options': network.attrs.get('Options', {}),
                    'labels': network.attrs.get('Labels', {})
                }
                return jsonify({
                    'success': True,
                    'network': network_config
                })
            except Exception as docker_error:
                # If not found in Docker, try to get from compose file
                compose_path = os.path.join(os.getcwd(), 'docker-compose.yml')
                if os.path.exists(compose_path):
                    with open(compose_path, 'r') as f:
                        compose_data = yaml.safe_load(f)
                    
                    if 'networks' in compose_data and network_name in compose_data['networks']:
                        network_config = compose_data['networks'][network_name]
                        return jsonify({
                            'success': True,
                            'network': network_config
                        })
                
                return jsonify({
                    'success': False,
                    'error': f'Network {network_name} not found'
                }), 404
        else:
            return jsonify({
                'success': False,
                'error': 'Docker client not available'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/docker/networks/<network_name>', methods=['PUT'])
def update_network_config(network_name):
    """Update network configuration in docker-compose.yml"""
    try:
        data = request.get_json()
        compose_path = os.path.join(os.getcwd(), 'docker-compose.yml')
        
        if not os.path.exists(compose_path):
            return jsonify({
                'success': False,
                'error': 'docker-compose.yml not found'
            }), 404
        
        with open(compose_path, 'r') as f:
            compose_data = yaml.safe_load(f)
        
        if 'networks' not in compose_data:
            compose_data['networks'] = {}
        
        # Build network configuration
        network_config = {}
        
        if data.get('driver') and data['driver'] != 'bridge':
            network_config['driver'] = data['driver']
        
        if data.get('internal'):
            network_config['internal'] = True
        
        if data.get('attachable'):
            network_config['attachable'] = True
        
        # Handle IPAM configuration
        if data.get('ipam'):
            network_config['ipam'] = data['ipam']
        
        # Handle labels
        if data.get('labels'):
            network_config['labels'] = data['labels']
        
        # Handle driver options
        if data.get('options'):
            network_config['driver_opts'] = data['options']
        
        # Update or create the network in compose
        compose_data['networks'][network_name] = network_config
        
        # Write back to file
        with open(compose_path, 'w') as f:
            yaml.dump(compose_data, f, default_flow_style=False, sort_keys=False)
        
        return jsonify({
            'success': True,
            'message': f'Network {network_name} updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/docker/start/<service_name>', methods=['POST'])
def start_docker_service_api(service_name):
    """Start a specific Docker service"""
    try:
        success = manager.start_docker_service(service_name)
        if success:
            return jsonify({
                'success': True,
                'message': f'Service {service_name} started successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to start service {service_name}'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/docker/stop/<service_name>', methods=['POST'])
def stop_docker_service_api(service_name):
    """Stop a specific Docker service"""
    try:
        success = manager.stop_docker_service(service_name)
        if success:
            return jsonify({
                'success': True,
                'message': f'Service {service_name} stopped successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to stop service {service_name}'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/docker/restart/<service_name>', methods=['POST'])
def restart_docker_service_api(service_name):
    """Restart a specific Docker service"""
    try:
        success = manager.restart_docker_service(service_name)
        if success:
            return jsonify({
                'success': True,
                'message': f'Service {service_name} restarted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to restart service {service_name}'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/docker/start-all', methods=['POST'])
def start_all_docker_services_api():
    """Start all Docker services"""
    try:
        success = manager.start_all_docker_services()
        if success:
            return jsonify({
                'success': True,
                'message': 'All services started successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to start all services'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/docker/stop-all', methods=['POST'])
def stop_all_docker_services_api():
    """Stop all Docker services"""
    try:
        success = manager.stop_all_docker_services()
        if success:
            return jsonify({
                'success': True,
                'message': 'All services stopped successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to stop all services'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/docker/restart-all', methods=['POST'])
def restart_all_docker_services_api():
    """Restart all Docker services"""
    try:
        # First stop all services, then start them
        stop_success = manager.stop_all_docker_services()
        if stop_success:
            start_success = manager.start_all_docker_services()
            if start_success:
                return jsonify({
                    'success': True,
                    'message': 'All services restarted successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to start services after stopping'
                }), 500
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to stop services for restart'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def is_docker_available():
    """Check if Docker client is available and working"""
    global docker_client
    if docker_client is None:
        return False
    try:
        docker_client.ping()
        return True
    except Exception:
        return False

    # Removed unreachable/invalid code block

@app.route('/api/docker-compose/service/<service_name>', methods=['GET'])
def get_service_config(service_name):
    """Get configuration for a specific service"""
    try:
        compose_path = os.path.join(os.getcwd(), 'docker-compose.yml')
        if not os.path.exists(compose_path):
            return jsonify({
                'success': False,
                'error': 'docker-compose.yml not found'
            }), 404
        
        with open(compose_path, 'r') as f:
            compose_data = yaml.safe_load(f)
        
        if 'services' not in compose_data or service_name not in compose_data['services']:
            return jsonify({
                'success': False,
                'error': f'Service {service_name} not found'
            }), 404
        
        service_config = compose_data['services'][service_name]
        service_yaml = yaml.dump({service_name: service_config}, default_flow_style=False)
        
        return jsonify({
            'success': True,
            'service': service_config,
            'yaml': service_yaml
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/docker-compose/service/<service_name>', methods=['PUT'])
def update_service_config(service_name):
    """Update configuration for a specific service"""
    try:
        data = request.get_json()
        compose_path = os.path.join(os.getcwd(), 'docker-compose.yml')
        
        if not os.path.exists(compose_path):
            return jsonify({
                'success': False,
                'error': 'docker-compose.yml not found'
            }), 404
        
        with open(compose_path, 'r') as f:
            compose_data = yaml.safe_load(f)
        
        if 'services' not in compose_data:
            compose_data['services'] = {}
        
        if 'yaml' in data:
            # Update from YAML
            try:
                yaml_data = yaml.safe_load(data['yaml'])
                if service_name in yaml_data:
                    compose_data['services'][service_name] = yaml_data[service_name]
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Service name mismatch in YAML'
                    }), 400
            except yaml.YAMLError as e:
                return jsonify({
                    'success': False,
                    'error': f'Invalid YAML: {str(e)}'
                }), 400
        else:
            # Update from visual form
            service_config = {}
            
            if data.get('image'):
                service_config['image'] = data['image']
            if data.get('container_name'):
                service_config['container_name'] = data['container_name']
            if data.get('restart'):
                service_config['restart'] = data['restart']
            if data.get('ports'):
                service_config['ports'] = [p for p in data['ports'] if p.strip()]
            if data.get('volumes'):
                service_config['volumes'] = [v for v in data['volumes'] if v.strip()]
            if data.get('command'):
                if ' ' in data['command']:
                    service_config['command'] = data['command'].split()
                else:
                    service_config['command'] = data['command']
            if data.get('environment'):
                service_config['environment'] = [e for e in data['environment'] if e.strip()]
            if data.get('networks'):
                service_config['networks'] = data['networks']
            
            compose_data['services'][service_name] = service_config
        
        # Write back to file
        with open(compose_path, 'w') as f:
            yaml.dump(compose_data, f, default_flow_style=False, sort_keys=False)
        
        return jsonify({
            'success': True,
            'message': f'Service {service_name} updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/docker-compose/validate', methods=['POST'])
def validate_yaml():
    """Validate YAML content"""
    try:
        data = request.get_json()
        yaml_content = data.get('yaml', '')
        
        # Try to parse the YAML
        yaml.safe_load(yaml_content)
        
        return jsonify({
            'valid': True,
            'message': 'YAML is valid'
        })
    except yaml.YAMLError as e:
        return jsonify({
            'valid': False,
            'error': str(e)
        })
    except Exception as e:
        return jsonify({
            'valid': False,
            'error': str(e)
        })

@app.route('/api/docker-compose/validate-port-consistency/<service_name>', methods=['GET'])
def validate_port_consistency_api(service_name):
    """API endpoint to validate port consistency for a service"""
    try:
        # Get the compose data and service configuration
        compose_data = manager.load_docker_compose()
        if not compose_data or 'services' not in compose_data:
            return jsonify({
                'success': False,
                'error': 'No docker-compose.yml found or no services defined',
                'consistent': False
            })
        
        if service_name not in compose_data['services']:
            return jsonify({
                'success': False,
                'error': f'Service {service_name} not found',
                'consistent': False
            })
        
        service_config = compose_data['services'][service_name]
        
        # Try to determine config file from service environment or command
        config_file = 'Unknown'
        if 'command' in service_config:
            command = service_config['command']
            if isinstance(command, list):
                command = ' '.join(command)
            
            # Look for --config parameter in command
            if '--config' in command:
                parts = command.split('--config')
                if len(parts) > 1:
                    config_part = parts[1].strip().split()[0]
                    config_file = config_part  # Keep full Docker path for consistency
        
        # Also check environment variables
        if 'environment' in service_config:
            env_vars = service_config['environment']
            if isinstance(env_vars, list):
                for env_var in env_vars:
                    if 'CONFIG_FILE=' in env_var:
                        config_file = env_var.split('CONFIG_FILE=')[1]
                        break
            elif isinstance(env_vars, dict):
                config_file = env_vars.get('CONFIG_FILE', config_file)
        
        result = manager.validate_port_consistency(service_name, service_config, config_file)
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'consistent': False
        })

@app.route('/api/docker-compose/validate-strategy/<service_name>', methods=['GET'])
def validate_strategy_api(service_name):
    """API endpoint to validate strategy for a service"""
    try:
        # Get the compose data and service configuration
        compose_data = manager.load_docker_compose()
        if not compose_data or 'services' not in compose_data:
            return jsonify({
                'success': False,
                'error': 'No docker-compose.yml found or no services defined',
                'valid': False
            })
        
        if service_name not in compose_data['services']:
            return jsonify({
                'success': False,
                'error': f'Service {service_name} not found',
                'valid': False
            })
        
        service_config = compose_data['services'][service_name]
        
        # Extract strategy from service environment or command
        strategy = 'Unknown'
        
        # Check environment variables
        if 'environment' in service_config:
            env_vars = service_config['environment']
            if isinstance(env_vars, list):
                for env_var in env_vars:
                    if isinstance(env_var, str) and 'STRATEGY=' in env_var:
                        strategy = env_var.split('STRATEGY=')[1]
                        break
        
        # Check command arguments
        if 'command' in service_config:
            command = service_config['command']
            command_str = ""
            
            if isinstance(command, list):
                command_str = " ".join(command)
            elif isinstance(command, str):
                command_str = command
            
            # Debug: temporarily log the raw command for freqtrade_godstra_hyperopt
            if service_name == 'freqtrade_godstra_hyperopt':
                logger.debug(f"{service_name}: Raw command type: {type(command)}")
                logger.debug(f"{service_name}: Raw command: {repr(command)}")
                logger.debug(f"{service_name}: Command string: {repr(command_str)}")
            
            # Handle shell commands with -c flag - normalize whitespace and newlines
            if '-c' in command_str and 'freqtrade' in command_str:
                # Normalize whitespace and newlines for parsing
                normalized_command = ' '.join(command_str.split())
                
                if service_name == 'freqtrade_godstra_hyperopt':
                    logger.debug(f"{service_name}: Normalized: {repr(normalized_command)}")
                
                # Extract content between quotes for shell commands - handle multi-line
                import re
                # Try different quote patterns to handle YAML multi-line strings
                shell_patterns = [
                    r'-c\s+"(.+)"',               # Double quotes - simple and robust
                    r"-c\s+'(.+)'",               # Single quotes - simple and robust
                    r'-c\s+(["\'])(.+?)\1',       # Flexible quotes with backreference
                ]
                
                shell_content = None
                for pattern in shell_patterns:
                    shell_match = re.search(pattern, normalized_command, re.DOTALL | re.MULTILINE)
                    if shell_match:
                        # Get the captured group (might be group 1 or 2 depending on pattern)
                        shell_content = shell_match.group(2) if shell_match.lastindex and shell_match.lastindex >= 2 else shell_match.group(1)
                        if service_name == 'freqtrade_godstra_hyperopt':
                            logger.debug(f"{service_name}: Pattern matched: {pattern}")
                            logger.debug(f"{service_name}: Shell content: {repr(shell_content)}")
                        break
                
                if shell_content:
                    # Look for --strategy in the shell content
                    strategy_match = re.search(r'--strategy\s+(\S+)', shell_content)
                    if strategy_match:
                        strategy = strategy_match.group(1)
                        if service_name == 'freqtrade_godstra_hyperopt':
                            logger.debug(f"{service_name}: Found strategy: {strategy}")
                        
            # Handle simple command format
            if isinstance(command, list):
                for i, arg in enumerate(command):
                    if arg == '--strategy' and i + 1 < len(command):
                        strategy = command[i + 1]
                        break
        
        result = manager.validate_strategy_availability(service_name, service_config, strategy)
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'valid': False
        })

@app.route('/api/docker-compose/validate-config/<service_name>', methods=['GET'])
def validate_config_api(service_name):
    """API endpoint to validate config file for a service"""
    try:
        # Get the compose data and service configuration
        compose_data = manager.load_docker_compose()
        if not compose_data or 'services' not in compose_data:
            return jsonify({
                'success': False,
                'error': 'No docker-compose.yml found or no services defined',
                'valid': False
            })
        
        if service_name not in compose_data['services']:
            return jsonify({
                'success': False,
                'error': f'Service {service_name} not found',
                'valid': False
            })
        
        service_config = compose_data['services'][service_name]
        
        # Extract config file from service environment or command
        config_file = 'Unknown'
        
        if 'command' in service_config:
            command = service_config['command']
            command_str = ""
            
            if isinstance(command, list):
                command_str = ' '.join(command)
            elif isinstance(command, str):
                command_str = command
            
            logger.debug(f"{service_name}: Config command_str: {repr(command_str)}")
            
            # Handle shell commands with -c flag
            if '-c' in command_str and 'freqtrade' in command_str:
                # Simple approach: just search for --config in the entire command string
                import re
                config_match = re.search(r'--config\s+(\S+)', command_str)
                logger.debug(f"{service_name}: Config match: {config_match}")
                if config_match:
                    config_file = config_match.group(1)  # Keep full Docker path
                    logger.debug(f"{service_name}: Config file extracted: {config_file}")
                        
            # Handle simple command format
            if '--config' in command_str:
                parts = command_str.split('--config')
                if len(parts) > 1:
                    config_file = parts[1].strip().split()[0]  # Keep full Docker path for consistency
        
        # Also check environment variables
        if 'environment' in service_config:
            env_vars = service_config['environment']
            if isinstance(env_vars, list):
                for env_var in env_vars:
                    if isinstance(env_var, str) and 'CONFIG_FILE=' in env_var:
                        config_file = env_var.split('CONFIG_FILE=')[1]
                        break
        
        result = manager.validate_config_file(service_name, service_config, config_file)
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'valid': False
        })

@app.route('/api/docker-compose/validate-all/<service_name>', methods=['GET'])
def validate_all_api(service_name):
    """API endpoint to run all validation checks for a service"""
    try:
        # Get the compose data and service configuration
        compose_data = manager.load_docker_compose()
        if not compose_data or 'services' not in compose_data:
            return jsonify({
                'success': False,
                'error': 'No docker-compose.yml found or no services defined'
            })
        
        if service_name not in compose_data['services']:
            return jsonify({
                'success': False,
                'error': f'Service {service_name} not found'
            })
        
        service_config = compose_data['services'][service_name]
        
        # Extract strategy and config from service
        strategy = 'Unknown'
        config_file = 'Unknown'
        
        # Check environment variables
        if 'environment' in service_config:
            env_vars = service_config['environment']
            if isinstance(env_vars, list):
                for env_var in env_vars:
                    if isinstance(env_var, str):
                        if 'STRATEGY=' in env_var:
                            strategy = env_var.split('STRATEGY=')[1]
                        elif 'CONFIG_FILE=' in env_var:
                            config_file = env_var.split('CONFIG_FILE=')[1]
        
        # Check command arguments
        if 'command' in service_config:
            command = service_config['command']
            if isinstance(command, list):
                for i, arg in enumerate(command):
                    if arg == '--strategy' and i + 1 < len(command):
                        strategy = command[i + 1]
                    elif arg == '--config' and i + 1 < len(command):
                        config_part = command[i + 1]
                        config_file = config_part  # Keep full Docker path for consistency
        
        # Run all validations
        port_result = manager.validate_port_consistency(service_name, service_config, config_file)
        strategy_result = manager.validate_strategy_availability(service_name, service_config, strategy)
        config_result = manager.validate_config_file(service_name, service_config, config_file)
        
        # Determine overall status with priority system
        overall_valid = True
        overall_priority = 'success'
        issues = []
        
        # Port consistency (highest priority for conflicts)
        if not port_result.get('consistent', False):
            if port_result.get('port_conflicts', []):
                overall_valid = False
                overall_priority = 'error'
                issues.append(f"Port conflicts: {port_result.get('message', '')}")
            elif port_result.get('config_missing', True):
                if overall_priority not in ['error']:
                    overall_priority = 'warning'
                issues.append("Config file missing")
        
        # Strategy validation
        if not strategy_result.get('valid', False):
            if strategy_result.get('priority') == 'error':
                overall_valid = False
                overall_priority = 'error'
            elif strategy_result.get('priority') == 'warning' and overall_priority not in ['error']:
                overall_priority = 'warning'
            issues.append(f"Strategy: {strategy_result.get('message', '')}")
        
        # Config validation
        if not config_result.get('valid', False):
            if config_result.get('priority') == 'error':
                overall_valid = False
                overall_priority = 'error'
            elif config_result.get('priority') == 'warning' and overall_priority not in ['error']:
                overall_priority = 'warning'
            issues.append(f"Config: {config_result.get('message', '')}")
        
        return jsonify({
            'success': True,
            'overall_valid': overall_valid,
            'overall_priority': overall_priority,
            'summary': '; '.join(issues) if issues else 'All validations passed',
            'port_consistency': port_result,
            'strategy_validation': strategy_result,
            'config_validation': config_result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/docker-compose/rationalize', methods=['POST'])
def rationalize_yaml_api():
    """API endpoint to rationalize and fix Docker Compose YAML"""
    try:
        data = request.get_json()
        if not data or 'yaml_content' not in data:
            return jsonify({
                'success': False,
                'error': 'YAML content is required'
            })
        
        yaml_content = data['yaml_content']
        success, result, issues_found, issues_fixed = manager.rationalize_docker_compose_yaml(yaml_content)
        
        if success:
            return jsonify({
                'success': True,
                'rationalized_yaml': result,
                'issues_found': issues_found,
                'issues_fixed': issues_fixed,
                'has_issues': len(issues_found) > 0,
                'has_fixes': len(issues_fixed) > 0
            })
        else:
            return jsonify({
                'success': False,
                'error': result,
                'issues_found': issues_found,
                'issues_fixed': issues_fixed
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


# --- STRATEGY API ENDPOINTS (after app and class definitions, before main) ---

manager = FreqTradeManager()

@app.route('/api/strategy', methods=['POST'])
def api_create_strategy():
    data = request.get_json()
    name = data.get('name', '').strip()
    code = data.get('code', '')
    category = data.get('category', 'custom')
    description = data.get('description', '')
    if not name or not code:
        return jsonify({'success': False, 'error': 'Name and code are required.'}), 400
    filename = secure_filename(f"{name}.py")
    filepath = STRATEGIES_PATH / filename
    if filepath.exists():
        return jsonify({'success': False, 'error': 'File already exists.'}), 409
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        # Optionally save description/category to a metadata file
        meta = {'name': name, 'category': category, 'description': description}
        with open(STRATEGIES_PATH / f"{name}.meta.json", 'w', encoding='utf-8') as mf:
            json.dump(meta, mf)
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# --- CLONE STRATEGY ENDPOINT ---
@app.route('/api/strategy/clone', methods=['POST'])
def clone_strategy():
    data = request.get_json()
    name = data.get('name', '').strip()
    code = data.get('code', '')
    category = data.get('category', 'custom')
    if not name or not code:
        return jsonify({'success': False, 'error': 'Name and code are required.'}), 400
    filename = secure_filename(f"{name}.py")
    filepath = STRATEGIES_PATH / filename
    if filepath.exists():
        return jsonify({'success': False, 'error': 'File already exists.'}), 409
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        meta = {'name': name, 'category': category}
        with open(STRATEGIES_PATH / f"{name}.meta.json", 'w', encoding='utf-8') as mf:
            json.dump(meta, mf)
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategy/upload', methods=['POST'])
def api_upload_strategy():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded.'}), 400
    file = request.files['file']
    category = request.form.get('category', 'custom')
    overwrite = request.form.get('overwrite', 'false') == 'true'
    description = request.form.get('description', '')
    if not file or not file.filename or not file.filename.endswith('.py'):
        return jsonify({'success': False, 'error': 'Only .py files allowed.'}), 400
    filename = secure_filename(file.filename)
    filepath = STRATEGIES_PATH / filename
    if filepath.exists() and not overwrite:
        return jsonify({'success': False, 'error': 'File already exists.'}), 409
    try:
        file.save(filepath)
        # Optionally save description/category to a metadata file
        meta = {'name': filename[:-3], 'category': category, 'description': description}
        with open(STRATEGIES_PATH / f"{filename[:-3]}.meta.json", 'w', encoding='utf-8') as mf:
            json.dump(meta, mf)
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategy/<filename>')
def get_strategy(filename):
    """Get strategy file contents"""
    try:
        strategy_path = STRATEGIES_PATH / filename
        if not strategy_path.exists():
            return jsonify({'error': 'Strategy not found'}), 404
        with open(strategy_path, 'r', encoding='utf-8') as f:
            code = f.read()
        # Optionally load metadata
        meta_path = STRATEGIES_PATH / f"{filename[:-3]}.meta.json"
        meta = {}
        if meta_path.exists():
            with open(meta_path, 'r', encoding='utf-8') as mf:
                meta = json.load(mf)
        return jsonify({'success': True, 'filename': filename, 'code': code, 'meta': meta})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategy/<filename>', methods=['PUT'])
def update_strategy(filename):
    """Update the code for a strategy file."""
    import os
    from flask import request
    import re
    # Only allow .py files
    if not filename.endswith('.py') or not re.match(r'^[\w\-.]+\.py$', filename):
        return jsonify({'success': False, 'error': 'Invalid filename.'}), 400
    strategies_dir = STRATEGIES_PATH if 'STRATEGIES_PATH' in globals() else os.path.join(os.path.dirname(__file__), '../user_data/strategies')
    file_path = os.path.join(strategies_dir, filename)
    try:
        code = request.get_data(as_text=True)
        # Optionally: add server-side Python syntax validation here
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategy/<filename>', methods=['DELETE'])
def delete_strategy(filename):
    """Delete a strategy file"""
    try:
        strategy_path = STRATEGIES_PATH / filename
        meta_path = STRATEGIES_PATH / f"{filename[:-3]}.meta.json"
        if not strategy_path.exists():
            return jsonify({'success': False, 'error': 'Strategy not found'}), 404
        os.remove(strategy_path)
        if meta_path.exists():
            os.remove(meta_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# --- END STRATEGY API ENDPOINTS ---

@app.route('/api/docker-compose/validate-yaml', methods=['POST'])
def validate_yaml_api():
    """API endpoint to validate Docker Compose YAML without changes"""
    try:
        data = request.get_json()
        if not data or 'yaml_content' not in data:
            return jsonify({
                'success': False,
                'error': 'YAML content is required'
            })
        
        yaml_content = data['yaml_content']
        is_valid, message = manager.validate_docker_compose_yaml(yaml_content)
        
        return jsonify({
            'success': True,
            'valid': is_valid,
            'message': message
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

from flask import abort
import subprocess
import time

# Helper for TCP Docker client (must be above route)
def get_tcp_docker_client():
    try:
        return docker.DockerClient(base_url='tcp://localhost:2375')
    except Exception as e:
        raise RuntimeError(f"Could not connect to Docker via TCP: {e}")

if __name__ == '__main__':
    # Create directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
