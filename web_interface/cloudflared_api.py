import yaml
from flask import jsonify
import docker

@app.route('/api/cloudflared/service', methods=['GET'])
def get_cloudflared_service():
    """Get status and config of the cloudflared service from its compose file and Docker."""
    compose_path = BASE_PATH / 'web_interface' / 'cloudflared-compose.yml'
    service_info = {
        'name': 'cloudflared',
        'status': 'not_created',
        'image': None,
        'ports': [],
        'container_id': None,
        'container_name': None
    }
    # Read compose config
    if compose_path.exists():
        try:
            with open(compose_path, 'r') as f:
                compose_data = yaml.safe_load(f)
            svc = compose_data.get('services', {}).get('cloudflared', {})
            service_info['image'] = svc.get('image')
            # cloudflared doesn't expose ports, but keep for future
            service_info['ports'] = svc.get('ports', [])
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error reading compose: {e}'})
    # Check Docker for running/stopped container
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)
        for c in containers:
            if 'cloudflared' in c.name:
                service_info['container_id'] = c.short_id
                service_info['container_name'] = c.name
                service_info['status'] = c.status
                break
        else:
            service_info['status'] = 'not_created'
    except Exception as e:
        service_info['status'] = 'docker_error'
        service_info['error'] = str(e)
    return jsonify({'success': True, 'service': service_info})
