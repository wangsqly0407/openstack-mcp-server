# OpenStack MCP Server

## 总览

基于MCP(Model Context Protocol)的OpenStack资源查询服务，提供API接口查询OpenStack云平台的计算、存储、网络、镜像等资源信息。

## 功能特性

- **实时资源查询**：通过API获取OpenStack集群的最新资源状态
- **多维度信息**：支持查询计算、存储、网络、镜像等多种资源
- **灵活过滤**：支持按名称、ID等条件筛选资源
- **详细程度控制**：支持基础、详细、完整三种信息展示级别
- **标准MCP接口**：完全兼容MCP协议，可与大语言模型无缝集成

## 技术架构

- 基于Starlette和Uvicorn的高性能异步HTTP服务
- 使用OpenStack SDK与OpenStack API交互
- 通过MCP协议将OpenStack资源信息结构化提供给大语言模型
- 支持SSE流式输出，提供实时反馈

### 架构图

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│             │    │             │    │             │
│  AI客户端    │───▶│  MCP Server │───▶│  OpenStack  │
│  (LLM大模型) │◀───│  (服务端)    │◀───│  API        │
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
```

## 安装

### 环境要求

- Python 3.10+
- OpenStack环境

### 通过pip安装

```bash
pip install openstack-mcp-server
```

## 使用方法

### 启动服务

```bash
openstack-mcp-server --port 8000 --log-level INFO --auth-url 'http://<OpenStack-API-Endpoint>:5000/v3' --username '<OpenStack-Admin-User>' --password '<OpenStack-Admin-Password>'
```

服务启动后，将在`http://localhost:8000/openstack`提供MCP接口。

### 参数说明

- `--port`: 服务监听端口，默认为8000
- `--log-level`: 日志级别，可选值为DEBUG、INFO、WARNING、ERROR、CRITICAL，默认为INFO
- `--json-response`: 使用JSON响应代替SSE流，默认为False

### 接口示例

通过MCP协议，可以使用以下工具查询OpenStack资源：

#### 获取OpenStack虚拟机实例

```json
{
  "name": "get_instances",
  "arguments": {
    "filter": "web-server",
    "limit": 10,
    "detail_level": "detailed"
  }
}
```

参数说明：
- `filter`: 筛选条件，如实例名称或ID（可选）
- `limit`: 返回结果的最大数量（可选，默认100）
- `detail_level`: 返回信息的详细程度，可选值为basic、detailed、full（可选，默认detailed）

## 通过源码安装

```bash
# 克隆仓库
git clone https://github.com/wangshqly0407/openstack-mcp-server.git
cd openstack-mcp-server
# 创建虚拟环境
uv venv
# 激活虚拟环境
source .venv/bin/activate
# 初始化运行环监
uv sync
# 开启流式HTTP MCP服务器
uv run ./src/mcp_openstack_http/server.py --port 8000 --log-level INFO --auth-url 'http://<OpenStack-API-Endpoint>:5000/v3' --username '<OpenStack-Admin-User>' --password '<OpenStack-Admin-Password>'
```

## 测试验证

```bash
# 方式1：使用npx测试
npx -y @modelcontextprotocol/inspector uv run ./src/mcp_openstack_http/server.py --port 8000 --log-level INFO --auth-url 'http://<OpenStack-API-Endpoint>:5000/v3' --username '<OpenStack-Admin-User>' --password '<OpenStack-Admin-Password>'

# 方式2：使用docker测试
docker run -it --rm -p 6274:6274 -p 6277:6277 -v $(pwd):/app -w /app node:18 npx -y @modelcontextprotocol/inspector uv run ./src/mcp_openstack_http/server.py --port 8000 --log-level INFO --auth-url 'http://<OpenStack-API-Endpoint>:5000/v3' --username '<OpenStack-Admin-User>' --password '<OpenStack-Admin-Password>'
```

访问：http://localhost:6274/

![image](./img/image.png)

## 扩展开发

### 添加新的资源查询工具

1. 在`src/mcp_openstack_http/server.py`中添加相应的资源获取函数
2. 在`list_tools`方法中注册新工具
3. 在`call_tool`方法中实现工具的处理逻辑

## 许可证

Apache 2.0
