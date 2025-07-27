# Project Setup

This document provides instructions to set up the environment for the custom Freqtrade project.

## Prerequisites

1. **Python**: Ensure Python 3.8 or higher is installed.
2. **Docker**: Install Docker and Docker Compose.
3. **NVIDIA Drivers**: Ensure NVIDIA drivers are installed for GPU support.

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

4. **Run the Script**:
   Use the `generate_docker_compose.py` script to dynamically create Docker Compose services:
   ```bash
   python generate_docker_compose.py
   ```

5. **Start Docker Services**:
   Run the following command to start the services:
   ```bash
   docker-compose up -d
   ```

## Notes

- Ensure the `user_data` folder contains valid configuration files (`.json`) and strategy scripts (`.py`).
- The script will prompt you to select a configuration and strategy, and it will automatically generate the necessary Docker Compose entries.

## Troubleshooting

- If you encounter issues with missing Python packages, ensure you have installed all dependencies from `requirements.txt`.
- For Docker-related issues, verify that Docker is running and properly configured on your system.
