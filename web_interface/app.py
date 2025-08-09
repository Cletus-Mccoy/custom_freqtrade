#!/usr/bin/env python3
"""
FreqTrade Web Management Interface
A Flask-based web application for managing FreqTrade strategies, pairlists, and Docker containers.
"""

import os
import json
import subprocess
import datetime
import yaml
import warnings
import shutil
import traceback
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import docker
from werkzeug.utils import secure_filename

# Suppress cryptography deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="cryptography")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="paramiko")

app = Flask(__name__)
app.secret_key = 'freqtrade_web_interface_2025'

# Configuration
BASE_PATH = Path(__file__).parent.parent
USER_DATA_PATH = BASE_PATH / "user_data"
PAIRLISTS_PATH = USER_DATA_PATH / "pairlists"
STRATEGIES_PATH = USER_DATA_PATH / "strategies"
CONFIGS_PATH = USER_DATA_PATH

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
            print(f"Attempting Docker connection method {i}: {conn_config['name']}")
            client = conn_config['method']()
            
            # Test the connection with timeout
            client.ping()
            
            # Additional test - try to get Docker info
            info = client.info()
            
            docker_client = client
            print(f"✅ Docker client connected successfully using {conn_config['name']}")
            print(f"   Docker version: {info.get('ServerVersion', 'Unknown')}")
            print("   All Docker features are available!")
            return True
            
        except Exception as e:
            print(f"❌ {conn_config['name']} failed: {str(e)}")
            continue
    
    print("\n⚠️  All Docker connection methods failed.")
    print("   Please ensure Docker Desktop is running and accessible.")
    print("   You can still use the web interface for configuration management.")
    print("   To fix Docker connection:")
    print("   1. Start Docker Desktop")
    print("   2. Ensure Docker is running (check system tray)")
    print("   3. Restart this application")
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
    def __init__(self):
        self.base_path = BASE_PATH
        self.user_data_path = USER_DATA_PATH
        self.pairlists_path = PAIRLISTS_PATH
        self.strategies_path = STRATEGIES_PATH
        self.configs_path = CONFIGS_PATH
        self.docker_compose_path = BASE_PATH / "docker-compose.yml"
        
    def get_available_pairlists(self):
        """Get all available pairlist files"""
        pairlists = []
        if self.pairlists_path.exists():
            for file in self.pairlists_path.glob("*.json"):
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                    pairlists.append({
                        'name': file.name,
                        'filename': file.name,
                        'path': str(file),
                        'pairs_count': len(data.get('pair_whitelist', [])),
                        'category': self._categorize_pairlist(file.name)
                    })
                except Exception as e:
                    print(f"Error reading pairlist {file}: {e}")
        return sorted(pairlists, key=lambda x: x['name'])
    
    def _categorize_pairlist(self, filename):
        """Categorize pairlist based on filename"""
        filename_lower = filename.lower()
        if 'test' in filename_lower:
            return 'test'
        elif 'freqai' in filename_lower:
            return 'freqai'
        elif 'full' in filename_lower or 'all' in filename_lower:
            return 'full'
        elif 'top' in filename_lower or 'volume' in filename_lower:
            return 'popular'
        else:
            return 'custom'
    
    def get_available_strategies(self):
        """Get all available strategy files"""
        strategies = []
        if self.strategies_path.exists():
            for file in self.strategies_path.glob("*.py"):
                if not file.name.startswith('__'):
                    strategies.append({
                        'name': file.stem,
                        'filename': file.name,
                        'path': str(file),
                        'modified': datetime.datetime.fromtimestamp(file.stat().st_mtime).strftime('%Y-%m-%d %H:%M'),
                        'type': self._categorize_strategy(file.name)
                    })
        return sorted(strategies, key=lambda x: x['name'])
    
    def _categorize_strategy(self, filename):
        """Categorize strategy based on filename"""
        filename_lower = filename.lower()
        if 'freqai' in filename_lower:
            return 'freqai'
        elif 'example' in filename_lower or 'sample' in filename_lower:
            return 'example'
        elif 'test' in filename_lower:
            return 'test'
        else:
            return 'custom'
    
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
                        'location': 'configs'
                    })
                except Exception as e:
                    print(f"Error reading config {file}: {e}")
        
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
                        'location': 'user_data'
                    })
                except Exception as e:
                    print(f"Error reading config {file}: {e}")
        
        return sorted(configs, key=lambda x: x['name'])
    
    def get_docker_containers(self):
        """Get FreqTrade Docker containers"""
        containers = []
        if docker_client:
            try:
                all_containers = docker_client.containers.list(all=True)
                for container in all_containers:
                    if 'freqtrade' in container.name.lower():
                        containers.append({
                            'name': container.name,
                            'id': container.short_id,
                            'status': container.status,
                            'image': container.image.tags[0] if container.image.tags else 'unknown',
                            'created': container.attrs['Created'],
                            'ports': container.ports
                        })
            except Exception as e:
                print(f"Error getting containers: {e}")
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

    def create_config_from_template(self, template_config, strategy, pairlist, container_name):
        """Create a new config file from template"""
        try:
            print(f"Creating config from template: {template_config}")
            
            # Validate inputs
            if not all([template_config, strategy, pairlist, container_name]):
                raise ValueError("All parameters are required")
            
            # Find template config file using helper method
            template_path = self.find_config_file(template_config)
            if not template_path:
                raise FileNotFoundError(f"Template config file '{template_config}' not found in configs or user_data directories")
            
            print(f"Found template at: {template_path}")
            
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
            
            print(f"Loaded pairlist with {len(pairlist_data['pair_whitelist'])} pairs")
            
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
                print("Updated FreqAI correlation pairs")
            
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
            print(f"Saving config to: {new_config_path}")
            
            with open(new_config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            
            print(f"Config created successfully: {new_config_path}")
            return str(new_config_path)
            
        except Exception as e:
            print(f"Error creating config from template: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Error creating config: {e}")

    def create_custom_config(self, custom_config, strategy, pairlist, container_name):
        """Create a new config file from custom settings"""
        try:
            print(f"Creating custom config for container: {container_name}")
            
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
            
            print(f"Loaded pairlist with {len(pairlist_data['pair_whitelist'])} pairs")
            
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
                
                print(f"Added FreqAI configuration with model: {model_type}")
            
            # Save new config
            new_config_path = self.configs_path / f"config_{container_name}.json"
            print(f"Saving custom config to: {new_config_path}")
            
            with open(new_config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            
            print(f"Custom config created successfully: {new_config_path}")
            return str(new_config_path)
            
        except Exception as e:
            print(f"Error creating custom config: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Error creating custom config: {e}")

    def get_docker_services(self):
        """Get all services from docker-compose.yml"""
        compose_data = self.load_docker_compose()
        if compose_data and 'services' in compose_data:
            return list(compose_data['services'].keys())
        return []
    
    def load_docker_compose(self):
        """Load docker-compose.yml file"""
        try:
            if self.docker_compose_path.exists():
                with open(self.docker_compose_path, 'r') as f:
                    return yaml.safe_load(f)
            return None
        except Exception as e:
            print(f"Error loading docker-compose.yml: {e}")
            return None
    
    def save_docker_compose(self, compose_data):
        """Save docker-compose.yml file with proper formatting"""
        try:
            print(f"Saving docker-compose.yml with {len(compose_data.get('services', {}))} services")
            
            # Backup the original file
            if self.docker_compose_path.exists():
                backup_path = self.docker_compose_path.with_suffix('.yml.backup')
                import shutil
                shutil.copy2(self.docker_compose_path, backup_path)
                print(f"Backup created: {backup_path}")
            
            # Ensure proper structure
            if 'version' not in compose_data:
                compose_data['version'] = '3.8'
            
            # Write with proper YAML formatting
            with open(self.docker_compose_path, 'w', encoding='utf-8') as f:
                yaml.dump(compose_data, f, 
                         default_flow_style=False, 
                         indent=2,
                         sort_keys=False,
                         allow_unicode=True,
                         width=120)
            
            print(f"Successfully saved docker-compose.yml")
            return True
            
        except Exception as e:
            print(f"Error saving docker-compose.yml: {e}")
            import traceback
            traceback.print_exc()
            return False
    
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
                
                service_info['strategy'] = strategy
                service_info['config_file'] = config_file
                
                services_dict[service_name] = service_info
        
        return services_dict
    
    def get_docker_compose_content(self):
        """Get the raw docker-compose.yml content"""
        try:
            with open(self.docker_compose_path, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading docker-compose.yml: {e}")
            return "# Error reading docker-compose.yml"
    
    def add_docker_service(self, service_name, strategy, config_file, pairlist_file, external_api_port=8081):
        """Add a new service to docker-compose.yml"""
        try:
            print(f"Adding Docker service: {service_name}")
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
                print(f"Service {service_name} already exists")
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
            print(f"Docker service addition result: {success}")
            return success
            
        except Exception as e:
            print(f"Error adding Docker service: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def remove_docker_service(self, service_name):
        """Remove a service from docker-compose.yml"""
        try:
            compose_data = self.load_docker_compose()
            if compose_data and 'services' in compose_data:
                if service_name in compose_data['services']:
                    del compose_data['services'][service_name]
                    return self.save_docker_compose(compose_data)
            return False
        except Exception as e:
            print(f"Error removing Docker service: {e}")
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
                        print(f"Successfully started service: {service_name} (using 'docker compose')")
                        return True
                    else:
                        print(f"Failed with 'docker compose': {result.stderr}")
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
                        print(f"Successfully started service: {service_name} (using 'docker-compose')")
                        return True
                    else:
                        print(f"Failed to start service {service_name}: {result.stderr}")
                        return False
                    
            finally:
                # Always restore original directory
                os.chdir(original_dir)
                
        except subprocess.TimeoutExpired:
            print(f"Timeout starting service: {service_name}")
            return False
        except Exception as e:
            print(f"Error starting Docker service: {e}")
            return False
    
    def stop_docker_service(self, service_name):
        """Stop a specific Docker service"""
        try:
            print(f"Stopping Docker service: {service_name}")
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
                    print(f"Successfully stopped service: {service_name} (using 'docker compose')")
                    return True
                else:
                    print(f"Failed to stop service {service_name} with 'docker compose': {result.stderr}")
            except subprocess.TimeoutExpired:
                print(f"Timeout stopping service {service_name} with 'docker compose'")
            except Exception as e:
                print(f"Error with 'docker compose' stop: {e}")
            
            # Fallback to legacy syntax
            try:
                result = subprocess.run(
                    ['docker-compose', 'stop', service_name],
                    capture_output=True,
                    text=True,
                    timeout=120  # 2 minutes timeout
                )
                
                if result.returncode == 0:
                    print(f"Successfully stopped service: {service_name} (using 'docker-compose')")
                    return True
                else:
                    print(f"Failed to stop service {service_name} with 'docker-compose': {result.stderr}")
            except subprocess.TimeoutExpired:
                print(f"Timeout stopping service {service_name} with 'docker-compose'")
                
        except Exception as e:
            print(f"Error stopping Docker service: {e}")
            return False
    
    def restart_docker_service(self, service_name):
        """Restart a specific Docker service"""
        try:
            print(f"Restarting Docker service: {service_name}")
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
                    print(f"Successfully restarted service: {service_name} (using 'docker compose')")
                    return True
                else:
                    print(f"Failed to restart service {service_name} with 'docker compose': {result.stderr}")
            except subprocess.TimeoutExpired:
                print(f"Timeout restarting service {service_name} with 'docker compose'")
            except Exception as e:
                print(f"Error with 'docker compose' restart: {e}")
            
            # Fallback to legacy syntax
            try:
                result = subprocess.run(
                    ['docker-compose', 'restart', service_name],
                    capture_output=True,
                    text=True,
                    timeout=180  # 3 minutes timeout
                )
                
                if result.returncode == 0:
                    print(f"Successfully restarted service: {service_name} (using 'docker-compose')")
                    return True
                else:
                    print(f"Failed to restart service {service_name} with 'docker-compose': {result.stderr}")
            except subprocess.TimeoutExpired:
                print(f"Timeout restarting service {service_name} with 'docker-compose'")
                
        except Exception as e:
            print(f"Error restarting Docker service: {e}")
            return False
    
    def start_all_docker_services(self):
        """Start all Docker services"""
        try:
            print("Starting all Docker services...")
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
                    print("Successfully started all services (using 'docker compose')")
                    return True
                else:
                    print(f"Failed to start all services with 'docker compose': {result.stderr}")
            except subprocess.TimeoutExpired:
                print("Timeout starting all services with 'docker compose'")
            except Exception as e:
                print(f"Error with 'docker compose' up: {e}")
            
            # Fallback to legacy syntax
            try:
                result = subprocess.run(
                    ['docker-compose', 'up', '-d'],
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minutes timeout
                )
                
                if result.returncode == 0:
                    print("Successfully started all services (using 'docker-compose')")
                    return True
                else:
                    print(f"Failed to start all services with 'docker-compose': {result.stderr}")
            except subprocess.TimeoutExpired:
                print("Timeout starting all services with 'docker-compose'")
                
        except Exception as e:
            print(f"Error starting all Docker services: {e}")
            return False
    
    def stop_all_docker_services(self):
        """Stop all Docker services"""
        try:
            print("Stopping all Docker services...")
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
                    print("Successfully stopped all services (using 'docker compose')")
                    return True
                else:
                    print(f"Failed to stop all services with 'docker compose': {result.stderr}")
            except subprocess.TimeoutExpired:
                print("Timeout stopping all services with 'docker compose'")
            except Exception as e:
                print(f"Error with 'docker compose' down: {e}")
            
            # Fallback to legacy syntax
            try:
                result = subprocess.run(
                    ['docker-compose', 'down'],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes timeout
                )
                
                if result.returncode == 0:
                    print("Successfully stopped all services (using 'docker-compose')")
                    return True
                else:
                    print(f"Failed to stop all services with 'docker-compose': {result.stderr}")
            except subprocess.TimeoutExpired:
                print("Timeout stopping all services with 'docker-compose'")
                
        except Exception as e:
            print(f"Error stopping all Docker services: {e}")
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
                    return "not_found"
            except Exception as e:
                print(f"Error with 'docker compose' ps: {e}")
            
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
                    return "not_found"
            except Exception:
                pass
                
        except Exception as e:
            print(f"Error getting service status: {e}")
            
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
            print(f"Error fixing Docker Compose formatting: {e}")
            return False

    def get_docker_networks(self):
        """Get all networks from docker-compose.yml"""
        try:
            compose_data = self.load_docker_compose()
            if compose_data and 'networks' in compose_data:
                return compose_data['networks']
            return {}
        except Exception as e:
            print(f"Error getting Docker networks: {e}")
            return {}
    
    def add_docker_network(self, network_name, driver='bridge'):
        """Add a network to docker-compose.yml"""
        try:
            compose_data = self.load_docker_compose()
            if not compose_data:
                compose_data = {'services': {}, 'networks': {}}
            
            if 'networks' not in compose_data:
                compose_data['networks'] = {}
            
            compose_data['networks'][network_name] = {
                'driver': driver
            }
            
            return self.save_docker_compose(compose_data)
        except Exception as e:
            print(f"Error adding Docker network: {e}")
            return False
    
    def remove_docker_network(self, network_name):
        """Remove a network from docker-compose.yml"""
        try:
            compose_data = self.load_docker_compose()
            if compose_data and 'networks' in compose_data:
                if network_name in compose_data['networks']:
                    del compose_data['networks'][network_name]
                    return self.save_docker_compose(compose_data)
            return False
        except Exception as e:
            print(f"Error removing Docker network: {e}")
            return False

manager = FreqTradeManager()

@app.route('/')
def index():
    """Main dashboard"""
    containers = manager.get_docker_containers()
    return render_template('index.html', containers=containers)

@app.route('/pairlists')
def pairlists():
    """Pairlist management page"""
    pairlists = manager.get_available_pairlists()
    return render_template('pairlists.html', pairlists=pairlists)

@app.route('/strategies')
def strategies():
    """Strategy management page"""
    strategies = manager.get_available_strategies()
    return render_template('strategies.html', strategies=strategies)

@app.route('/configs')
def configs():
    """Config management page"""
    configs = manager.get_available_configs()
    return render_template('configs.html', configs=configs)

@app.route('/services')
def services():
    """Docker services management page"""
    services = manager.get_docker_services_detailed()
    compose_yaml = manager.get_docker_compose_content()
    print(f"DEBUG: Services route called")
    print(f"DEBUG: services data length: {len(str(services)) if services else 0}")
    print(f"DEBUG: compose_yaml length: {len(compose_yaml) if compose_yaml else 0}")
    if compose_yaml:
        print(f"DEBUG: compose_yaml preview: {compose_yaml[:100]}...")
    return render_template('services.html', services=services, compose_yaml=compose_yaml)

@app.route('/containers')
def containers():
    """Running containers page (different from services)"""
    containers = manager.get_docker_containers()
    return render_template('containers.html', containers=containers)

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
            
    except docker.errors.NotFound:
        return jsonify({'error': f'Container {container_name} not found'}), 404
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
    except docker.errors.NotFound:
        return jsonify({'error': f'Container {container_name} not found'}), 404
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

@app.route('/api/config/<filename>')
def get_config(filename):
    """Get config details"""
    try:
        config_path = manager.configs_path / filename
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

@app.route('/api/docker-compose/update', methods=['POST'])
def update_docker_compose():
    """Update docker-compose.yml with new service"""
    try:
        data = request.json
        service_name = data['service_name']
        strategy = data['strategy']
        config_file = data['config_file']
        pairlist_file = data['pairlist_file']
        
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
            data.get('external_api_port', 8081)
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

@app.route('/api/docker-compose/remove/<service_name>', methods=['DELETE'])
def remove_docker_service(service_name):
    """Remove a service from docker-compose.yml"""
    try:
        # Use global manager instead of creating new instance
        success = manager.remove_docker_service(service_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Successfully removed {service_name} from docker-compose.yml'
            })
        else:
            return jsonify({
                'error': f'Failed to remove {service_name} from docker-compose.yml'
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

@app.route('/api/docker/compose', methods=['POST'])
def save_docker_compose():
    """Save Docker Compose content"""
    try:
        data = request.get_json()
        content = data.get('content', '')
        
        # Parse and save the YAML content
        import yaml
        try:
            yaml_data = yaml.safe_load(content)
            success = manager.save_docker_compose(yaml_data)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Docker Compose saved successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to save Docker Compose file'
                }), 500
        except yaml.YAMLError as e:
            return jsonify({
                'success': False,
                'error': f'YAML syntax error: {str(e)}'
            }), 400
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
                'message': 'Docker client reconnected successfully',
                'status': get_docker_status()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to reconnect to Docker',
                'status': get_docker_status()
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

@app.route('/api/docker/networks', methods=['GET'])
def get_docker_networks():
    """Get all Docker networks from docker-compose.yml"""
    try:
        networks = manager.get_docker_networks()
        return jsonify({
            'success': True,
            'networks': networks
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/docker/networks', methods=['POST'])
def add_docker_network():
    """Add a new Docker network to docker-compose.yml"""
    try:
        data = request.get_json()
        name = data.get('name')
        driver = data.get('driver', 'bridge')
        
        if not name:
            return jsonify({
                'success': False,
                'error': 'Network name is required'
            }), 400
        
        success = manager.add_docker_network(name, driver)
        if success:
            return jsonify({
                'success': True,
                'message': f'Network {name} added successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to add network'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/docker/networks/<network_name>', methods=['DELETE'])
def remove_docker_network(network_name):
    """Remove a Docker network from docker-compose.yml"""
    try:
        success = manager.remove_docker_network(network_name)
        if success:
            return jsonify({
                'success': True,
                'message': f'Network {network_name} removed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to remove network'
            }), 500
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

def get_docker_status():
    """Get detailed Docker status information"""
    if not is_docker_available():
        return {
            'available': False,
            'error': 'Docker client not connected',
            'containers': [],
            'images': []
        }
    
    try:
        containers = []
        for container in docker_client.containers.list(all=True):
            containers.append({
                'id': container.id[:12],
                'name': container.name,
                'status': container.status,
                'image': container.image.tags[0] if container.image.tags else 'unknown'
            })
        
        images = []
        for image in docker_client.images.list():
            images.append({
                'id': image.id[:12],
                'tags': image.tags,
                'size': image.attrs.get('Size', 0)
            })
        
        return {
            'available': True,
            'error': None,
            'containers': containers,
            'images': images
        }
    except Exception as e:
        return {
            'available': False,
            'error': str(e),
            'containers': [],
            'images': []
        }

if __name__ == '__main__':
    # Create directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
