import json
import anyio
from typing import Optional
import mcp.types as types

async def get_compute_services(filter_value: str = "", limit: int = 100, detail_level: str = "detailed", **kwargs) -> list[dict]:
    """获取OpenStack计算服务列表，支持过滤和详细程度选项。
    
    Args:
        filter_value: 可选的服务名称或ID过滤器
        limit: 返回结果的最大数量
        detail_level: 返回详细程度 (basic, detailed, full)
        **kwargs: OpenStack连接的额外关键字参数
        
    Returns:
        基于detail_level的计算服务信息字典列表
        
    Raises:
        Exception: 如果OpenStack连接或查询失败
    """
    from openstack import connection
    
    # 使用anyio在线程池中运行阻塞操作
    def get_services():
        # 认证配置
        conn = connection.Connection(
            **kwargs
        )
        
        # 获取所有计算服务
        services = list(conn.compute.services())
        
        # 应用过滤器
        if filter_value:
            services = [s for s in services if (
                (hasattr(s, 'binary') and filter_value.lower() in s.binary.lower()) or 
                (hasattr(s, 'host') and filter_value.lower() in s.host.lower()) or
                (hasattr(s, 'id') and filter_value in s.id)
            )]
        
        # 应用限制
        services = services[:limit]
        
        # 根据详细程度准备结果
        results = []
        for service in services:
            if detail_level == "basic":
                service_info = {
                    "id": getattr(service, "id", "未知"),
                    "binary": getattr(service, "binary", "未知"),
                    "host": getattr(service, "host", "未知"),
                    "state": getattr(service, "state", "未知")
                }
            elif detail_level == "detailed":
                service_info = {
                    "id": getattr(service, "id", "未知"),
                    "binary": getattr(service, "binary", "未知"),
                    "host": getattr(service, "host", "未知"),
                    "state": getattr(service, "state", "未知"),
                    "status": getattr(service, "status", "未知"),
                    "zone": getattr(service, "zone", "未知"),
                    "updated_at": getattr(service, "updated_at", "未知"),
                    "disabled_reason": getattr(service, "disabled_reason", None)
                }
            else:  # full
                # 将服务对象转换为字典
                service_info = {k: v for k, v in service.to_dict().items() if v is not None}
            
            results.append(service_info)
        
        return results
    
    # 在线程池中执行阻塞操作
    return await anyio.to_thread.run_sync(get_services)


def format_compute_services_summary(services: list[dict], detail_level: str = "detailed") -> str:
    """格式化OpenStack计算服务信息为人类可读的摘要。
    
    Args:
        services: OpenStack计算服务信息列表
        detail_level: 详细程度 (basic, detailed, full)
        
    Returns:
        格式化后的文本摘要
    """
    if not services:
        return "未找到符合条件的OpenStack计算服务。"
    
    # 基本摘要信息
    summary = f"找到 {len(services)} 个OpenStack计算服务:\n\n"
    for idx, service in enumerate(services, 1):
        summary += f"{idx}. 服务: {service['binary']}\n"
        summary += f"   主机: {service['host']}\n"
        summary += f"   状态: {service['state']}\n"
        
        # 根据详细程度添加额外信息
        if detail_level != "basic":
            if "status" in service:
                summary += f"   服务状态: {service['status']}\n"
            if "zone" in service:
                summary += f"   可用区: {service['zone']}\n"
            if "updated_at" in service:
                summary += f"   更新时间: {service['updated_at']}\n"
            if "disabled_reason" in service and service["disabled_reason"]:
                summary += f"   禁用原因: {service['disabled_reason']}\n"
        
        summary += "\n"
    
    return summary


async def process_compute_service_query(
    ctx, 
    filter_value: str = "", 
    limit: int = 100, 
    detail_level: str = "detailed",
    get_compute_services_func = None
) -> Optional[list[types.TextContent]]:
    """处理OpenStack计算服务查询的完整流程。
    
    Args:
        ctx: MCP请求上下文
        filter_value: 服务筛选条件
        limit: 返回结果数量限制
        detail_level: 详细程度
        get_compute_services_func: 获取计算服务的函数
        
    Returns:
        返回格式化的结果或None（如果出现错误）
        
    Raises:
        ValueError: 如果查询过程中出现错误
    """
    await ctx.session.send_log_message(
        level="info",
        data=f"正在获取OpenStack计算服务信息...",
        logger="openstack",
        related_request_id=ctx.request_id,
    )
    
    try:
        # 异步运行OpenStack查询
        if get_compute_services_func:
            services = await get_compute_services_func(filter_value, limit, detail_level)
        else:
            services = await get_compute_services(filter_value, limit, detail_level)
        
        # 发送成功消息
        await ctx.session.send_log_message(
            level="info",
            data=f"成功获取到 {len(services)} 个OpenStack计算服务",
            logger="openstack",
            related_request_id=ctx.request_id,
        )
        
        # 使用格式化函数生成摘要
        summary = format_compute_services_summary(services, detail_level)
        
        return [
            types.TextContent(type="text", text=summary),
        ]
        
    except Exception as err:
        # 发送错误信息
        error_message = f"获取OpenStack计算服务信息失败: {str(err)}"
        await ctx.session.send_log_message(
            level="error",
            data=error_message,
            logger="openstack",
            related_request_id=ctx.request_id,
        )
        raise ValueError(error_message) 