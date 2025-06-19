import json
import anyio
from typing import Optional
import mcp.types as types

async def get_instances(filter_value: str = "", limit: int = 100, detail_level: str = "detailed", **kwargs) -> list[dict]:
    """Get OpenStack instances with filtering and detail level options.
    
    Args:
        filter_value: Optional filter for instance name or ID
        limit: Maximum number of instances to return
        detail_level: Level of detail to return (basic, detailed, full)
        **kwargs: Additional keyword arguments for OpenStack connection
        
    Returns:
        List of instance dictionaries with information based on detail_level
        
    Raises:
        Exception: If OpenStack connection or query fails
    """
    from openstack import connection
    
    # 使用anyio在线程池中运行阻塞操作
    def get_instances():
        # 认证配置
        conn = connection.Connection(
            **kwargs
        )
        
        # 获取所有虚拟机实例
        servers = list(conn.compute.servers())
        
        # 应用过滤器
        if filter_value:
            servers = [s for s in servers if filter_value.lower() in s.name.lower() or filter_value in s.id]
        
        # 应用限制
        servers = servers[:limit]
        
        # 根据详细程度准备结果
        results = []
        for server in servers:
            if detail_level == "basic":
                instance_info = {
                    "id": server.id,
                    "name": server.name,
                    "status": server.status
                }
            elif detail_level == "detailed":
                instance_info = {
                    "id": server.id,
                    "name": server.name,
                    "status": server.status,
                    "flavor": getattr(server, "flavor", {}).get("id", "未知"),
                    "image": getattr(server, "image", {}).get("id", "未知"),
                    "addresses": getattr(server, "addresses", {}),
                    "created_at": getattr(server, "created_at", "未知")
                }
            else:  # full
                # 将服务器对象转换为字典
                instance_info = {k: v for k, v in server.to_dict().items() if v is not None}
            
            results.append(instance_info)
        
        return results
    
    # 在线程池中执行阻塞操作
    return await anyio.to_thread.run_sync(get_instances)


def format_instances_summary(instances: list[dict], detail_level: str = "detailed") -> str:
    """格式化OpenStack实例信息为人类可读的摘要。
    
    Args:
        instances: OpenStack实例信息列表
        detail_level: 详细程度 (basic, detailed, full)
        
    Returns:
        格式化后的文本摘要
    """
    if not instances:
        return "未找到符合条件的OpenStack实例。"
    
    # 基本摘要信息
    summary = f"找到 {len(instances)} 个OpenStack实例:\n\n"
    for idx, instance in enumerate(instances, 1):
        summary += f"{idx}. ID: {instance['id']}\n"
        summary += f"   名称: {instance['name']}\n"
        summary += f"   状态: {instance['status']}\n"
        
        # 根据详细程度添加额外信息
        if detail_level != "basic":
            if "created_at" in instance:
                summary += f"   创建时间: {instance['created_at']}\n"
            if "flavor" in instance and instance["flavor"] != "未知":
                summary += f"   规格: {instance['flavor']}\n"
            if "addresses" in instance:
                summary += f"   网络地址: {json.dumps(instance['addresses'], ensure_ascii=False)}\n"
        
        summary += "\n"
    
    return summary


async def process_instance_query(
    ctx, 
    filter_value: str = "", 
    limit: int = 100, 
    detail_level: str = "detailed",
    get_instances_func = None
) -> Optional[list[types.TextContent]]:
    """处理OpenStack实例查询的完整流程。
    
    Args:
        ctx: MCP请求上下文
        filter_value: 实例筛选条件
        limit: 返回结果数量限制
        detail_level: 详细程度
        get_instances_func: 获取实例的函数
        
    Returns:
        返回格式化的结果或None（如果出现错误）
        
    Raises:
        ValueError: 如果查询过程中出现错误
    """
    await ctx.session.send_log_message(
        level="info",
        data=f"正在获取OpenStack实例信息...",
        logger="openstack",
        related_request_id=ctx.request_id,
    )
    
    try:
        # 异步运行OpenStack查询
        if get_instances_func:
            instances = await get_instances_func(filter_value, limit, detail_level)
        else:
            instances = await get_instances(filter_value, limit, detail_level)
        
        # 发送成功消息
        await ctx.session.send_log_message(
            level="info",
            data=f"成功获取到 {len(instances)} 个OpenStack实例",
            logger="openstack",
            related_request_id=ctx.request_id,
        )
        
        # 使用格式化函数生成摘要
        summary = format_instances_summary(instances, detail_level)
        
        return [
            types.TextContent(type="text", text=summary),
        ]
        
    except Exception as err:
        # 发送错误信息
        error_message = f"获取OpenStack实例信息失败: {str(err)}"
        await ctx.session.send_log_message(
            level="error",
            data=error_message,
            logger="openstack",
            related_request_id=ctx.request_id,
        )
        raise ValueError(error_message) 