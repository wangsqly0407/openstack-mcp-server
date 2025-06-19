import json
import anyio
from typing import Optional
import mcp.types as types

async def get_network_agents(filter_value: str = "", limit: int = 100, detail_level: str = "detailed", **kwargs) -> list[dict]:
    """获取OpenStack网络代理列表，支持过滤和详细程度选项。
    
    Args:
        filter_value: 可选的代理类型或主机过滤器
        limit: 返回结果的最大数量
        detail_level: 返回详细程度 (basic, detailed, full)
        **kwargs: OpenStack连接的额外关键字参数
        
    Returns:
        基于detail_level的网络代理信息字典列表
        
    Raises:
        Exception: 如果OpenStack连接或查询失败
    """
    from openstack import connection
    
    # 使用anyio在线程池中运行阻塞操作
    def get_agents():
        # 认证配置
        conn = connection.Connection(
            **kwargs
        )
        
        # 获取所有网络代理
        agents = list(conn.network.agents())
        
        # 应用过滤器
        if filter_value:
            agents = [a for a in agents if (
                (hasattr(a, 'agent_type') and filter_value.lower() in a.agent_type.lower()) or 
                (hasattr(a, 'host') and filter_value.lower() in a.host.lower()) or
                (hasattr(a, 'id') and filter_value in a.id)
            )]
        
        # 应用限制
        agents = agents[:limit]
        
        # 根据详细程度准备结果
        results = []
        for agent in agents:
            if detail_level == "basic":
                agent_info = {
                    "id": agent.id,
                    "agent_type": getattr(agent, "agent_type", "未知"),
                    "host": getattr(agent, "host", "未知"),
                    "alive": getattr(agent, "is_alive", False)
                }
            elif detail_level == "detailed":
                agent_info = {
                    "id": agent.id,
                    "agent_type": getattr(agent, "agent_type", "未知"),
                    "host": getattr(agent, "host", "未知"),
                    "alive": getattr(agent, "is_alive", False),
                    "admin_state_up": getattr(agent, "is_admin_state_up", False),
                    "binary": getattr(agent, "binary", "未知"),
                    "created_at": getattr(agent, "created_at", "未知"),
                    "heartbeat_timestamp": getattr(agent, "heartbeat_timestamp", "未知"),
                    "availability_zone": getattr(agent, "availability_zone", "未知")
                }
            else:  # full
                # 将代理对象转换为字典
                agent_info = {k: v for k, v in agent.to_dict().items() if v is not None}
            
            results.append(agent_info)
        
        return results
    
    # 在线程池中执行阻塞操作
    return await anyio.to_thread.run_sync(get_agents)


def format_network_agents_summary(agents: list[dict], detail_level: str = "detailed") -> str:
    """格式化OpenStack网络代理信息为人类可读的摘要。
    
    Args:
        agents: OpenStack网络代理信息列表
        detail_level: 详细程度 (basic, detailed, full)
        
    Returns:
        格式化后的文本摘要
    """
    if not agents:
        return "未找到符合条件的OpenStack网络代理。"
    
    # 基本摘要信息
    summary = f"找到 {len(agents)} 个OpenStack网络代理:\n\n"
    for idx, agent in enumerate(agents, 1):
        summary += f"{idx}. ID: {agent['id']}\n"
        summary += f"   类型: {agent['agent_type']}\n"
        summary += f"   主机: {agent['host']}\n"
        summary += f"   存活状态: {'活跃' if agent['alive'] else '不活跃'}\n"
        
        # 根据详细程度添加额外信息
        if detail_level != "basic":
            if "admin_state_up" in agent:
                summary += f"   管理状态: {'启用' if agent['admin_state_up'] else '禁用'}\n"
            if "binary" in agent:
                summary += f"   二进制: {agent['binary']}\n"
            if "heartbeat_timestamp" in agent:
                summary += f"   心跳时间戳: {agent['heartbeat_timestamp']}\n"
            if "availability_zone" in agent and agent["availability_zone"]:
                summary += f"   可用区: {agent['availability_zone']}\n"
        
        summary += "\n"
    
    return summary


async def process_network_agent_query(
    ctx, 
    filter_value: str = "", 
    limit: int = 100, 
    detail_level: str = "detailed",
    get_network_agents_func = None
) -> Optional[list[types.TextContent]]:
    """处理OpenStack网络代理查询的完整流程。
    
    Args:
        ctx: MCP请求上下文
        filter_value: 代理筛选条件
        limit: 返回结果数量限制
        detail_level: 详细程度
        get_network_agents_func: 获取网络代理的函数
        
    Returns:
        返回格式化的结果或None（如果出现错误）
        
    Raises:
        ValueError: 如果查询过程中出现错误
    """
    await ctx.session.send_log_message(
        level="info",
        data=f"正在获取OpenStack网络代理信息...",
        logger="openstack",
        related_request_id=ctx.request_id,
    )
    
    try:
        # 异步运行OpenStack查询
        if get_network_agents_func:
            agents = await get_network_agents_func(filter_value, limit, detail_level)
        else:
            agents = await get_network_agents(filter_value, limit, detail_level)
        
        # 发送成功消息
        await ctx.session.send_log_message(
            level="info",
            data=f"成功获取到 {len(agents)} 个OpenStack网络代理",
            logger="openstack",
            related_request_id=ctx.request_id,
        )
        
        # 使用格式化函数生成摘要
        summary = format_network_agents_summary(agents, detail_level)
        
        return [
            types.TextContent(type="text", text=summary),
        ]
        
    except Exception as err:
        # 发送错误信息
        error_message = f"获取OpenStack网络代理信息失败: {str(err)}"
        await ctx.session.send_log_message(
            level="error",
            data=error_message,
            logger="openstack",
            related_request_id=ctx.request_id,
        )
        raise ValueError(error_message) 