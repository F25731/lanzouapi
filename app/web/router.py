from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi.responses import HTMLResponse
from fastapi.responses import PlainTextResponse

from app.api.deps import require_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.services.metrics_service import MetricsService

web_router = APIRouter()


@web_router.get("/metrics", response_class=PlainTextResponse)
def metrics_export(db=Depends(get_db)) -> str:
    return MetricsService(db).render_prometheus()


@web_router.get(
    "/admin/panel",
    response_class=HTMLResponse,
    dependencies=[Depends(require_admin)],
)
def admin_panel(token: Optional[str] = Query(default=None)) -> HTMLResponse:
    settings = get_settings()
    return HTMLResponse(
        content=_render_admin_panel_html(
            api_prefix=settings.api_prefix,
            token=token or "",
        )
    )


def _render_admin_panel_html(api_prefix: str, token: str) -> str:
    safe_token = token.replace('"', "&quot;")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>统一书库管理面板</title>
  <style>
    :root {{
      --bg: #f4efe7;
      --panel: rgba(255, 252, 246, 0.92);
      --ink: #1e2a2f;
      --muted: #5e6b70;
      --line: rgba(30, 42, 47, 0.12);
      --accent: #cb5f2d;
      --accent-2: #1d6a70;
      --good: #2f7d32;
      --warn: #b7791f;
      --bad: #c53030;
      --shadow: 0 18px 60px rgba(48, 33, 17, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(203, 95, 45, 0.18), transparent 30%),
        radial-gradient(circle at top right, rgba(29, 106, 112, 0.14), transparent 24%),
        linear-gradient(180deg, #f8f2ea 0%, #efe4d2 100%);
      font-family: "Trebuchet MS", "Microsoft YaHei", sans-serif;
    }}
    .shell {{
      width: min(1280px, calc(100vw - 32px));
      margin: 24px auto 40px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.3fr 0.7fr;
      gap: 18px;
      margin-bottom: 18px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }}
    .hero-card {{
      padding: 26px 28px;
      position: relative;
      overflow: hidden;
    }}
    .hero-card::after {{
      content: "";
      position: absolute;
      inset: auto -40px -40px auto;
      width: 180px;
      height: 180px;
      background: radial-gradient(circle, rgba(203, 95, 45, 0.18), transparent 68%);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(28px, 4vw, 42px);
      letter-spacing: 0.02em;
    }}
    .lead {{
      margin: 0;
      color: var(--muted);
      font-size: 15px;
      line-height: 1.7;
    }}
    .token-box {{
      padding: 22px;
      display: grid;
      gap: 12px;
      align-content: start;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .span-3 {{ grid-column: span 3; }}
    .span-4 {{ grid-column: span 4; }}
    .span-5 {{ grid-column: span 5; }}
    .span-6 {{ grid-column: span 6; }}
    .span-7 {{ grid-column: span 7; }}
    .span-8 {{ grid-column: span 8; }}
    .span-12 {{ grid-column: span 12; }}
    .section {{
      padding: 20px 22px;
    }}
    .section h2 {{
      margin: 0 0 14px;
      font-size: 18px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
    }}
    .kpi {{
      padding: 16px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.6);
      border: 1px solid var(--line);
    }}
    .kpi strong {{
      display: block;
      font-size: 28px;
      margin-top: 6px;
    }}
    label {{
      font-size: 12px;
      text-transform: uppercase;
      color: var(--muted);
      letter-spacing: 0.08em;
    }}
    input, select, button, textarea {{
      width: 100%;
      border-radius: 14px;
      border: 1px solid var(--line);
      padding: 12px 14px;
      font: inherit;
      background: rgba(255, 255, 255, 0.82);
      color: var(--ink);
    }}
    button {{
      cursor: pointer;
      background: linear-gradient(135deg, var(--accent), #de8b53);
      color: #fff8f0;
      font-weight: 700;
      border: none;
    }}
    button.alt {{
      background: linear-gradient(135deg, var(--accent-2), #2b8a92);
    }}
    .row {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
      margin-bottom: 12px;
    }}
    .row-3 {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin-bottom: 12px;
    }}
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .chip {{
      border-radius: 999px;
      padding: 7px 12px;
      background: rgba(29, 106, 112, 0.1);
      color: var(--accent-2);
      font-size: 12px;
      font-weight: 700;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      text-align: left;
      padding: 12px 8px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .status {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      background: rgba(29, 106, 112, 0.1);
    }}
    .status.bad {{ background: rgba(197, 48, 48, 0.12); color: var(--bad); }}
    .status.good {{ background: rgba(47, 125, 50, 0.12); color: var(--good); }}
    .status.warn {{ background: rgba(183, 121, 31, 0.14); color: var(--warn); }}
    .mono {{ font-family: Consolas, "Courier New", monospace; }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      background: rgba(20, 30, 34, 0.92);
      color: #e8e2d6;
      padding: 16px;
      border-radius: 16px;
      min-height: 240px;
    }}
    .mini-actions {{
      display: flex;
      gap: 8px;
    }}
    .mini-actions button {{
      width: auto;
      padding: 10px 12px;
      border-radius: 12px;
    }}
    @media (max-width: 980px) {{
      .hero, .kpis, .row, .row-3 {{
        grid-template-columns: 1fr;
      }}
      .span-3, .span-4, .span-5, .span-6, .span-7, .span-8, .span-12 {{
        grid-column: span 12;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="hero">
      <div class="panel hero-card">
        <div class="chips">
          <span class="chip">OpenSearch</span>
          <span class="chip">热门预热</span>
          <span class="chip">统一下载缓存</span>
          <span class="chip">运维面板</span>
        </div>
        <h1>统一书库 API 平台</h1>
        <p class="lead">
          这里会直接读取你的 source 状态、扫盘任务、缓存命中率、热门文件和搜索后端健康情况。
          所有操作仍然走同一套后端 API，没有额外的后台依赖。
        </p>
      </div>
      <div class="panel token-box">
        <label>Admin Token</label>
        <input id="tokenInput" type="password" value="{safe_token}" placeholder="如果配置了 ADMIN_TOKEN，请填这里">
        <button onclick="applyToken()">应用 Token</button>
        <button class="alt" onclick="refreshAll()">刷新面板</button>
      </div>
    </div>

    <div class="grid">
      <section class="panel section span-12">
        <h2>核心指标</h2>
        <div class="kpis">
          <div class="kpi"><label>活跃文件</label><strong id="kpiFiles">-</strong></div>
          <div class="kpi"><label>总容量</label><strong id="kpiSize">-</strong></div>
          <div class="kpi"><label>缓存命中率</label><strong id="kpiCache">-</strong></div>
          <div class="kpi"><label>搜索后端</label><strong id="kpiSearch">-</strong></div>
        </div>
      </section>

      <section class="panel section span-5">
        <h2>运维动作</h2>
        <div class="row">
          <div>
            <label>Source ID</label>
            <input id="rescanSourceId" type="number" min="1" placeholder="例如 1">
          </div>
          <div>
            <label>扫描模式</label>
            <select id="rescanMode">
              <option value="rescan">rescan</option>
              <option value="incremental">incremental</option>
              <option value="full">full</option>
            </select>
          </div>
        </div>
        <div class="mini-actions">
          <button onclick="triggerRescan()">发起重扫</button>
          <button class="alt" onclick="triggerReindex()">重建索引</button>
          <button class="alt" onclick="triggerPreheat()">热门预热</button>
        </div>
        <div class="row-3" style="margin-top:12px;">
          <div>
            <label>重建 Source ID</label>
            <input id="reindexSourceId" type="number" min="1" placeholder="留空为全量">
          </div>
          <div>
            <label>批量大小</label>
            <input id="reindexBatch" type="number" min="1" value="500">
          </div>
          <div>
            <label>预热数量</label>
            <input id="preheatLimit" type="number" min="1" value="50">
          </div>
        </div>
      </section>

      <section class="panel section span-7">
        <h2>搜索试跑</h2>
        <div class="row-3">
          <div>
            <label>关键词</label>
            <input id="searchKeyword" type="text" placeholder="书名、作者、扩展名">
          </div>
          <div>
            <label>扩展名</label>
            <input id="searchExtensions" type="text" placeholder="epub,mobi,pdf">
          </div>
          <div>
            <label>每页数量</label>
            <input id="searchSize" type="number" min="1" max="100" value="10">
          </div>
        </div>
        <button onclick="runSearch()">搜索</button>
        <pre id="searchOutput" style="margin-top:12px;">等待搜索</pre>
      </section>

      <section class="panel section span-6">
        <h2>Source 状态</h2>
        <div id="sourceStatus"></div>
      </section>

      <section class="panel section span-6">
        <h2>搜索与缓存</h2>
        <div id="backendStatus"></div>
        <div style="height:10px;"></div>
        <div id="cacheOverview"></div>
      </section>

      <section class="panel section span-12">
        <h2>扫盘任务</h2>
        <div id="scanJobs"></div>
      </section>

      <section class="panel section span-6">
        <h2>热门文件</h2>
        <div id="hotFiles"></div>
      </section>

      <section class="panel section span-6">
        <h2>原始指标</h2>
        <pre id="metricsOutput">等待加载</pre>
      </section>
    </div>
  </div>

  <script>
    const API_PREFIX = "{api_prefix}";
    const tokenInput = document.getElementById("tokenInput");

    function getAdminHeaders() {{
      const token = tokenInput.value.trim();
      return token ? {{ "X-Admin-Token": token }} : {{}};
    }}

    async function apiFetch(path, options = {{}}) {{
      const response = await fetch(path, {{
        ...options,
        headers: {{
          "Content-Type": "application/json",
          ...getAdminHeaders(),
          ...(options.headers || {{}})
        }}
      }});
      if (!response.ok) {{
        const text = await response.text();
        throw new Error(text || `HTTP ${{response.status}}`);
      }}
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {{
        return response.json();
      }}
      return response.text();
    }}

    function bytesToReadable(bytes) {{
      if (!bytes) return "0 B";
      const units = ["B", "KB", "MB", "GB", "TB"];
      let value = bytes;
      let index = 0;
      while (value >= 1024 && index < units.length - 1) {{
        value /= 1024;
        index += 1;
      }}
      return `${{value.toFixed(index === 0 ? 0 : 1)}} ${{units[index]}}`;
    }}

    function applyToken() {{
      const url = new URL(window.location.href);
      const token = tokenInput.value.trim();
      if (token) {{
        url.searchParams.set("token", token);
      }} else {{
        url.searchParams.delete("token");
      }}
      window.location.href = url.toString();
    }}

    async function refreshAll() {{
      try {{
        const [metrics, sources, cache, hotFiles, scanJobs, backend] = await Promise.all([
          apiFetch(`${{API_PREFIX}}/admin/metrics`),
          apiFetch(`${{API_PREFIX}}/admin/source-status`),
          apiFetch(`${{API_PREFIX}}/admin/cache-overview`),
          apiFetch(`${{API_PREFIX}}/admin/hot-files`),
          apiFetch(`${{API_PREFIX}}/admin/scan-jobs`),
          apiFetch(`${{API_PREFIX}}/admin/search-backend`)
        ]);

        document.getElementById("kpiFiles").textContent = metrics.file_overview.active_files;
        document.getElementById("kpiSize").textContent = bytesToReadable(metrics.file_overview.total_size_bytes);
        document.getElementById("kpiCache").textContent = `${{(metrics.cache_overview.hit_rate * 100).toFixed(1)}}%`;
        document.getElementById("kpiSearch").textContent = backend.backend + (backend.healthy ? " / healthy" : " / degraded");

        document.getElementById("metricsOutput").textContent = JSON.stringify(metrics, null, 2);

        document.getElementById("backendStatus").innerHTML = `
          <div class="chips">
            <span class="chip">backend: ${{backend.backend}}</span>
            <span class="chip">enabled: ${{backend.enabled}}</span>
            <span class="chip">healthy: ${{backend.healthy}}</span>
            <span class="chip">docs: ${{backend.document_count}}</span>
          </div>
          <div style="margin-top:10px;color:var(--muted);">${{backend.last_error || "搜索后端运行正常"}}</div>
        `;

        document.getElementById("cacheOverview").innerHTML = `
          <table>
            <tr><th>总缓存</th><td>${{cache.total_entries}}</td></tr>
            <tr><th>有效缓存</th><td>${{cache.valid_entries}}</td></tr>
            <tr><th>命中次数</th><td>${{cache.total_hits}}</td></tr>
            <tr><th>未命中次数</th><td>${{cache.total_misses}}</td></tr>
          </table>
        `;

        document.getElementById("sourceStatus").innerHTML = renderTable(
          ["ID", "名称", "状态", "最近同步", "错误"],
          sources.map(item => [
            item.id,
            item.name,
            `<span class="status ${{item.status === "active" ? "good" : item.status === "error" ? "bad" : "warn"}}">${{item.status}}</span>`,
            item.last_sync_at || "-",
            item.last_error || "-"
          ])
        );

        document.getElementById("scanJobs").innerHTML = renderTable(
          ["任务", "Source", "模式", "状态", "进度", "错误"],
          scanJobs.map(item => [
            item.id,
            item.source_id,
            item.mode,
            `<span class="status ${{item.status === "completed" ? "good" : item.status === "failed" ? "bad" : "warn"}}">${{item.status}}</span>`,
            `${{item.progress_current}} / ${{item.progress_total || "?"}}`,
            item.error_message || "-"
          ])
        );

        document.getElementById("hotFiles").innerHTML = renderTable(
          ["文件", "Source", "热度", "下载", "搜索"],
          hotFiles.map(item => [
            item.file_name,
            item.source_name,
            item.hot_score,
            item.download_count,
            item.search_count
          ])
        );
      }} catch (error) {{
        document.getElementById("metricsOutput").textContent = "加载失败: " + error.message;
      }}
    }}

    function renderTable(headers, rows) {{
      return `
        <table>
          <thead><tr>${{headers.map(item => `<th>${{item}}</th>`).join("")}}</tr></thead>
          <tbody>
            ${{rows.map(cols => `<tr>${{cols.map(col => `<td>${{col}}</td>`).join("")}}</tr>`).join("") || '<tr><td colspan="' + headers.length + '">暂无数据</td></tr>'}}
          </tbody>
        </table>
      `;
    }}

    async function runSearch() {{
      const keyword = document.getElementById("searchKeyword").value.trim();
      const extensions = document.getElementById("searchExtensions").value.trim();
      const size = Number(document.getElementById("searchSize").value || 10);
      const payload = {{
        keyword: keyword || null,
        extensions: extensions ? extensions.split(",").map(item => item.trim()).filter(Boolean) : null,
        page: 1,
        size
      }};
      try {{
        const result = await apiFetch(`${{API_PREFIX}}/search`, {{
          method: "POST",
          body: JSON.stringify(payload),
          headers: {{}}
        }});
        document.getElementById("searchOutput").textContent = JSON.stringify(result, null, 2);
      }} catch (error) {{
        document.getElementById("searchOutput").textContent = "搜索失败: " + error.message;
      }}
    }}

    async function triggerRescan() {{
      const sourceId = document.getElementById("rescanSourceId").value.trim();
      const mode = document.getElementById("rescanMode").value;
      if (!sourceId) {{
        alert("请先填写 Source ID");
        return;
      }}
      const result = await apiFetch(`${{API_PREFIX}}/admin/source/${{sourceId}}/rescan`, {{
        method: "POST",
        body: JSON.stringify({{ mode }})
      }});
      alert("已创建重扫任务 #" + result.id);
      refreshAll();
    }}

    async function triggerReindex() {{
      const sourceId = document.getElementById("reindexSourceId").value.trim();
      const batchSize = Number(document.getElementById("reindexBatch").value || 500);
      const result = await apiFetch(`${{API_PREFIX}}/admin/reindex`, {{
        method: "POST",
        body: JSON.stringify({{
          source_id: sourceId ? Number(sourceId) : null,
          batch_size: batchSize
        }})
      }});
      alert("索引重建完成: " + JSON.stringify(result));
      refreshAll();
    }}

    async function triggerPreheat() {{
      const limit = Number(document.getElementById("preheatLimit").value || 50);
      const result = await apiFetch(`${{API_PREFIX}}/admin/preheat`, {{
        method: "POST",
        body: JSON.stringify({{ limit, min_hot_score: 1 }})
      }});
      alert("热门预热完成: " + JSON.stringify(result));
      refreshAll();
    }}

    refreshAll();
  </script>
</body>
</html>"""
