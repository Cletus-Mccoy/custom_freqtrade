# FreqTrade Web Management Interface

A comprehensive web-based management interface for FreqTrade Docker containers with full docker-compose integration.

## ✨ Features

### 🚀 Container Management
- **Intuitive Creation Wizard**: Step-by-step container creation with validation
- **Template & Custom Configs**: Choose from existing templates or build custom configurations
- **Auto-start Capability**: Automatically start containers after creation
- **Port Conflict Detection**: Smart port assignment with conflict prevention
- **Strategy & Pairlist Integration**: Browse and select from available resources

### � Docker Services Management
- **Full Docker Compose Integration**: Complete docker-compose.yml management
- **Dual Editor Modes**: Switch between visual and YAML editing
- **Service Control**: Start, stop, restart individual or all services
- **Real-time Monitoring**: Live service status updates
- **Backup & Validation**: Automatic backups and YAML validation

### 🌐 Network Management
- **Modal-based Interface**: Clean popup interface for network management
- **Smart Validation**: Prevents deletion of networks in use
- **Docker Integration**: Seamless integration with Docker Compose networks

### � Configuration Management
- **Strategy Browser**: Visual strategy selection and validation
- **Categorized Pairlists**: Organized pairlists (Test, FreqAI, Full)
- **FreqAI Support**: Complete FreqAI configuration with multiple AI models
- **API Auto-configuration**: Automatic API setup for container management

## 🛠️ Recent Improvements

### Fixed Issues ✅
1. **Container Creation**: Complete rewrite with proper validation and error handling
2. **Docker Connection**: Improved Docker client initialization with multiple connection methods
3. **Services Management**: Enhanced docker-compose file loading and saving with YAML validation
4. **Network Management**: Moved from sidebar to clean modal popup interface
5. **Error Handling**: Comprehensive error handling and user feedback
6. **Configuration Validation**: Input validation for all configuration parameters

### Enhanced Features 🔥
1. **Better UX**: Responsive design with mobile-friendly interface
2. **Real-time Updates**: Live status monitoring and automatic refreshes
3. **API Improvements**: RESTful API with standardized responses
4. **Logging**: Structured logging for better debugging
5. **Backup System**: Automatic backups of docker-compose.yml before changes
- View and organize trading strategies
- Strategy categorization (FreqAI, Custom, Examples, Test)
- Code viewing with syntax highlighting
- Strategy testing and validation
- Upload new strategies

### 📝 Pairlist Management
- Manage trading pair lists
- Categorized pairlists (Test, FreqAI, Full)
- Visual pair distribution charts
- Import/export functionality
- Clone and modify existing pairlists

### ⚙️ Configuration Management
- Edit FreqTrade configurations
- Configuration validation
- Template-based config creation
- Backup and restore configs
- JSON syntax validation

### 🚀 Container Creation Wizard
- Step-by-step container creation
- Strategy and pairlist selection
- Configuration templates
- Real-time preview
- Docker integration

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- Docker (for container management features)
- FreqTrade setup with Docker Compose

### Quick Start (Windows)

#### Option 1: Using Batch File
```batch
# Simply double-click or run:
start_web_interface.bat
```

#### Option 2: Using PowerShell
```powershell
# Run the PowerShell script:
.\start_web_interface.ps1

# Or with custom settings:
.\start_web_interface.ps1 -ListenHost "0.0.0.0" -Port 8080 -Debug
```

### Manual Installation

1. **Navigate to the web interface directory:**
   ```bash
   cd web_interface
   ```

2. **Create virtual environment (recommended):**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the web interface:**
   ```bash
   python run.py
   ```

## 🔧 Configuration

### Command Line Options
```bash
python run.py --help

Options:
  --host HOST          Host to bind to (default: 0.0.0.0)
  --port PORT          Port to bind to (default: 5000)
  --debug              Run in debug mode
  --install-deps       Install dependencies and exit
```

### Environment Variables
- `FREQTRADE_USER_DATA_DIR`: Override user data directory path
- `DOCKER_HOST`: Docker daemon connection string
- `WEB_INTERFACE_SECRET_KEY`: Custom secret key for sessions

### Docker Integration
The web interface automatically detects and connects to your Docker environment. Make sure Docker is running and accessible.

## 📱 Usage

### Accessing the Interface
Once started, open your web browser and navigate to:
- Local access: `http://localhost:5000`
- Network access: `http://your-server-ip:5000`

