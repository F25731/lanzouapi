# 统一书库 API 平台

面向最多 5 个蓝奏云优享版账号的统一书库后端。外部机器人、网站、后台只调用你自己的 API，平台内部再按 source 维度处理登录、扫盘、索引、搜索、下载缓存和预热。

当前仓库已经覆盖第一阶段和第二阶段的核心能力：

- 最多 5 个 source 管理
- 扫盘任务入库、断点续扫、独立队列
- 文件索引、统一搜索、统一下载
- 直链缓存、并发解析锁、失败退避
- OpenSearch 同步与搜索回退
- 热门文件预热 worker
- 轻量管理面板与指标接口
- Docker Compose、初始化 SQL、`.env.example`
- 基础单元测试、健康检查、Prometheus 风格指标出口

## 参考项目

- [zaxtyson/LanZouCloud-API](https://github.com/zaxtyson/LanZouCloud-API)
- [qaiu/netdisk-fast-download](https://github.com/qaiu/netdisk-fast-download)
- [nfd-parser/nfd-vercel](https://github.com/nfd-parser/nfd-vercel)

本项目没有把底层蓝奏能力写死，而是通过 provider 抽象解耦，便于后续替换成你自己的蓝奏账号 API、解析服务或内部网关。

## 技术栈

- API: FastAPI
- Worker: Python
- 数据库: MySQL 8
- 缓存 / 锁: Redis
- 搜索: OpenSearch
- 部署: Docker Compose

## 项目结构

```text
app/
  api/            # API 路由
  core/           # 配置与日志
  db/             # SQLAlchemy 基础设施
  models/         # 数据模型
  providers/      # 底层网盘 / 解析适配器
  repositories/   # 数据访问层
  schemas/        # Pydantic 模型
  services/       # 业务逻辑
  web/            # 管理面板与指标输出
  workers/        # 扫盘 / 预热 worker
deploy/mysql/init # 初始化 SQL
tests/            # 基础测试
```

## 第一阶段能力

- 5 个 source 独立配置、独立登录、独立限速
- 文件元数据入库：`files`、`source_folders`
- 下载统一出口：`GET /api/download/{id}`
- `direct_link_cache` 缓存当前可用直链，而不是永久直链
- 同一 `file_id` 并发请求只允许一个解析线程进入
- 解析失败自动回退 `share_url`

## 第二阶段能力

### OpenSearch 同步

- 扫盘成功后自动把本次新增 / 更新文件同步到 OpenSearch
- 全量扫描时会把已删除文件从搜索索引移除
- `POST /api/search` 在配置 `OPENSEARCH_URL` 时优先走搜索引擎
- 搜索引擎异常或未配置时自动回退数据库搜索
- 支持手动重建索引：`POST /api/admin/reindex`

### 热门预热

- 依据 `hot_score` 选择热门文件
- 对快过期或缺失的直链缓存做主动刷新
- 支持独立预热 worker
- 支持手动预热：`POST /api/admin/preheat`

### 管理面板与指标

- 管理面板：`GET /admin/panel`
- JSON 指标：`GET /api/admin/metrics`
- Prometheus 文本指标：`GET /metrics`
- 搜索后端状态：`GET /api/admin/search-backend`

## 数据表

当前初始化 SQL 已包含：

- `source_sources`
- `source_folders`
- `files`
- `direct_link_cache`
- `file_stats`
- `scan_jobs`

初始化脚本位于 [deploy/mysql/init/001_schema.sql](/C:/Users/F1589/Desktop/API/deploy/mysql/init/001_schema.sql)。

## API 一览

### 对外接口

- `POST /api/search`
- `GET /api/file/{id}`
- `GET /api/download/{id}`
- `POST /api/refresh/{id}`
- `GET /api/health`

### 管理接口

- `GET /api/admin/sources`
- `POST /api/admin/sources`
- `PUT /api/admin/source/{id}`
- `POST /api/admin/source/{id}/disable`
- `GET /api/admin/source-status`
- `GET /api/admin/scan-jobs`
- `POST /api/admin/source/{id}/rescan`
- `GET /api/admin/cache-overview`
- `GET /api/admin/hot-files`
- `GET /api/admin/search-backend`
- `POST /api/admin/reindex`
- `POST /api/admin/preheat`
- `GET /api/admin/metrics`

如果设置了 `ADMIN_TOKEN`，管理 API 可以通过请求头 `X-Admin-Token` 访问，管理面板可以通过 `?token=...` 打开，例如：

```text
http://localhost:8000/admin/panel?token=change-me
```

## `lanzou_http` 适配约定

`lanzou_http` 假定你有一个可控的内部适配服务。每个 source 的 `config` 建议类似：

```json
{
  "login_path": "/api/login",
  "list_root_path": "/api/folders",
  "list_folder_path": "/api/folders/{folder_id}",
  "resolve_path": "/api/resolve",
  "resolve_method": "POST",
  "headers": {
    "X-Service-Token": "replace-me"
  }
}
```

目录列表接口建议返回：

```json
{
  "folders": [
    {
      "id": "folder-1",
      "name": "小说",
      "full_path": "/小说",
      "share_url": "https://..."
    }
  ],
  "files": [
    {
      "id": "file-1",
      "name": "示例.epub",
      "path": "/小说/示例.epub",
      "size_bytes": 123456,
      "share_url": "https://...",
      "updated_at": "2026-04-08T12:00:00"
    }
  ],
  "next_cursor": null
}
```

解析接口建议返回：

```json
{
  "direct_url": "https://download.example.com/file",
  "expires_at": "2026-04-08T12:30:00"
}
```

## 本地运行

1. 复制环境变量：

```bash
cp .env.example .env
```

2. 启动容器：

```bash
docker compose up --build
```

3. 打开：

- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/api/health`
- 管理面板：`http://localhost:8000/admin/panel`

## 本地开发

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
python -m app.workers.scan_worker
python -m app.workers.preheat_worker
pytest
```

## 常见操作

### 新增 source

```json
POST /api/admin/sources
{
  "name": "lz-source-1",
  "adapter_type": "lanzou_http",
  "base_url": "http://your-lanzou-adapter:9000",
  "username": "your-account",
  "password": "your-password",
  "root_folder_id": "0",
  "rate_limit_per_minute": 30,
  "request_timeout_seconds": 20,
  "config": {
    "login_path": "/api/login",
    "list_root_path": "/api/folders",
    "list_folder_path": "/api/folders/{folder_id}",
    "resolve_path": "/api/resolve"
  }
}
```

### 发起全量重扫

```json
POST /api/admin/source/1/rescan
{
  "mode": "full"
}
```

### 搜索文件

```json
POST /api/search
{
  "keyword": "三体",
  "extensions": ["epub", "mobi"],
  "page": 1,
  "size": 20
}
```

### 重建搜索索引

```json
POST /api/admin/reindex
{
  "source_id": null,
  "batch_size": 500
}
```

### 触发热门预热

```json
POST /api/admin/preheat
{
  "limit": 50,
  "min_hot_score": 1
}
```

## 关键环境变量

- `OPENSEARCH_URL`: OpenSearch 地址，留空则搜索自动回退数据库
- `OPENSEARCH_INDEX_NAME`: 索引名
- `PREHEAT_ENABLED`: 是否开启预热 worker
- `PREHEAT_POLL_INTERVAL_SECONDS`: 预热轮询周期
- `PREHEAT_REFRESH_BEFORE_SECONDS`: 距离过期多久开始预热

## 注意事项

- 当前示例将 source 密码明文保存在数据库中，生产环境建议接入 KMS 或自行加密
- `download` 在解析失败时会回退到分享页，这是最后兜底路径，不建议当成主下载路径
- 多实例部署时建议 Redis 必开，用于分布式直链解析锁
- OpenSearch 未配置时不影响系统运行，只是搜索会回退数据库
