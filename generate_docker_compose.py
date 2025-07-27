import os
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def list_files_in_directory(directory, extension):
    """List all files in a directory with a specific extension."""
    return [f for f in os.listdir(directory) if f.endswith(extension)]

def get_user_choice(options, prompt):
    """Prompt the user to select an option from a list."""
    print(prompt)
    for idx, option in enumerate(options, start=1):
        print(f"{idx}. {option}")
    
    while True:
        try:
            choice = int(input("Enter the number of your choice: "))
            if 1 <= choice <= len(options):
                return options[choice - 1]
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def generate_docker_compose(config, strategy, port, volume_name):
    """Generate a docker-compose service definition."""
    service_name = f"freqtrade_{os.path.splitext(config)[0]}"
    return {
        service_name: {
            "image": os.getenv("FREQTRADE_IMAGE", "freqtradeorg/freqtrade:stable_freqai"),
            "restart": "always",
            "container_name": service_name,
            "deploy": {
                "resources": {
                    "reservations": {
                        "devices": [
                            {
                                "driver": os.getenv("GPU_DRIVER", "nvidia"),
                                "count": 1,
                                "capabilities": ["gpu"]
                            }
                        ]
                    }
                }
            },
            "volumes": [
                f"{volume_name}:/freqtrade/user_data",
                f"./user_data/{config}:/freqtrade/user_data/config.json",
                f"./user_data/strategies/{strategy}:/freqtrade/user_data/strategies/{strategy}"
            ],
            "command": f"trade --config /freqtrade/user_data/config.json --strategy {os.path.splitext(strategy)[0]} --freqaimodel LightGBMRegressor --db-url sqlite:////freqtrade/user_data/tradesv3.sqlite --strategy-path /freqtrade/user_data/strategies",
            "ports": [
                f"0.0.0.0:{port}:8080"
            ],
            "networks": ["freqnet"]
        }
    }

def main():
    user_data_path = "./user_data"
    strategies_path = os.path.join(user_data_path, "strategies")

    # List available configs and strategies
    configs = list_files_in_directory(user_data_path, ".json")
    strategies = list_files_in_directory(strategies_path, ".py")

    if not configs:
        print("No configuration files found in user_data.")
        return

    if not strategies:
        print("No strategy files found in user_data/strategies.")
        return

    # Get user choices
    selected_config = get_user_choice(configs, "Select a configuration file:")
    selected_strategy = get_user_choice(strategies, "Select a strategy file:")

    # Generate unique port and volume name
    base_port = int(os.getenv("BASE_PORT", 8080))
    port = base_port + len(configs)  # Increment port based on the number of configs
    volume_name = f"userdata_{os.path.splitext(selected_config)[0]}"

    # Generate docker-compose content
    docker_compose_path = "docker-compose-1.yml"
    if os.path.exists(docker_compose_path):
        with open(docker_compose_path, "r") as file:
            docker_compose = yaml.safe_load(file)
    else:
        docker_compose = {"services": {}, "networks": {"freqnet": {"driver": "bridge"}}, "volumes": {}}

    # Add new service and volume
    new_service = generate_docker_compose(selected_config, selected_strategy, port, volume_name)
    docker_compose["services"].update(new_service)
    docker_compose["volumes"].update({volume_name: {}})

    # Write updated docker-compose.yml
    with open(docker_compose_path, "w") as file:
        yaml.dump(docker_compose, file, default_flow_style=False)

    print(f"Docker-compose updated with service for {selected_config} and {selected_strategy}.")

if __name__ == "__main__":
    main()