### Main Navigation
- **Dashboard**: Overview of all containers and quick actions
- **Containers**: Detailed container management
- **Strategies**: Trading strategy management
- **Pairlists**: Trading pair list management
- **Configs**: Configuration file management

### Creating a New Container

1. Click "Create Container" from any page
2. Select your strategy from the dropdown
3. Choose a pairlist category (Test, FreqAI, or Full)
4. Select specific pairlist
5. Choose a configuration template
6. Customize advanced settings if needed
7. Click "Create Container"

The system will:
- Generate a new configuration file
- Provide Docker Compose service configuration
- Show deployment instructions

### Managing Existing Containers

#### Individual Container Actions:
- **Start/Stop/Restart**: Control container lifecycle
- **View Logs**: Real-time log streaming with auto-refresh
- **Inspect**: Detailed container information
- **Remove**: Delete container (with confirmation)

#### Bulk Operations:
- Select multiple containers using checkboxes
- Apply start/stop/restart to all selected
- Export container list to CSV

### Strategy Management

#### Viewing Strategies:
- Browse by category (FreqAI, Custom, Examples, Test)
- View strategy code with syntax highlighting
- Download strategy files

#### Testing Strategies:
- Select test pairlist and timeframe
- Configure test parameters
- Run backtesting simulation
- View results and performance metrics

### Pairlist Management

#### Categories:
- **Test**: Small pairlist for testing (10-20 pairs)
- **FreqAI**: Optimized for FreqAI strategies (20-50 pairs)
- **Full**: Complete market coverage (100+ pairs)

#### Features:
- Visual pair distribution charts
- Edit pairlists directly in the interface
- Clone and modify existing pairlists
- Import/export JSON files

### Configuration Management

#### Validation Features:
- JSON syntax validation
- FreqTrade configuration validation
- Required field checking
- Warning detection for common issues

#### Templates:
- Start from existing configurations
- Pre-configured for different trading modes
- Automatic pairlist integration

## 🔐 Security

### Access Control
- Basic session management
- CSRF protection
- Input sanitization

### Production Deployment
For production use:

1. **Use a reverse proxy** (nginx, Apache)
2. **Enable HTTPS**
3. **Set strong secret key**
4. **Limit network access**
5. **Regular backups**

Example nginx configuration:
```nginx
server {
    listen 80;
    server_name freqtrade.yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🐛 Troubleshooting

### Common Issues

#### "Docker not available"
- Ensure Docker is installed and running
- Check Docker daemon permissions
- Verify Docker socket accessibility

#### "Permission denied" errors
- Run with appropriate permissions
- Check file ownership in user_data directory
- Ensure Docker group membership (Linux)

#### Port already in use
- Change port with `--port` option
- Check for other running services
- Use `netstat -an | grep :5000` to check port usage

#### Module import errors
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`
- Check Python version (3.8+ required)

### Debug Mode
Enable debug mode for detailed error information:
```bash
python run.py --debug
```

## 🤝 Integration

### FreqTrade Configuration
The web interface works with your existing FreqTrade setup. Ensure your `user_data` directory structure matches:

```
user_data/
├── pairlists/
├── strategies/
├── config*.json
└── ...
```

### Docker Compose Integration
Add containers created through the web interface to your `docker-compose.yml`:

```yaml
services:
  your_new_container:
    image: freqtradeorg/freqtrade:stable
    container_name: your_new_container
    restart: unless-stopped
    volumes:
      - ./user_data:/freqtrade/user_data
    command:
      - trade
      - --config
      - /freqtrade/user_data/config_your_new_container.json
```

## 🔄 Updates

### Updating the Web Interface
1. Pull latest changes from repository
2. Update dependencies: `pip install -r requirements.txt`
3. Restart the web interface

### Backup Important Data
Before updates, backup:
- Configuration files
- Custom strategies
- Pairlists
- Container configurations

## 📝 Changelog

### Version 1.0.0
- Initial release
- Container management
- Strategy browser
- Pairlist management
- Configuration editor
- Container creation wizard

## 🆘 Support

### Getting Help
1. Check this README
2. Review error logs in debug mode
3. Check FreqTrade documentation
4. Open GitHub issue with details

### Contributing
Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Add tests if applicable
4. Submit pull request

## 📄 License

This project is part of the FreqTrade ecosystem and follows the same licensing terms.

---

**Happy Trading! 🚀**
