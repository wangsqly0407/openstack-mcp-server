import json
import anyio
from typing import Optional
import mcp.types as types

async def get_images(filter_value: str = "", limit: int = 100, detail_level: str = "detailed", **kwargs) -> list[dict]:
    """Get OpenStack Glance images with filtering and detail level options.
    
    Args:
        filter_value: Optional filter for image name or ID
        limit: Maximum number of images to return
        detail_level: Level of detail to return (basic, detailed, full)
        **kwargs: Additional keyword arguments for OpenStack connection
        
    Returns:
        List of image dictionaries with information based on detail_level
        
    Raises:
        Exception: If OpenStack connection or query fails
    """
    from openstack import connection
    
    # 使用anyio在线程池中运行阻塞操作
    def get_images():
        # 认证配置
        conn = connection.Connection(
            **kwargs
        )
        
        # 获取所有镜像
        images = list(conn.image.images())
        
        # 应用过滤器
        if filter_value:
            images = [i for i in images if (
                (i.name and filter_value.lower() in i.name.lower()) or 
                filter_value in i.id
            )]
        
        # 应用限制
        images = images[:limit]
        
        # 根据详细程度准备结果
        results = []
        for image in images:
            if detail_level == "basic":
                image_info = {
                    "id": image.id,
                    "name": image.name,
                    "status": image.status,
                    "size": getattr(image, "size", 0),
                    "disk_format": getattr(image, "disk_format", "未知")
                }
            elif detail_level == "detailed":
                image_info = {
                    "id": image.id,
                    "name": image.name,
                    "status": image.status,
                    "size": getattr(image, "size", 0),
                    "disk_format": getattr(image, "disk_format", "未知"),
                    "container_format": getattr(image, "container_format", "未知"),
                    "min_disk": getattr(image, "min_disk", 0),
                    "min_ram": getattr(image, "min_ram", 0),
                    "created_at": getattr(image, "created_at", "未知"),
                    "updated_at": getattr(image, "updated_at", "未知"),
                    "visibility": getattr(image, "visibility", "未知"),
                    "protected": getattr(image, "protected", False),
                    "owner_id": getattr(image, "owner_id", "未知")
                }
            else:  # full
                # 将镜像对象转换为字典
                image_info = {k: v for k, v in image.to_dict().items() if v is not None}
            
            results.append(image_info)
        
        return results
    
    # 在线程池中执行阻塞操作
    return await anyio.to_thread.run_sync(get_images)


def format_images_summary(images: list[dict], detail_level: str = "detailed") -> str:
    """格式化OpenStack镜像信息为人类可读的摘要。
    
    Args:
        images: OpenStack镜像信息列表
        detail_level: 详细程度 (basic, detailed, full)
        
    Returns:
        格式化后的文本摘要
    """
    if not images:
        return "未找到符合条件的OpenStack镜像。"
    
    # 基本摘要信息
    summary = f"找到 {len(images)} 个OpenStack镜像:\n\n"
    for idx, image in enumerate(images, 1):
        summary += f"{idx}. ID: {image['id']}\n"
        summary += f"   名称: {image['name'] or '未命名'}\n"
        summary += f"   状态: {image['status']}\n"
        
        # 格式化镜像大小
        size_mb = image.get('size', 0) / (1024 * 1024) if image.get('size') else 0
        if size_mb > 1024:
            size_gb = size_mb / 1024
            summary += f"   大小: {size_gb:.2f} GB\n"
        else:
            summary += f"   大小: {size_mb:.2f} MB\n"
            
        summary += f"   格式: {image.get('disk_format', '未知')}\n"
        
        # 根据详细程度添加额外信息
        if detail_level != "basic":
            if "container_format" in image:
                summary += f"   容器格式: {image['container_format']}\n"
            if "min_disk" in image:
                summary += f"   最小磁盘: {image['min_disk']} GB\n"
            if "min_ram" in image:
                summary += f"   最小内存: {image['min_ram']} MB\n"
            if "created_at" in image:
                summary += f"   创建时间: {image['created_at']}\n"
            if "visibility" in image:
                summary += f"   可见性: {image['visibility']}\n"
            if "protected" in image:
                summary += f"   受保护: {'是' if image['protected'] else '否'}\n"
            if "owner_id" in image:
                summary += f"   所有者ID: {image['owner_id']}\n"
        
        summary += "\n"
    
    return summary


async def process_image_query(
    ctx, 
    filter_value: str = "", 
    limit: int = 100, 
    detail_level: str = "detailed",
    get_images_func = None
) -> Optional[list[types.TextContent]]:
    """处理OpenStack镜像查询的完整流程。
    
    Args:
        ctx: MCP请求上下文
        filter_value: 镜像筛选条件
        limit: 返回结果数量限制
        detail_level: 详细程度
        get_images_func: 获取镜像的函数
        
    Returns:
        返回格式化的结果或None（如果出现错误）
        
    Raises:
        ValueError: 如果查询过程中出现错误
    """
    await ctx.session.send_log_message(
        level="info",
        data=f"正在获取OpenStack镜像信息...",
        logger="openstack",
        related_request_id=ctx.request_id,
    )
    
    try:
        # 异步运行OpenStack查询
        if get_images_func:
            images = await get_images_func(filter_value, limit, detail_level)
        else:
            images = await get_images(filter_value, limit, detail_level)
        
        # 发送成功消息
        await ctx.session.send_log_message(
            level="info",
            data=f"成功获取到 {len(images)} 个OpenStack镜像",
            logger="openstack",
            related_request_id=ctx.request_id,
        )
        
        # 使用格式化函数生成摘要
        summary = format_images_summary(images, detail_level)
        
        return [
            types.TextContent(type="text", text=summary),
        ]
        
    except Exception as err:
        # 发送错误信息
        error_message = f"获取OpenStack镜像信息失败: {str(err)}"
        await ctx.session.send_log_message(
            level="error",
            data=error_message,
            logger="openstack",
            related_request_id=ctx.request_id,
        )
        raise ValueError(error_message) 