from __future__ import annotations

from html import escape


def render_admin_panel_html(api_prefix: str, token: str) -> str:
    html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>统一书库管理面板</title>
  <style>
    body{margin:0;font-family:"Segoe UI","Microsoft YaHei",sans-serif;background:#f5efe6;color:#1f2b30}
    .wrap{max-width:1280px;margin:20px auto;padding:0 14px}
    .grid{display:grid;grid-template-columns:repeat(12,1fr);gap:16px}
    .card{grid-column:span 12;background:#fffdf8;border:1px solid #e8ddd0;border-radius:18px;padding:18px;box-shadow:0 10px 30px rgba(0,0,0,.06)}
    .span-6{grid-column:span 6}.span-5{grid-column:span 5}.span-7{grid-column:span 7}
    h1,h2{margin:0 0 12px} p{color:#60707a;line-height:1.7}
    .hero{display:grid;grid-template-columns:1.2fr .8fr;gap:16px;margin-bottom:16px}
    .row,.row3{display:grid;gap:10px;margin-bottom:10px}.row{grid-template-columns:1fr 1fr}.row3{grid-template-columns:1fr 1fr 1fr}
    label{display:block;margin-bottom:6px;font-size:12px;color:#60707a;text-transform:uppercase}
    input,select,textarea,button{width:100%;padding:11px 12px;border-radius:12px;border:1px solid #dccfc0;font:inherit}
    textarea{min-height:90px;resize:vertical} button{cursor:pointer;border:none;background:#bf5d30;color:#fff;font-weight:700}
    button.alt{background:#1f7078} button.ghost{background:#fff;color:#1f2b30;border:1px solid #dccfc0}
    .actions{display:flex;gap:8px;flex-wrap:wrap}.actions button{width:auto}
    .kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
    .kpi{padding:14px;border:1px solid #e8ddd0;border-radius:14px;background:#fff}.kpi small{display:block;color:#60707a}.kpi strong{font-size:26px}
    table{width:100%;border-collapse:collapse} th,td{padding:10px 8px;border-bottom:1px solid #efe5da;text-align:left;vertical-align:top}
    th{font-size:12px;color:#60707a;text-transform:uppercase} pre{margin:0;padding:14px;background:#10181c;color:#eef4f5;border-radius:14px;white-space:pre-wrap;word-break:break-word}
    .status{display:inline-block;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:700}.good{background:#e3f3e6;color:#226738}.bad{background:#fde8e8;color:#b83232}.warn{background:#fff1d8;color:#9c6b1c}
    .mono{font-family:Consolas,"Courier New",monospace}.tip{font-size:13px;color:#60707a}
    @media (max-width:980px){.hero,.kpis,.row,.row3{grid-template-columns:1fr}.span-6,.span-5,.span-7{grid-column:span 12}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <section class="card">
        <h1>统一书库管理面板</h1>
        <p>这里可以直接管理 source、测试登录、发起重扫，也可以创建和轮换 API Key。当前 <span class="mono">lanzou_http</span> 需要你提供蓝奏 HTTP 适配服务地址，不是直接蓝奏官网地址。</p>
      </section>
      <section class="card">
        <label>Admin Token</label>
        <input id="tokenInput" type="password" value="__TOKEN__" placeholder="请输入管理 token">
        <div class="actions" style="margin-top:10px">
          <button onclick="applyToken()">应用 Token</button>
          <button class="alt" onclick="refreshAll()">刷新</button>
        </div>
        <p class="tip">API 根地址：<span class="mono">__API_PREFIX__</span><br>基础 API Key 默认含搜索、详情、下载权限。</p>
      </section>
    </div>

    <div class="grid">
      <section class="card">
        <div class="kpis">
          <div class="kpi"><small>活跃文件</small><strong id="kpiFiles">-</strong></div>
          <div class="kpi"><small>总容量</small><strong id="kpiSize">-</strong></div>
          <div class="kpi"><small>缓存命中率</small><strong id="kpiCache">-</strong></div>
          <div class="kpi"><small>搜索后端</small><strong id="kpiSearch">-</strong></div>
        </div>
      </section>

      <section class="card span-7">
        <h2>Source 创建 / 蓝奏登录配置</h2>
        <p class="tip">如果选择 <span class="mono">lanzou_http</span>，请把 <span class="mono">base_url</span> 填成你的蓝奏适配服务地址。</p>
        <div class="row3">
          <div><label>名称</label><input id="sourceName" type="text" placeholder="例如 lanzou-main"></div>
          <div><label>适配器</label><select id="sourceAdapter"><option value="lanzou_http">lanzou_http</option><option value="mock">mock</option></select></div>
          <div><label>根目录 ID</label><input id="sourceRootFolderId" type="text" placeholder="留空则默认"></div>
        </div>
        <div class="row">
          <div><label>Base URL</label><input id="sourceBaseUrl" type="text" placeholder="例如 http://127.0.0.1:7001"></div>
          <div><label>用户名</label><input id="sourceUsername" type="text" placeholder="账号"></div>
        </div>
        <div class="row">
          <div><label>密码</label><input id="sourcePassword" type="password" placeholder="密码"></div>
          <div><label>Headers JSON</label><input id="sourceHeadersJson" type="text" value="{}"></div>
        </div>
        <div class="row3">
          <div><label>rate_limit_per_minute</label><input id="sourceRateLimit" type="number" value="30"></div>
          <div><label>request_timeout_seconds</label><input id="sourceTimeout" type="number" value="20"></div>
          <div><label>resolve_method</label><select id="sourceResolveMethod"><option value="POST">POST</option><option value="GET">GET</option></select></div>
        </div>
        <div class="row3">
          <div><label>login_path</label><input id="sourceLoginPath" type="text" value="/api/login"></div>
          <div><label>list_root_path</label><input id="sourceListRootPath" type="text" value="/api/folders"></div>
          <div><label>list_folder_path</label><input id="sourceListFolderPath" type="text" value="/api/folders/{folder_id}"></div>
        </div>
        <div class="row">
          <div><label>resolve_path</label><input id="sourceResolvePath" type="text" value="/api/resolve"></div>
          <div><label>附加 config JSON</label><input id="sourceExtraConfig" type="text" value="{}"></div>
        </div>
        <div class="actions">
          <button onclick="createSource()">创建 Source</button>
          <button class="alt" onclick="fillLanzouDefaults()">蓝奏默认值</button>
          <button class="ghost" onclick="fillMockDefaults()">Mock 示例</button>
        </div>
        <div style="margin-top:10px"><pre id="sourceActionOutput">等待结果</pre></div>
      </section>

      <section class="card span-5">
        <h2>API Key 管理</h2>
        <div class="row">
          <div><label>client_name</label><input id="clientName" type="text" placeholder="例如 robot-main"></div>
          <div><label>client_type</label><input id="clientType" type="text" value="robot"></div>
        </div>
        <div class="row">
          <div><label>rate_limit_per_min</label><input id="clientRateLimit" type="number" value="60"></div>
          <div><label>ip_whitelist</label><input id="clientIpWhitelist" type="text" placeholder="多个 IP 用英文逗号分隔"></div>
        </div>
        <div class="actions">
          <button onclick="createApiClient()">创建 API Key</button>
          <button class="alt" onclick="loadApiClients()">刷新列表</button>
        </div>
        <div style="margin-top:10px"><pre id="apiKeyOutput">创建后会在这里显示一次明文 API Key</pre></div>
      </section>

      <section class="card span-7">
        <h2>搜索试跑</h2>
        <div class="row3">
          <div><label>关键词</label><input id="searchKeyword" type="text" placeholder="例如 三体"></div>
          <div><label>扩展名</label><input id="searchExtensions" type="text" placeholder="例如 epub,pdf"></div>
          <div><label>每页数量</label><input id="searchSize" type="number" value="10"></div>
        </div>
        <button onclick="runSearch()">搜索</button>
        <div style="margin-top:10px"><pre id="searchOutput">等待搜索结果</pre></div>
      </section>

      <section class="card span-5">
        <h2>运维动作</h2>
        <div class="row">
          <div><label>重扫 Source ID</label><input id="rescanSourceId" type="number" placeholder="例如 2"></div>
          <div><label>扫描模式</label><select id="rescanMode"><option value="rescan">rescan</option><option value="incremental">incremental</option><option value="full">full</option></select></div>
        </div>
        <div class="row3">
          <div><label>重建索引 Source ID</label><input id="reindexSourceId" type="number" placeholder="留空为全部"></div>
          <div><label>批量大小</label><input id="reindexBatch" type="number" value="500"></div>
          <div><label>预热数量</label><input id="preheatLimit" type="number" value="50"></div>
        </div>
        <div class="actions">
          <button onclick="triggerRescanFromForm()">发起重扫</button>
          <button class="alt" onclick="triggerReindex()">重建索引</button>
          <button class="alt" onclick="triggerPreheat()">热门预热</button>
        </div>
        <div style="margin-top:10px"><pre id="opsOutput">等待操作结果</pre></div>
      </section>

      <section class="card">
        <h2>Source 列表</h2>
        <div id="sourceTable"></div>
      </section>

      <section class="card">
        <h2>API Key 列表</h2>
        <div id="apiClientTable"></div>
      </section>

      <section class="card span-7">
        <h2>扫描任务</h2>
        <div id="scanJobs"></div>
      </section>

      <section class="card span-5">
        <h2>缓存与搜索状态</h2>
        <div id="backendStatus"></div>
        <div style="height:10px"></div>
        <div id="cacheOverview"></div>
      </section>

      <section class="card span-6">
        <h2>热门文件</h2>
        <div id="hotFiles"></div>
      </section>

      <section class="card span-6">
        <h2>原始指标</h2>
        <pre id="metricsOutput">等待加载</pre>
      </section>
    </div>
  </div>
  <script>
    const API_PREFIX = "__API_PREFIX__";
    const tokenInput = document.getElementById("tokenInput");
    const basicScopes = ["search:read","file:read","download:read"];
    const adminHeaders = () => tokenInput.value.trim() ? {"X-Admin-Token": tokenInput.value.trim()} : {};
    const list = (raw) => (raw || "").split(",").map(v => v.trim()).filter(Boolean);
    const parseJson = (raw, fallback) => { const v = (raw || "").trim(); return v ? JSON.parse(v) : fallback; };
    const statusClass = (v) => ["active","completed","ok"].includes(v) ? "good" : (["disabled","failed","error"].includes(v) ? "bad" : "warn");
    const bytes = (n) => { if(!n) return "0 B"; const u=["B","KB","MB","GB","TB"]; let i=0,v=n; while(v>=1024 && i<u.length-1){v/=1024;i++;} return `${v.toFixed(i?1:0)} ${u[i]}`; };
    async function api(path, options={}) {
      const res = await fetch(path, { ...options, headers: { "Content-Type": "application/json", ...adminHeaders(), ...(options.headers||{}) } });
      const type = res.headers.get("content-type") || "";
      const body = type.includes("application/json") ? await res.json() : await res.text();
      if (!res.ok) throw new Error(typeof body === "string" ? body : JSON.stringify(body));
      return body;
    }
    function applyToken(){ const url = new URL(window.location.href); const token = tokenInput.value.trim(); token ? url.searchParams.set("token", token) : url.searchParams.delete("token"); window.location.href = url.toString(); }
    function render(headers, rows){ return `<table><thead><tr>${headers.map(v=>`<th>${v}</th>`).join("")}</tr></thead><tbody>${rows.length?rows.map(cols=>`<tr>${cols.map(col=>`<td>${col}</td>`).join("")}</tr>`).join(""):`<tr><td colspan="${headers.length}">暂无数据</td></tr>`}</tbody></table>`; }
    function fillLanzouDefaults(){ document.getElementById("sourceAdapter").value="lanzou_http"; document.getElementById("sourceLoginPath").value="/api/login"; document.getElementById("sourceListRootPath").value="/api/folders"; document.getElementById("sourceListFolderPath").value="/api/folders/{folder_id}"; document.getElementById("sourceResolvePath").value="/api/resolve"; document.getElementById("sourceResolveMethod").value="POST"; document.getElementById("sourceHeadersJson").value="{}"; document.getElementById("sourceExtraConfig").value="{}"; }
    function fillMockDefaults(){ document.getElementById("sourceAdapter").value="mock"; document.getElementById("sourceLoginPath").value=""; document.getElementById("sourceHeadersJson").value="{}"; document.getElementById("sourceExtraConfig").value="{\\"seed\\":\\"books\\"}"; }
    function sourceConfig(){ const adapter = document.getElementById("sourceAdapter").value; const extra = parseJson(document.getElementById("sourceExtraConfig").value, {}); if (adapter === "mock") return extra; return { ...extra, login_path: document.getElementById("sourceLoginPath").value.trim() || null, list_root_path: document.getElementById("sourceListRootPath").value.trim() || "/api/folders", list_folder_path: document.getElementById("sourceListFolderPath").value.trim() || "/api/folders/{folder_id}", resolve_path: document.getElementById("sourceResolvePath").value.trim() || "/api/resolve", resolve_method: document.getElementById("sourceResolveMethod").value, headers: parseJson(document.getElementById("sourceHeadersJson").value, {}) }; }
    async function createSource(){ try{ const body = { name: document.getElementById("sourceName").value.trim(), adapter_type: document.getElementById("sourceAdapter").value, base_url: document.getElementById("sourceBaseUrl").value.trim() || null, username: document.getElementById("sourceUsername").value.trim(), password: document.getElementById("sourcePassword").value, root_folder_id: document.getElementById("sourceRootFolderId").value.trim() || null, config: sourceConfig(), rate_limit_per_minute: Number(document.getElementById("sourceRateLimit").value||30), request_timeout_seconds: Number(document.getElementById("sourceTimeout").value||20) }; const result = await api(`${API_PREFIX}/admin/sources`, {method:"POST", body: JSON.stringify(body)}); document.getElementById("sourceActionOutput").textContent = JSON.stringify(result,null,2); document.getElementById("rescanSourceId").value = result.id; await refreshAll(); }catch(e){ document.getElementById("sourceActionOutput").textContent = "创建失败\\n"+e.message; } }
    async function testSourceLogin(id){ try{ const result = await api(`${API_PREFIX}/admin/source/${id}/login-test`, {method:"POST", body:"{}"}); document.getElementById("sourceActionOutput").textContent = JSON.stringify(result,null,2); await refreshAll(); }catch(e){ document.getElementById("sourceActionOutput").textContent = "登录测试失败\\n"+e.message; } }
    async function disableSource(id){ if(!confirm(`确认禁用 source #${id} 吗？`)) return; try{ const result = await api(`${API_PREFIX}/admin/source/${id}/disable`, {method:"POST", body:"{}"}); document.getElementById("sourceActionOutput").textContent = JSON.stringify(result,null,2); await refreshAll(); }catch(e){ document.getElementById("sourceActionOutput").textContent = "禁用失败\\n"+e.message; } }
    async function triggerRescan(id, mode="rescan"){ try{ const result = await api(`${API_PREFIX}/admin/source/${id}/rescan`, {method:"POST", body: JSON.stringify({provider_folder_id:null, mode})}); document.getElementById("opsOutput").textContent = JSON.stringify(result,null,2); await refreshAll(); }catch(e){ document.getElementById("opsOutput").textContent = "重扫失败\\n"+e.message; } }
    async function triggerRescanFromForm(){ const id = document.getElementById("rescanSourceId").value.trim(); if(!id){ document.getElementById("opsOutput").textContent = "请先填写 Source ID"; return; } await triggerRescan(id, document.getElementById("rescanMode").value); }
    async function triggerReindex(){ try{ const sourceId = document.getElementById("reindexSourceId").value.trim(); const result = await api(`${API_PREFIX}/admin/reindex`, {method:"POST", body: JSON.stringify({ source_id: sourceId ? Number(sourceId) : null, batch_size: Number(document.getElementById("reindexBatch").value||500) })}); document.getElementById("opsOutput").textContent = JSON.stringify(result,null,2); await refreshAll(); }catch(e){ document.getElementById("opsOutput").textContent = "重建索引失败\\n"+e.message; } }
    async function triggerPreheat(){ try{ const result = await api(`${API_PREFIX}/admin/preheat`, {method:"POST", body: JSON.stringify({ limit: Number(document.getElementById("preheatLimit").value||50), min_hot_score: 1 })}); document.getElementById("opsOutput").textContent = JSON.stringify(result,null,2); await refreshAll(); }catch(e){ document.getElementById("opsOutput").textContent = "热门预热失败\\n"+e.message; } }
    async function createApiClient(){ try{ const body = { client_name: document.getElementById("clientName").value.trim(), client_type: document.getElementById("clientType").value.trim() || "robot", scopes: basicScopes, rate_limit_per_min: Number(document.getElementById("clientRateLimit").value||60), ip_whitelist: list(document.getElementById("clientIpWhitelist").value) }; const result = await api(`${API_PREFIX}/admin/api-client/create`, {method:"POST", body: JSON.stringify(body)}); document.getElementById("apiKeyOutput").textContent = JSON.stringify(result,null,2); await loadApiClients(); }catch(e){ document.getElementById("apiKeyOutput").textContent = "创建失败\\n"+e.message; } }
    async function setApiClientStatus(id, enabled){ try{ const action = enabled ? "enable" : "disable"; const result = await api(`${API_PREFIX}/admin/api-client/${id}/${action}`, {method:"POST", body:"{}"}); document.getElementById("apiKeyOutput").textContent = JSON.stringify(result,null,2); await loadApiClients(); }catch(e){ document.getElementById("apiKeyOutput").textContent = "状态更新失败\\n"+e.message; } }
    async function rotateApiClient(id){ try{ const result = await api(`${API_PREFIX}/admin/api-client/${id}/rotate`, {method:"POST", body:"{}"}); document.getElementById("apiKeyOutput").textContent = JSON.stringify(result,null,2); await loadApiClients(); }catch(e){ document.getElementById("apiKeyOutput").textContent = "轮换失败\\n"+e.message; } }
    async function loadApiClients(){ const clients = await api(`${API_PREFIX}/admin/api-clients`); document.getElementById("apiClientTable").innerHTML = render(["ID","名称","前缀","状态","最后使用","操作"], clients.map(v => [v.id, `${v.client_name}<div class="tip">${v.client_type}</div>`, `<span class="mono">${v.key_prefix}</span>`, `<span class="status ${statusClass(v.status)}">${v.status}</span>`, v.last_used_at || "-", `<div class="actions"><button class="ghost" onclick="rotateApiClient(${v.id})">轮换</button><button class="ghost" onclick="setApiClientStatus(${v.id}, ${v.status !== "active"})">${v.status === "active" ? "禁用" : "启用"}</button></div>`])); }
    async function runSearch(){ try{ const exts = list(document.getElementById("searchExtensions").value); const body = { keyword: document.getElementById("searchKeyword").value.trim() || null, extensions: exts.length ? exts : null, page: 1, size: Number(document.getElementById("searchSize").value||10) }; const result = await api(`${API_PREFIX}/search`, {method:"POST", body: JSON.stringify(body), headers:{}}); document.getElementById("searchOutput").textContent = JSON.stringify(result,null,2); }catch(e){ document.getElementById("searchOutput").textContent = "搜索失败\\n"+e.message; } }
    async function refreshAll(){ try{ const [metrics,statuses,cache,hot,jobs,backend,sources] = await Promise.all([api(`${API_PREFIX}/admin/metrics`),api(`${API_PREFIX}/admin/source-status`),api(`${API_PREFIX}/admin/cache-overview`),api(`${API_PREFIX}/admin/hot-files`),api(`${API_PREFIX}/admin/scan-jobs`),api(`${API_PREFIX}/admin/search-backend`),api(`${API_PREFIX}/admin/sources`)]); document.getElementById("kpiFiles").textContent = metrics.file_overview.active_files; document.getElementById("kpiSize").textContent = bytes(metrics.file_overview.total_size_bytes); document.getElementById("kpiCache").textContent = `${(metrics.cache_overview.hit_rate*100).toFixed(1)}%`; document.getElementById("kpiSearch").textContent = `${backend.backend} / ${backend.healthy ? "healthy" : "degraded"}`; document.getElementById("metricsOutput").textContent = JSON.stringify(metrics,null,2); const map = new Map(statuses.map(v=>[v.id,v])); document.getElementById("sourceTable").innerHTML = render(["ID","名称","适配器","状态","最近同步","错误","操作"], sources.map(v => { const rt = map.get(v.id) || v; return [v.id, `${v.name}<div class="tip">${v.username}</div>`, `<span class="mono">${v.adapter_type}</span>`, `<span class="status ${statusClass(rt.status)}">${rt.status}</span>`, rt.last_sync_at || "-", rt.last_error || "-", `<div class="actions"><button class="ghost" onclick="testSourceLogin(${v.id})">登录测试</button><button class="ghost" onclick="triggerRescan(${v.id})">重扫</button><button class="ghost" onclick="disableSource(${v.id})">禁用</button></div>`]; })); document.getElementById("scanJobs").innerHTML = render(["任务","Source","模式","状态","进度","错误"], jobs.map(v => [v.id,v.source_id,v.mode,`<span class="status ${statusClass(v.status)}">${v.status}</span>`,`${v.progress_current} / ${v.progress_total || "?"}`,v.error_message || "-"])); document.getElementById("backendStatus").innerHTML = render(["指标","值"], [["backend", backend.backend], ["healthy", backend.healthy], ["document_count", backend.document_count], ["last_error", backend.last_error || "-"]]); document.getElementById("cacheOverview").innerHTML = render(["指标","值"], [["total_entries",cache.total_entries],["valid_entries",cache.valid_entries],["total_hits",cache.total_hits],["total_misses",cache.total_misses]]); document.getElementById("hotFiles").innerHTML = render(["文件","Source","热度","下载","搜索"], hot.map(v => [v.file_name,v.source_name,v.hot_score,v.download_count,v.search_count])); await loadApiClients(); }catch(e){ document.getElementById("metricsOutput").textContent = "加载失败\\n"+e.message; } }
    fillLanzouDefaults(); refreshAll();
  </script>
</body>
</html>
"""
    return html.replace("__API_PREFIX__", escape(api_prefix)).replace(
        "__TOKEN__", escape(token)
    )
