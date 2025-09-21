# Project Setup

This document provides instructions to set up the environment for the custom Freqtrade project.

## Prerequisites

1. **Python**: Ensure Python 3.8 or higher is installed.
2. **Docker**: Install Docker and Docker Compose.
3. **NVIDIA Drivers**: Ensure NVIDIA drivers are installed for GPU support (optional for FreqAI).

## Installation Steps

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd custom_freqtrade
   ```

2. **Set Up Python Environment**:
   Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Edit the `.env` file to customize the following variables:
   - `FREQTRADE_IMAGE`: Docker image to use (default: `freqtradeorg/freqtrade:stable_freqai`)
   - `GPU_DRIVER`: GPU driver to use (default: `nvidia`)
   - `BASE_PORT`: Base port for services (default: `8080`)

4. **Start the Web Interface**:
   Launch the improved web management interface:
   ```bash
   cd web_interface
   python app.py
   ```
   The web interface will be available at: http://localhost:5000

## Web Interface Features

### Container Management
- **Create Containers**: Easy wizard to create new FreqTrade containers
- **Template or Custom Configs**: Choose from existing templates or create custom configurations
- **Auto-start Option**: Automatically start containers after creation
- **Port Management**: Automatic port assignment with conflict detection

### Services Management
- **Docker Compose Integration**: Full docker-compose.yml management
- **Visual and YAML Editors**: Switch between visual and code editing modes
- **Service Control**: Start, stop, restart individual or all services
- **Real-time Status**: Live service status monitoring

### Network Management
- **Docker Networks**: Create and manage Docker networks via modal popup
- **Network Validation**: Automatic validation before network deletion
- **Service Integration**: Networks are automatically integrated with services

### Configuration Management
- **Strategy Selection**: Browse and select from available strategies
- **Pairlist Categories**: Organized pairlists (Test, FreqAI, Full)
- **FreqAI Support**: Built-in FreqAI configuration with multiple models
- **API Configuration**: Automatic API setup for container management

## Alternative: Command Line Setup

5. **Run the Script** (Alternative to Web Interface):
   Use the `generate_docker_compose.py` script to dynamically create Docker Compose services:
   ```bash
   python generate_docker_compose.py
   ```

6. **Start Docker Services**:
   Run the following command to start the services:
   ```bash
   docker-compose up -d
   ```

## Directory Structure

```
custom_freqtrade/
├── web_interface/          # Web management interface
│   ├── app.py             # Main Flask application
│   ├── templates/         # HTML templates
│   └── static/           # CSS, JS, and assets
├── user_data/            # FreqTrade configurations and data
│   ├── strategies/       # Trading strategies
│   ├── pairlists/       # Trading pair lists
│   └── models/          # FreqAI models
├── docker-compose.yml   # Docker services configuration
└── requirements.txt     # Python dependencies
```

## Usage Examples

### Creating a New Container via Web Interface
1. Navigate to http://localhost:5000
2. Click "Create New Container"
3. Choose container name, strategy, and pairlist
4. Select configuration mode (template or custom)
5. Configure additional settings (API port, FreqAI, etc.)
6. Click "Create Container" (optionally auto-start)

### Managing Services
1. Go to "Docker Services" in the web interface
2. View all services in list or card view
3. Start/stop/restart individual services
4. Edit docker-compose.yml directly or visually
5. Manage networks via the Networks button

### Container Creation via API
```bash
curl -X POST http://localhost:5000/api/create-container \
  -H "Content-Type: application/json" \
  -d '{
    "container_name": "my_bot",
    "strategy": "GodStra",
    "pairlist": "freqai_pairs.json",
    "config_mode": "template",
    "template_config": "config_freqai.LightGBM.json",
    "external_api_port": 8081,
    "start_container": true
  }'
```

## Troubleshooting

### Docker Issues
- **Connection Failed**: Ensure Docker Desktop is running
- **Permission Denied**: Check Docker permissions and try restarting Docker Desktop
- **Port Conflicts**: Use the web interface port conflict detection

### Web Interface Issues
- **Dependencies**: Install requirements with `pip install -r web_interface/requirements.txt`
- **Port 5000 in use**: Change the port in `app.py` (last line: `app.run(port=5001)`)

### Configuration Issues
- **Invalid Strategy**: Ensure the strategy file exists in `user_data/strategies/`
- **Invalid Pairlist**: Check that pairlist files exist in `user_data/pairlists/`
- **FreqAI Errors**: Ensure you're using the `freqtradeorg/freqtrade:stable_freqai` image

### Common Fixes
- **Missing Dependencies**: Run `pip install -r requirements.txt` in the project root
- **Docker Compose Format**: Use the "Fix Format" button in the web interface
- **Service Won't Start**: Check container logs via the web interface or `docker-compose logs <service_name>`

## Advanced Features

### Custom Configuration Templates
Create your own configuration templates by placing `.json` files in the `user_data/` directory. The web interface will automatically detect and offer them as templates.

### FreqAI Integration
The web interface supports full FreqAI configuration including:
- Model selection (LightGBM, CatBoost, XGBoost, PyTorch)
- Training period configuration
- Feature parameter customization
- Correlation pair management

### API Integration
All web interface features are available via REST API endpoints. See the application logs or use browser developer tools to understand the API structure.
