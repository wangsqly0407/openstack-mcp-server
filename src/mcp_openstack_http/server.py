import contextlib
import logging
import os
from collections.abc import AsyncIterator

import click
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

# 导入分拆后的模块
from mcp_openstack_http.os_server import get_instances, process_instance_query
from mcp_openstack_http.os_volume import get_volumes, process_volume_query
from mcp_openstack_http.os_network import get_networks, process_network_query
from mcp_openstack_http.os_image import get_images, process_image_query
from mcp_openstack_http.os_compute_service import get_compute_services, process_compute_service_query
from mcp_openstack_http.os_network_agent import get_network_agents, process_network_agent_query
from mcp_openstack_http.os_volume_service import get_volume_services, process_volume_service_query
from mcp_openstack_http.os_service import get_services, process_service_query

# ---------------------------------------------------------------------------
# MCP Server 主程序
# ---------------------------------------------------------------------------

@click.command()
@click.option("--port", default=8000, help="Port to listen on for HTTP")
@click.option(
    "--log-level",
    default="INFO",
    help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
)
@click.option(
    "--json-response",
    is_flag=True,
    default=False,
    help="Enable JSON responses instead of SSE streams",
)
@click.option(
    "--auth-url",
    default="http://127.0.0.1:5000/v3",
    required=True,
    help="OpenStack认证URL",
)
@click.option(
    "--username",
    default="admin",
    required=True,
    help="OpenStack用户名",
)
@click.option(
    "--password",
    default="admin",
    required=True,
    help="OpenStack密码",
)
@click.option(
    "--project-name",
    default="admin",
    help="OpenStack项目名称",
)
@click.option(
    "--user-domain-name",
    default="Default",
    help="OpenStack用户域名",
)
@click.option(
    "--project-domain-name",
    default="Default",
    help="OpenStack项目域名",
)
def main(
    port: int, 
    log_level: str, 
    json_response: bool,
    auth_url: str,
    username: str,
    password: str,
    project_name: str,
    user_domain_name: str,
    project_domain_name: str
) -> int:
    """Run an MCP OpenStack server using Streamable HTTP transport."""

    # ---------------------- Configure logging ----------------------
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("openstack-server")

    # ---------------------- Create MCP Server ----------------------
    app = Server("mcp-streamable-http-openstack")

    # OpenStack认证配置
    openstack_config = {
        "auth_url": auth_url,
        "username": username,
        "password": password,
        "project_name": project_name,
        "user_domain_name": user_domain_name,
        "project_domain_name": project_domain_name
    }
    
    # 更新get_instances函数以使用配置
    async def get_instances_with_config(filter_value: str = "", limit: int = 100, detail_level: str = "detailed") -> list[dict]:
        """使用命令行配置获取OpenStack实例。"""
        return await get_instances(
            filter_value=filter_value,
            limit=limit,
            detail_level=detail_level,
            **openstack_config
        )
        
    # 更新get_volumes函数以使用配置
    async def get_volumes_with_config(filter_value: str = "", limit: int = 100, detail_level: str = "detailed") -> list[dict]:
        """使用命令行配置获取OpenStack卷。"""
        return await get_volumes(
            filter_value=filter_value,
            limit=limit,
            detail_level=detail_level,
            **openstack_config
        )
        
    # 更新get_networks函数以使用配置
    async def get_networks_with_config(filter_value: str = "", limit: int = 100, detail_level: str = "detailed") -> list[dict]:
        """使用命令行配置获取OpenStack网络。"""
        return await get_networks(
            filter_value=filter_value,
            limit=limit,
            detail_level=detail_level,
            **openstack_config
        )
        
    # 更新get_images函数以使用配置
    async def get_images_with_config(filter_value: str = "", limit: int = 100, detail_level: str = "detailed") -> list[dict]:
        """使用命令行配置获取OpenStack镜像。"""
        return await get_images(
            filter_value=filter_value,
            limit=limit,
            detail_level=detail_level,
            **openstack_config
        )

    # 更新get_compute_services函数以使用配置
    async def get_compute_services_with_config(filter_value: str = "", limit: int = 100, detail_level: str = "detailed") -> list[dict]:
        """使用命令行配置获取OpenStack计算服务。"""
        return await get_compute_services(
            filter_value=filter_value,
            limit=limit,
            detail_level=detail_level,
            **openstack_config
        )
        
    # 更新get_network_agents函数以使用配置
    async def get_network_agents_with_config(filter_value: str = "", limit: int = 100, detail_level: str = "detailed") -> list[dict]:
        """使用命令行配置获取OpenStack网络代理。"""
        return await get_network_agents(
            filter_value=filter_value,
            limit=limit,
            detail_level=detail_level,
            **openstack_config
        )
        
    # 更新get_volume_services函数以使用配置
    async def get_volume_services_with_config(filter_value: str = "", limit: int = 100, detail_level: str = "detailed") -> list[dict]:
        """使用命令行配置获取OpenStack卷服务。"""
        return await get_volume_services(
            filter_value=filter_value,
            limit=limit,
            detail_level=detail_level,
            **openstack_config
        )
        
    # 更新get_services函数以使用配置
    async def get_services_with_config(filter_value: str = "", limit: int = 100, detail_level: str = "detailed") -> list[dict]:
        """使用命令行配置获取OpenStack服务。"""
        return await get_services(
            filter_value=filter_value,
            limit=limit,
            detail_level=detail_level,
            **openstack_config
        )

    # ---------------------- Tool implementation -------------------
    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        """Handle the tool calls."""
        ctx = app.request_context
        
        # 处理OpenStack实例查询工具
        if name == "get_instances":
            filter_value = arguments.get("filter", "")
            limit = arguments.get("limit", 100)  # 默认最多返回100个实例
            detail_level = arguments.get("detail_level", "detailed")
            
            return await process_instance_query(
                ctx, 
                filter_value, 
                limit, 
                detail_level, 
                get_instances_func=get_instances_with_config
            )
        
        # 处理OpenStack卷查询工具
        elif name == "get_volumes":
            filter_value = arguments.get("filter", "")
            limit = arguments.get("limit", 100)  # 默认最多返回100个卷
            detail_level = arguments.get("detail_level", "detailed")
            
            return await process_volume_query(
                ctx, 
                filter_value, 
                limit, 
                detail_level, 
                get_volumes_func=get_volumes_with_config
            )
        
        # 处理OpenStack网络查询工具
        elif name == "get_networks":
            filter_value = arguments.get("filter", "")
            limit = arguments.get("limit", 100)  # 默认最多返回100个网络
            detail_level = arguments.get("detail_level", "detailed")
            
            return await process_network_query(
                ctx, 
                filter_value, 
                limit, 
                detail_level, 
                get_networks_func=get_networks_with_config
            )
        
        # 处理OpenStack镜像查询工具
        elif name == "get_images":
            filter_value = arguments.get("filter", "")
            limit = arguments.get("limit", 100)  # 默认最多返回100个镜像
            detail_level = arguments.get("detail_level", "detailed")
            
            return await process_image_query(
                ctx, 
                filter_value, 
                limit, 
                detail_level, 
                get_images_func=get_images_with_config
            )
        
        # 处理OpenStack计算服务查询工具
        elif name == "get_compute_services":
            filter_value = arguments.get("filter", "")
            limit = arguments.get("limit", 100)
            detail_level = arguments.get("detail_level", "detailed")
            
            return await process_compute_service_query(
                ctx, 
                filter_value, 
                limit, 
                detail_level, 
                get_compute_services_func=get_compute_services_with_config
            )
        
        # 处理OpenStack网络代理查询工具
        elif name == "get_network_agents":
            filter_value = arguments.get("filter", "")
            limit = arguments.get("limit", 100)
            detail_level = arguments.get("detail_level", "detailed")
            
            return await process_network_agent_query(
                ctx, 
                filter_value, 
                limit, 
                detail_level, 
                get_network_agents_func=get_network_agents_with_config
            )
        
        # 处理OpenStack卷服务查询工具
        elif name == "get_volume_services":
            filter_value = arguments.get("filter", "")
            limit = arguments.get("limit", 100)
            detail_level = arguments.get("detail_level", "detailed")
            
            return await process_volume_service_query(
                ctx, 
                filter_value, 
                limit, 
                detail_level, 
                get_volume_services_func=get_volume_services_with_config
            )
        
        # 处理OpenStack服务查询工具
        elif name == "get_services":
            filter_value = arguments.get("filter", "")
            limit = arguments.get("limit", 100)
            detail_level = arguments.get("detail_level", "detailed")
            
            return await process_service_query(
                ctx, 
                filter_value, 
                limit, 
                detail_level, 
                get_services_func=get_services_with_config
            )
        
        else:
            raise ValueError(f"Unknown tool: {name}")

    # ---------------------- Tool registry -------------------------
    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        """Expose available tools to the LLM."""
        return [
            types.Tool(
                name="get_instances",
                description="获取OpenStack虚拟机实例的详细信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "筛选条件，如实例名称或ID",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回结果的最大数量",
                        },
                        "detail_level": {
                            "type": "string",
                            "enum": ["basic", "detailed", "full"],
                            "description": "返回信息的详细程度",
                            "default": "detailed"
                        }
                    },
                },
            ),
            types.Tool(
                name="get_volumes",
                description="获取OpenStack存储卷(Cinder)的详细信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "筛选条件，如卷名称或ID",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回结果的最大数量",
                        },
                        "detail_level": {
                            "type": "string",
                            "enum": ["basic", "detailed", "full"],
                            "description": "返回信息的详细程度",
                            "default": "detailed"
                        }
                    },
                },
            ),
            types.Tool(
                name="get_networks",
                description="获取OpenStack网络的详细信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "筛选条件，如网络名称或ID",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回结果的最大数量",
                        },
                        "detail_level": {
                            "type": "string",
                            "enum": ["basic", "detailed", "full"],
                            "description": "返回信息的详细程度",
                            "default": "detailed"
                        }
                    },
                },
            ),
            types.Tool(
                name="get_images",
                description="获取OpenStack镜像的详细信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "筛选条件，如镜像名称或ID",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回结果的最大数量",
                        },
                        "detail_level": {
                            "type": "string",
                            "enum": ["basic", "detailed", "full"],
                            "description": "返回信息的详细程度",
                            "default": "detailed"
                        }
                    },
                },
            ),
            types.Tool(
                name="get_compute_services",
                description="获取OpenStack计算服务的详细信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "筛选条件，如服务名称或主机",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回结果的最大数量",
                        },
                        "detail_level": {
                            "type": "string",
                            "enum": ["basic", "detailed", "full"],
                            "description": "返回信息的详细程度",
                            "default": "detailed"
                        }
                    },
                },
            ),
            types.Tool(
                name="get_network_agents",
                description="获取OpenStack网络代理的详细信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "筛选条件，如代理类型或主机",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回结果的最大数量",
                        },
                        "detail_level": {
                            "type": "string",
                            "enum": ["basic", "detailed", "full"],
                            "description": "返回信息的详细程度",
                            "default": "detailed"
                        }
                    },
                },
            ),
            types.Tool(
                name="get_volume_services",
                description="获取OpenStack卷服务的详细信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "筛选条件，如服务名称或主机",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回结果的最大数量",
                        },
                        "detail_level": {
                            "type": "string",
                            "enum": ["basic", "detailed", "full"],
                            "description": "返回信息的详细程度",
                            "default": "detailed"
                        }
                    },
                },
            ),
            types.Tool(
                name="get_services",
                description="获取OpenStack服务的详细信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "筛选条件，如服务名称或类型",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回结果的最大数量",
                        },
                        "detail_level": {
                            "type": "string",
                            "enum": ["basic", "detailed", "full"],
                            "description": "返回信息的详细程度",
                            "default": "detailed"
                        }
                    },
                },
            )
        ]

    # ---------------------- Session manager -----------------------
    session_manager = StreamableHTTPSessionManager(
        app=app,
        event_store=None,  # 无状态；不保存历史事件
        json_response=json_response,
        stateless=True,
    )

    async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:  # noqa: D401,E501
        await session_manager.handle_request(scope, receive, send)

    # ---------------------- Lifespan Management --------------------
    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with session_manager.run():
            logger.info("OpenStack MCP server started! 🚀")
            try:
                yield
            finally:
                logger.info("OpenStack MCP server shutting down…")

    # ---------------------- ASGI app + Uvicorn ---------------------
    starlette_app = Starlette(
        debug=False,
        routes=[Mount("/openstack", app=handle_streamable_http)],
        lifespan=lifespan,
    )

    import uvicorn

    uvicorn.run(starlette_app, host="0.0.0.0", port=port)

    return 0


if __name__ == "__main__":
    main()
