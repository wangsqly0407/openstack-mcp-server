import json
import anyio
from typing import Optional
import mcp.types as types

async def get_volumes(filter_value: str = "", limit: int = 100, detail_level: str = "detailed", **kwargs) -> list[dict]:
    """Get OpenStack Cinder volumes with filtering and detail level options.
    
    Args:
        filter_value: Optional filter for volume name or ID
        limit: Maximum number of volumes to return
        detail_level: Level of detail to return (basic, detailed, full)
        **kwargs: Additional keyword arguments for OpenStack connection
        
    Returns:
        List of volume dictionaries with information based on detail_level
        
    Raises:
        Exception: If OpenStack connection or query fails
    """
    from openstack import connection
    
    # 使用anyio在线程池中运行阻塞操作
    def get_volumes():
        # 认证配置
        conn = connection.Connection(
            **kwargs
        )
        
        # 获取所有卷
        volumes = list(conn.block_storage.volumes())
        
        # 应用过滤器
        if filter_value:
            volumes = [v for v in volumes if (
                (v.name and filter_value.lower() in v.name.lower()) or 
                filter_value in v.id
            )]
        
        # 应用限制
        volumes = volumes[:limit]
        
        # 根据详细程度准备结果
        results = []
        for volume in volumes:
            if detail_level == "basic":
                volume_info = {
                    "id": volume.id,
                    "name": volume.name,
                    "status": volume.status,
                    "size": volume.size
                }
            elif detail_level == "detailed":
                volume_info = {
                    "id": volume.id,
                    "name": volume.name,
                    "status": volume.status,
                    "size": volume.size,
                    "volume_type": getattr(volume, "volume_type", "未知"),
                    "bootable": getattr(volume, "bootable", False),
                    "created_at": getattr(volume, "created_at", "未知"),
                    "attachments": getattr(volume, "attachments", []),
                    "availability_zone": getattr(volume, "availability_zone", "未知")
                }
            else:  # full
                # 将卷对象转换为字典
                volume_info = {k: v for k, v in volume.to_dict().items() if v is not None}
            
            results.append(volume_info)
        
        return results
    
    # 在线程池中执行阻塞操作
    return await anyio.to_thread.run_sync(get_volumes)


def format_volumes_summary(volumes: list[dict], detail_level: str = "detailed") -> str:
    """格式化OpenStack卷信息为人类可读的摘要。
    
    Args:
        volumes: OpenStack卷信息列表
        detail_level: 详细程度 (basic, detailed, full)
        
    Returns:
        格式化后的文本摘要
    """
    if not volumes:
        return "未找到符合条件的OpenStack卷。"
    
    # 基本摘要信息
    summary = f"找到 {len(volumes)} 个OpenStack卷:\n\n"
    for idx, volume in enumerate(volumes, 1):
        summary += f"{idx}. ID: {volume['id']}\n"
        summary += f"   名称: {volume['name'] or '未命名'}\n"
        summary += f"   状态: {volume['status']}\n"
        summary += f"   大小: {volume['size']} GB\n"
        
        # 根据详细程度添加额外信息
        if detail_level != "basic":
            if "created_at" in volume:
                summary += f"   创建时间: {volume['created_at']}\n"
            if "volume_type" in volume:
                summary += f"   卷类型: {volume['volume_type']}\n"
            if "bootable" in volume:
                summary += f"   可启动: {'是' if volume['bootable'] == 'true' else '否'}\n"
            if "availability_zone" in volume:
                summary += f"   可用区: {volume['availability_zone']}\n"
            if "attachments" in volume and volume["attachments"]:
                summary += f"   挂载信息: {json.dumps(volume['attachments'], ensure_ascii=False)}\n"
        
        summary += "\n"
    
    return summary


async def process_volume_query(
    ctx, 
    filter_value: str = "", 
    limit: int = 100, 
    detail_level: str = "detailed",
    get_volumes_func = None
) -> Optional[list[types.TextContent]]:
    """处理OpenStack卷查询的完整流程。
    
    Args:
        ctx: MCP请求上下文
        filter_value: 卷筛选条件
        limit: 返回结果数量限制
        detail_level: 详细程度
        get_volumes_func: 获取卷的函数
        
    Returns:
        返回格式化的结果或None（如果出现错误）
        
    Raises:
        ValueError: 如果查询过程中出现错误
    """
    await ctx.session.send_log_message(
        level="info",
        data=f"正在获取OpenStack卷信息...",
        logger="openstack",
        related_request_id=ctx.request_id,
    )
    
    try:
        # 异步运行OpenStack查询
        if get_volumes_func:
            volumes = await get_volumes_func(filter_value, limit, detail_level)
        else:
            volumes = await get_volumes(filter_value, limit, detail_level)
        
        # 发送成功消息
        await ctx.session.send_log_message(
            level="info",
            data=f"成功获取到 {len(volumes)} 个OpenStack卷",
            logger="openstack",
            related_request_id=ctx.request_id,
        )
        
        # 使用格式化函数生成摘要
        summary = format_volumes_summary(volumes, detail_level)
        
        return [
            types.TextContent(type="text", text=summary),
        ]
        
    except Exception as err:
        # 发送错误信息
        error_message = f"获取OpenStack卷信息失败: {str(err)}"
        await ctx.session.send_log_message(
            level="error",
            data=error_message,
            logger="openstack",
            related_request_id=ctx.request_id,
        )
        raise ValueError(error_message) 