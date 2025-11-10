#!/usr/bin/env python3

import sys
sys.path.append('.')
from app import FreqTradeManager

# Initialize manager
manager = FreqTradeManager()

# Test the validation for test122 service
compose_data = manager.load_docker_compose()
if compose_data and 'services' in compose_data and 'test122' in compose_data['services']:
    service_config = compose_data['services']['test122']
    
    print('=== test122 Service Configuration ===')
    print('Command:', service_config.get('command'))
    print('Environment:', service_config.get('environment'))
    print()
    
    # Extract strategy from command
    command_strategy = 'Unknown'
    if 'command' in service_config:
        command = service_config['command']
        if isinstance(command, list):
            for i, arg in enumerate(command):
                if arg == '--strategy' and i + 1 < len(command):
                    command_strategy = command[i + 1]
                    break
    
    # Extract strategy from environment
    env_strategy = 'Unknown'
    if 'environment' in service_config:
        env_vars = service_config['environment']
        if isinstance(env_vars, list):
            for env_var in env_vars:
                if isinstance(env_var, str) and 'FREQTRADE_STRATEGY=' in env_var:
                    env_strategy = env_var.split('FREQTRADE_STRATEGY=')[1]
                    break
    
    print(f'Strategy from command: {command_strategy}')
    print(f'Strategy from environment: {env_strategy}')
    print(f'Match: {command_strategy == env_strategy}')
    print()
    
    # Check if strategies exist
    print('=== Strategy File Validation ===')
    for strategy_name in [command_strategy, env_strategy]:
        if strategy_name != 'Unknown':
            strategy_result = manager.validate_strategy_availability('test122', service_config, strategy_name)
            print(f'Strategy "{strategy_name}":')
            print(f'  Found: {strategy_result.get("strategy_found", False)}')
            print(f'  Valid: {strategy_result.get("valid", False)}')
            print(f'  Path: {strategy_result.get("strategy_path", "N/A")}')
            print(f'  Message: {strategy_result.get("message", "N/A")}')
            print()
    
    # Extract and validate config
    print('=== Config File Validation ===')
    config_file = 'Unknown'
    if 'command' in service_config:
        command = service_config['command']
        if isinstance(command, list):
            for i, arg in enumerate(command):
                if arg == '--config' and i + 1 < len(command):
                    config_part = command[i + 1]
                    config_file = config_part.replace('/freqtrade/user_data/', '')
                    break
    
    print(f'Config file: {config_file}')
    if config_file != 'Unknown':
        config_result = manager.validate_config_file('test122', service_config, config_file)
        print('Config validation:')
        print(f'  Found: {config_result.get("config_found", False)}')
        print(f'  Valid: {config_result.get("valid", False)}')
        print(f'  Path: {config_result.get("config_path", "N/A")}')
        print(f'  Message: {config_result.get("message", "N/A")}')
        
    # Check what strategy files actually exist
    print('\n=== Available Strategy Files ===')
    strategies_path = manager.strategies_path
    if strategies_path.exists():
        strategy_files = [f.stem for f in strategies_path.glob('*.py') if f.is_file() and not f.name.startswith('__')]
        print('Available strategies:', strategy_files)
        
        # Check for similar names
        for strategy in [command_strategy, env_strategy]:
            if strategy != 'Unknown':
                similar = [s for s in strategy_files if strategy.lower() in s.lower() or s.lower() in strategy.lower()]
                if similar:
                    print(f'Similar to "{strategy}": {similar}')
    else:
        print('Strategies directory not found')

else:
    print('Service test122 not found in docker-compose.yml')
