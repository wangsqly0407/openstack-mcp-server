import json
import anyio
from typing import Optional
import mcp.types as types

async def get_networks(filter_value: str = "", limit: int = 100, detail_level: str = "detailed", **kwargs) -> list[dict]:
    """Get OpenStack Neutron networks with filtering and detail level options.
    
    Args:
        filter_value: Optional filter for network name or ID
        limit: Maximum number of networks to return
        detail_level: Level of detail to return (basic, detailed, full)
        **kwargs: Additional keyword arguments for OpenStack connection
        
    Returns:
        List of network dictionaries with information based on detail_level
        
    Raises:
        Exception: If OpenStack connection or query fails
    """
    from openstack import connection
    
    # 使用anyio在线程池中运行阻塞操作
    def get_networks():
        # 认证配置
        conn = connection.Connection(
            **kwargs
        )
        
        # 获取所有网络
        networks = list(conn.network.networks())
        
        # 应用过滤器
        if filter_value:
            networks = [n for n in networks if (
                (n.name and filter_value.lower() in n.name.lower()) or 
                filter_value in n.id
            )]
        
        # 应用限制
        networks = networks[:limit]
        
        # 根据详细程度准备结果
        results = []
        for network in networks:
            # 将网络对象转换为字典以便更可靠地访问属性
            network_dict = network.to_dict()
            
            if detail_level == "basic":
                network_info = {
                    "id": network_dict.get("id", "未知"),
                    "name": network_dict.get("name", "未知"),
                    "status": network_dict.get("status", "未知"),
                    "is_shared": network_dict.get("shared", False),
                    "is_external": network_dict.get("router:external", False)
                }
            elif detail_level == "detailed":
                network_info = {
                    "id": network_dict.get("id", "未知"),
                    "name": network_dict.get("name", "未知"),
                    "status": network_dict.get("status", "未知"),
                    "is_shared": network_dict.get("shared", False),
                    "is_external": network_dict.get("router:external", False),
                    "mtu": network_dict.get("mtu", None),
                    "subnets": network_dict.get("subnets", []),
                    "availability_zones": network_dict.get("availability_zones", []),
                    "created_at": network_dict.get("created_at", "未知"),
                    "project_id": network_dict.get("project_id", "未知")
                }
            else:  # full
                # 使用完整的网络字典
                network_info = network_dict.copy()  # 创建副本以避免修改原始数据
                # 确保is_external字段存在，便于统一处理
                if "router:external" in network_info:
                    network_info["is_external"] = network_info["router:external"]
                # 过滤掉None值
                network_info = {k: v for k, v in network_info.items() if v is not None}
            
            results.append(network_info)
        
        return results
    
    # 在线程池中执行阻塞操作
    return await anyio.to_thread.run_sync(get_networks)


def format_networks_summary(networks: list[dict], detail_level: str = "detailed") -> str:
    """格式化OpenStack网络信息为人类可读的摘要。
    
    Args:
        networks: OpenStack网络信息列表
        detail_level: 详细程度 (basic, detailed, full)
        
    Returns:
        格式化后的文本摘要
    """
    if not networks:
        return "未找到符合条件的OpenStack网络。"
    
    # 基本摘要信息
    summary = f"找到 {len(networks)} 个OpenStack网络:\n\n"
    for idx, network in enumerate(networks, 1):
        summary += f"{idx}. ID: {network['id']}\n"
        summary += f"   名称: {network['name'] or '未命名'}\n"
        summary += f"   状态: {network['status']}\n"
        summary += f"   共享: {'是' if network.get('is_shared') else '否'}\n"
        
        # 处理外部网络标志，可能是is_external或router:external
        is_external = network.get('is_external', network.get('router:external', False))
        summary += f"   外部网络: {'是' if is_external else '否'}\n"
        
        # 根据详细程度添加额外信息
        if detail_level != "basic":
            if "created_at" in network:
                summary += f"   创建时间: {network['created_at']}\n"
            if "mtu" in network and network["mtu"]:
                summary += f"   MTU: {network['mtu']}\n"
            if "subnets" in network and network["subnets"]:
                summary += f"   子网: {', '.join(network['subnets'])}\n"
            if "availability_zones" in network and network["availability_zones"]:
                summary += f"   可用区: {', '.join(network['availability_zones'])}\n"
            if "project_id" in network:
                summary += f"   项目ID: {network['project_id']}\n"
        
        summary += "\n"
    
    return summary


async def process_network_query(
    ctx, 
    filter_value: str = "", 
    limit: int = 100, 
    detail_level: str = "detailed",
    get_networks_func = None
) -> Optional[list[types.TextContent]]:
    """处理OpenStack网络查询的完整流程。
    
    Args:
        ctx: MCP请求上下文
        filter_value: 网络筛选条件
        limit: 返回结果数量限制
        detail_level: 详细程度
        get_networks_func: 获取网络的函数
        
    Returns:
        返回格式化的结果或None（如果出现错误）
        
    Raises:
        ValueError: 如果查询过程中出现错误
    """
    await ctx.session.send_log_message(
        level="info",
        data=f"正在获取OpenStack网络信息...",
        logger="openstack",
        related_request_id=ctx.request_id,
    )
    
    try:
        # 异步运行OpenStack查询
        if get_networks_func:
            networks = await get_networks_func(filter_value, limit, detail_level)
        else:
            networks = await get_networks(filter_value, limit, detail_level)
        
        # 发送成功消息
        await ctx.session.send_log_message(
            level="info",
            data=f"成功获取到 {len(networks)} 个OpenStack网络",
            logger="openstack",
            related_request_id=ctx.request_id,
        )
        
        # 使用格式化函数生成摘要
        summary = format_networks_summary(networks, detail_level)
        
        return [
            types.TextContent(type="text", text=summary),
        ]
        
    except Exception as err:
        # 发送错误信息
        error_message = f"获取OpenStack网络信息失败: {str(err)}"
        await ctx.session.send_log_message(
            level="error",
            data=error_message,
            logger="openstack",
            related_request_id=ctx.request_id,
        )
        raise ValueError(error_message) 