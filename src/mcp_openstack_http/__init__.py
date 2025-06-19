"""OpenStack MCP Server - 基于MCP协议的OpenStack资源查询服务。"""

from .server import main
from .os_server import get_instances, format_instances_summary, process_instance_query
from .os_volume import get_volumes, format_volumes_summary, process_volume_query
from .os_network import get_networks, format_networks_summary, process_network_query
from .os_image import get_images, format_images_summary, process_image_query
from .os_compute_service import get_compute_services, format_compute_services_summary, process_compute_service_query
from .os_network_agent import get_network_agents, format_network_agents_summary, process_network_agent_query
from .os_volume_service import get_volume_services, format_volume_services_summary, process_volume_service_query
from .os_service import get_services, format_services_summary, process_service_query

__all__ = [
    'main',
    'get_instances', 'format_instances_summary', 'process_instance_query',
    'get_volumes', 'format_volumes_summary', 'process_volume_query',
    'get_networks', 'format_networks_summary', 'process_network_query',
    'get_images', 'format_images_summary', 'process_image_query',
    'get_compute_services', 'format_compute_services_summary', 'process_compute_service_query',
    'get_network_agents', 'format_network_agents_summary', 'process_network_agent_query',
    'get_volume_services', 'format_volume_services_summary', 'process_volume_service_query',
    'get_services', 'format_services_summary', 'process_service_query',
]
