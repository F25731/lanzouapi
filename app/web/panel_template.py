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
    :root{
      --bg:#f5efe6;--card:#fffdf8;--line:#e8ddd0;--text:#1f2b30;--muted:#60707a;
      --brand:#bf5d30;--brand-alt:#1f7078;--ok-bg:#e3f3e6;--ok-fg:#226738;
      --bad-bg:#fde8e8;--bad-fg:#b83232;--warn-bg:#fff1d8;--warn-fg:#9c6b1c;
    }
    *{box-sizing:border-box}
    body{margin:0;font-family:"Segoe UI","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text)}
    .wrap{max-width:1280px;margin:20px auto;padding:0 14px}
    .hero{display:grid;grid-template-columns:1.2fr .8fr;gap:16px;margin-bottom:16px}
    .grid{display:grid;grid-template-columns:repeat(12,1fr);gap:16px}
    .card{grid-column:span 12;background:var(--card);border:1px solid var(--line);border-radius:18px;padding:18px;box-shadow:0 10px 30px rgba(0,0,0,.06)}
    .span-7{grid-column:span 7}.span-6{grid-column:span 6}.span-5{grid-column:span 5}
    h1,h2{margin:0 0 12px}
    p{margin:0 0 10px;color:var(--muted);line-height:1.75}
    .row,.row3{display:grid;gap:10px;margin-bottom:10px}
    .row{grid-template-columns:1fr 1fr}.row3{grid-template-columns:1fr 1fr 1fr}
    .stack{display:grid;gap:10px}
    label{display:block;margin-bottom:6px;font-size:12px;color:var(--muted);text-transform:uppercase}
    input,select,textarea,button{width:100%;padding:11px 12px;border-radius:12px;border:1px solid #dccfc0;font:inherit}
    textarea{min-height:96px;resize:vertical}
    button{cursor:pointer;border:none;background:var(--brand);color:#fff;font-weight:700}
    button.alt{background:var(--brand-alt)}
    button.ghost{background:#fff;color:var(--text);border:1px solid #dccfc0}
    .actions{display:flex;gap:8px;flex-wrap:wrap}
    .actions button{width:auto}
    .kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
    .kpi{padding:14px;border:1px solid var(--line);border-radius:14px;background:#fff}
    .kpi small{display:block;color:var(--muted)}
    .kpi strong{font-size:26px}
    table{width:100%;border-collapse:collapse}
    th,td{padding:10px 8px;border-bottom:1px solid #efe5da;text-align:left;vertical-align:top}
    th{font-size:12px;color:var(--muted);text-transform:uppercase}
    pre{margin:0;padding:14px;background:#10181c;color:#eef4f5;border-radius:14px;white-space:pre-wrap;word-break:break-word}
    .status{display:inline-block;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:700}
    .good{background:var(--ok-bg);color:var(--ok-fg)}
    .bad{background:var(--bad-bg);color:var(--bad-fg)}
    .warn{background:var(--warn-bg);color:var(--warn-fg)}
    .mono{font-family:Consolas,"Courier New",monospace}
    .tip{font-size:13px;color:var(--muted)}
    .hidden{display:none !important}
    @media (max-width:980px){
      .hero,.kpis,.row,.row3{grid-template-columns:1fr}
      .span-7,.span-6,.span-5{grid-column:span 12}
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <section class="card">
        <h1>统一书库管理面板</h1>
        <p>这里可以直接创建 source、测试蓝奏登录、发起重扫、查看任务，也可以创建和轮换 API Key。</p>
        <p>直连模式推荐使用 <span class="mono">lanzou_sdk</span>，优先填 Cookie；<span class="mono">lanzou_http</span> 仅在你已经有自己的蓝奏适配服务时使用。</p>
      </section>
      <section class="card">
        <label>Admin Token</label>
        <input id="tokenInput" type="password" value="__TOKEN__" placeholder="请输入管理 token">
        <div class="actions" style="margin-top:10px">
          <button onclick="applyToken()">应用 Token</button>
          <button class="alt" onclick="refreshAll()">刷新面板</button>
        </div>
        <p class="tip">API 根地址：<span class="mono">__API_PREFIX__</span><br>基础 API Key 默认包含搜索、文件详情、下载三项权限。</p>
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
        <div class="row3">
          <div><label>名称</label><input id="sourceName" type="text" placeholder="例如 lanzou-main"></div>
          <div>
            <label>适配器</label>
            <select id="sourceAdapter" onchange="refreshSourceMode()">
              <option value="lanzou_sdk">lanzou_sdk（直连蓝奏）</option>
              <option value="lanzou_http">lanzou_http（已有适配服务）</option>
              <option value="mock">mock（本地演示）</option>
            </select>
          </div>
          <div><label>根目录 ID</label><input id="sourceRootFolderId" type="text" placeholder="留空表示根目录"></div>
        </div>

        <div id="sourceSdkHint" class="tip" style="margin-bottom:10px">
          直连蓝奏推荐只填 <span class="mono">ylogin</span> 和 <span class="mono">phpdisk_info</span>。账号密码可以不填，仅作为少数场景的兼容回退。
        </div>
        <div id="sourceHttpHint" class="tip hidden" style="margin-bottom:10px">
          如果选择 <span class="mono">lanzou_http</span>，请把 <span class="mono">base_url</span> 填成你自己的蓝奏适配服务地址。
        </div>
        <div id="sourceMockHint" class="tip hidden" style="margin-bottom:10px">
          Mock 仅用于本地演示，不会访问真实蓝奏账号。
        </div>

        <div id="baseUrlRow" class="row hidden">
          <div><label>Base URL</label><input id="sourceBaseUrl" type="text" placeholder="例如 http://127.0.0.1:7001"></div>
          <div><label>Headers JSON</label><input id="sourceHeadersJson" type="text" value="{}"></div>
        </div>

        <div id="sdkCookieRow" class="row">
          <div><label>ylogin</label><input id="sourceYlogin" type="text" placeholder="浏览器 Cookie 里的 ylogin"></div>
          <div><label>phpdisk_info</label><input id="sourcePhpdiskInfo" type="text" placeholder="浏览器 Cookie 里的 phpdisk_info"></div>
        </div>

        <div id="credentialRow" class="row">
          <div><label>用户名</label><input id="sourceUsername" type="text" placeholder="Cookie 模式可留空"></div>
          <div><label>密码</label><input id="sourcePassword" type="password" placeholder="Cookie 模式可留空"></div>
        </div>

        <div id="httpPathsBlock" class="stack hidden">
          <div class="row3">
            <div><label>login_path</label><input id="sourceLoginPath" type="text" value="/api/login"></div>
            <div><label>list_root_path</label><input id="sourceListRootPath" type="text" value="/api/folders"></div>
            <div><label>list_folder_path</label><input id="sourceListFolderPath" type="text" value="/api/folders/{folder_id}"></div>
          </div>
          <div class="row">
            <div><label>resolve_path</label><input id="sourceResolvePath" type="text" value="/api/resolve"></div>
            <div><label>resolve_method</label><select id="sourceResolveMethod"><option value="POST">POST</option><option value="GET">GET</option></select></div>
          </div>
        </div>

        <div class="row3">
          <div><label>rate_limit_per_minute</label><input id="sourceRateLimit" type="number" value="30"></div>
          <div><label>request_timeout_seconds</label><input id="sourceTimeout" type="number" value="20"></div>
          <div><label>附加 config JSON</label><input id="sourceExtraConfig" type="text" value="{}"></div>
        </div>

        <div class="actions">
          <button onclick="createSource()">创建 Source</button>
          <button class="alt" onclick="fillLanzouSdkDefaults()">蓝奏直连默认</button>
          <button class="alt" onclick="fillLanzouHttpDefaults()">适配服务默认</button>
          <button class="ghost" onclick="fillMockDefaults()">Mock 示例</button>
        </div>
        <div style="margin-top:10px"><pre id="sourceActionOutput">等待操作结果</pre></div>
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
        <button onclick="runSearch()">执行搜索</button>
        <div style="margin-top:10px"><pre id="searchOutput">等待搜索结果</pre></div>
      </section>

      <section class="card span-5">
        <h2>运维动作</h2>
        <div class="row">
          <div><label>重扫 Source ID</label><input id="rescanSourceId" type="number" placeholder="例如 2"></div>
          <div><label>扫描模式</label><select id="rescanMode"><option value="rescan">rescan</option><option value="incremental">incremental</option><option value="full">full</option></select></div>
        </div>
        <div class="row3">
          <div><label>重建索引 Source ID</label><input id="reindexSourceId" type="number" placeholder="留空表示全部"></div>
          <div><label>索引批大小</label><input id="reindexBatch" type="number" value="500"></div>
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
    const parseJson = (raw, fallback) => {
      const value = (raw || "").trim();
      if (!value) return fallback;
      try { return JSON.parse(value); } catch (_) { throw new Error("JSON 格式不正确"); }
    };
    const statusClass = (value) => ["active","completed","ok"].includes(value) ? "good" : (["disabled","failed","error"].includes(value) ? "bad" : "warn");
    const bytes = (value) => {
      if (!value) return "0 B";
      const units = ["B","KB","MB","GB","TB"];
      let size = Number(value);
      let index = 0;
      while (size >= 1024 && index < units.length - 1) { size /= 1024; index += 1; }
      return `${size.toFixed(index ? 1 : 0)} ${units[index]}`;
    };

    async function api(path, options = {}) {
      const response = await fetch(path, {
        ...options,
        headers: { "Content-Type": "application/json", ...adminHeaders(), ...(options.headers || {}) }
      });
      const type = response.headers.get("content-type") || "";
      const body = type.includes("application/json") ? await response.json() : await response.text();
      if (!response.ok) throw new Error(typeof body === "string" ? body : JSON.stringify(body, null, 2));
      return body;
    }

    function renderTable(headers, rows) {
      const head = `<thead><tr>${headers.map(v => `<th>${v}</th>`).join("")}</tr></thead>`;
      const body = rows.length ? rows.map(cols => `<tr>${cols.map(col => `<td>${col}</td>`).join("")}</tr>`).join("") : `<tr><td colspan="${headers.length}">暂无数据</td></tr>`;
      return `<table>${head}<tbody>${body}</tbody></table>`;
    }

    function applyToken() {
      const url = new URL(window.location.href);
      const token = tokenInput.value.trim();
      if (token) url.searchParams.set("token", token); else url.searchParams.delete("token");
      window.location.href = url.toString();
    }

    function refreshSourceMode() {
      const adapter = document.getElementById("sourceAdapter").value;
      const isSdk = adapter === "lanzou_sdk";
      const isHttp = adapter === "lanzou_http";
      const isMock = adapter === "mock";
      document.getElementById("sourceSdkHint").classList.toggle("hidden", !isSdk);
      document.getElementById("sourceHttpHint").classList.toggle("hidden", !isHttp);
      document.getElementById("sourceMockHint").classList.toggle("hidden", !isMock);
      document.getElementById("baseUrlRow").classList.toggle("hidden", !isHttp);
      document.getElementById("sdkCookieRow").classList.toggle("hidden", !isSdk);
      document.getElementById("httpPathsBlock").classList.toggle("hidden", !isHttp);
      const hint = isSdk ? "Cookie 模式可留空" : (isMock ? "演示数据可随便填" : "蓝奏适配服务登录账号");
      document.getElementById("sourceUsername").placeholder = hint;
      document.getElementById("sourcePassword").placeholder = hint;
    }

    function fillLanzouSdkDefaults() {
      document.getElementById("sourceAdapter").value = "lanzou_sdk";
      document.getElementById("sourceBaseUrl").value = "";
      document.getElementById("sourceHeadersJson").value = "{}";
      document.getElementById("sourceUsername").value = "";
      document.getElementById("sourcePassword").value = "";
      document.getElementById("sourceYlogin").value = "";
      document.getElementById("sourcePhpdiskInfo").value = "";
      document.getElementById("sourceExtraConfig").value = "{\\"fetch_share_urls\\":true}";
      refreshSourceMode();
    }

    function fillLanzouHttpDefaults() {
      document.getElementById("sourceAdapter").value = "lanzou_http";
      document.getElementById("sourceLoginPath").value = "/api/login";
      document.getElementById("sourceListRootPath").value = "/api/folders";
      document.getElementById("sourceListFolderPath").value = "/api/folders/{folder_id}";
      document.getElementById("sourceResolvePath").value = "/api/resolve";
      document.getElementById("sourceResolveMethod").value = "POST";
      document.getElementById("sourceHeadersJson").value = "{}";
      document.getElementById("sourceExtraConfig").value = "{}";
      refreshSourceMode();
    }

    function fillMockDefaults() {
      document.getElementById("sourceAdapter").value = "mock";
      document.getElementById("sourceBaseUrl").value = "";
      document.getElementById("sourceUsername").value = "demo";
      document.getElementById("sourcePassword").value = "demo";
      document.getElementById("sourceHeadersJson").value = "{}";
      document.getElementById("sourceExtraConfig").value = "{\\"seed\\":\\"books\\"}";
      refreshSourceMode();
    }

    function buildSourceConfig() {
      const adapter = document.getElementById("sourceAdapter").value;
      const extra = parseJson(document.getElementById("sourceExtraConfig").value, {});
      if (adapter === "mock") return extra;
      if (adapter === "lanzou_http") {
        return {
          ...extra,
          login_path: document.getElementById("sourceLoginPath").value.trim() || null,
          list_root_path: document.getElementById("sourceListRootPath").value.trim() || "/api/folders",
          list_folder_path: document.getElementById("sourceListFolderPath").value.trim() || "/api/folders/{folder_id}",
          resolve_path: document.getElementById("sourceResolvePath").value.trim() || "/api/resolve",
          resolve_method: document.getElementById("sourceResolveMethod").value,
          headers: parseJson(document.getElementById("sourceHeadersJson").value, {})
        };
      }
      const cookie = {};
      const ylogin = document.getElementById("sourceYlogin").value.trim();
      const phpdiskInfo = document.getElementById("sourcePhpdiskInfo").value.trim();
      if (ylogin) cookie.ylogin = ylogin;
      if (phpdiskInfo) cookie.phpdisk_info = phpdiskInfo;
      return { ...extra, ...(Object.keys(cookie).length ? { cookie } : {}) };
    }

    async function createSource() {
      try {
        const adapter = document.getElementById("sourceAdapter").value;
        const config = buildSourceConfig();
        const body = {
          name: document.getElementById("sourceName").value.trim(),
          adapter_type: adapter,
          base_url: adapter === "lanzou_http" ? (document.getElementById("sourceBaseUrl").value.trim() || null) : null,
          username: document.getElementById("sourceUsername").value.trim(),
          password: document.getElementById("sourcePassword").value,
          root_folder_id: document.getElementById("sourceRootFolderId").value.trim() || null,
          config,
          rate_limit_per_minute: Number(document.getElementById("sourceRateLimit").value || 30),
          request_timeout_seconds: Number(document.getElementById("sourceTimeout").value || 20)
        };
        const result = await api(`${API_PREFIX}/admin/sources`, {method:"POST", body: JSON.stringify(body)});
        document.getElementById("sourceActionOutput").textContent = JSON.stringify(result, null, 2);
        document.getElementById("rescanSourceId").value = result.id;
        await refreshAll();
      } catch (error) {
        document.getElementById("sourceActionOutput").textContent = `创建失败\\n${error.message}`;
      }
    }

    async function testSourceLogin(id) {
      try {
        const result = await api(`${API_PREFIX}/admin/source/${id}/login-test`, {method:"POST", body:"{}"});
        document.getElementById("sourceActionOutput").textContent = JSON.stringify(result, null, 2);
        await refreshAll();
      } catch (error) {
        document.getElementById("sourceActionOutput").textContent = `登录测试失败\\n${error.message}`;
      }
    }

    async function disableSource(id) {
      if (!confirm(`确认禁用 source #${id} 吗？`)) return;
      try {
        const result = await api(`${API_PREFIX}/admin/source/${id}/disable`, {method:"POST", body:"{}"});
        document.getElementById("sourceActionOutput").textContent = JSON.stringify(result, null, 2);
        await refreshAll();
      } catch (error) {
        document.getElementById("sourceActionOutput").textContent = `禁用失败\\n${error.message}`;
      }
    }

    async function triggerRescan(id, mode = "rescan") {
      try {
        const result = await api(`${API_PREFIX}/admin/source/${id}/rescan`, {method:"POST", body: JSON.stringify({provider_folder_id: null, mode})});
        document.getElementById("opsOutput").textContent = JSON.stringify(result, null, 2);
        await refreshAll();
      } catch (error) {
        document.getElementById("opsOutput").textContent = `重扫失败\\n${error.message}`;
      }
    }

    async function triggerRescanFromForm() {
      const id = document.getElementById("rescanSourceId").value.trim();
      if (!id) { document.getElementById("opsOutput").textContent = "请先填写 Source ID"; return; }
      await triggerRescan(id, document.getElementById("rescanMode").value);
    }

    async function triggerReindex() {
      try {
        const sourceId = document.getElementById("reindexSourceId").value.trim();
        const result = await api(`${API_PREFIX}/admin/reindex`, {method:"POST", body: JSON.stringify({ source_id: sourceId ? Number(sourceId) : null, batch_size: Number(document.getElementById("reindexBatch").value || 500) })});
        document.getElementById("opsOutput").textContent = JSON.stringify(result, null, 2);
        await refreshAll();
      } catch (error) {
        document.getElementById("opsOutput").textContent = `重建索引失败\\n${error.message}`;
      }
    }

    async function triggerPreheat() {
      try {
        const result = await api(`${API_PREFIX}/admin/preheat`, {method:"POST", body: JSON.stringify({ limit: Number(document.getElementById("preheatLimit").value || 50), min_hot_score: 1 })});
        document.getElementById("opsOutput").textContent = JSON.stringify(result, null, 2);
        await refreshAll();
      } catch (error) {
        document.getElementById("opsOutput").textContent = `热门预热失败\\n${error.message}`;
      }
    }

    async function createApiClient() {
      try {
        const body = {
          client_name: document.getElementById("clientName").value.trim(),
          client_type: document.getElementById("clientType").value.trim() || "robot",
          scopes: basicScopes,
          rate_limit_per_min: Number(document.getElementById("clientRateLimit").value || 60),
          ip_whitelist: list(document.getElementById("clientIpWhitelist").value)
        };
        const result = await api(`${API_PREFIX}/admin/api-client/create`, {method:"POST", body: JSON.stringify(body)});
        document.getElementById("apiKeyOutput").textContent = JSON.stringify(result, null, 2);
        await loadApiClients();
      } catch (error) {
        document.getElementById("apiKeyOutput").textContent = `创建失败\\n${error.message}`;
      }
    }

    async function setApiClientStatus(id, enabled) {
      try {
        const action = enabled ? "enable" : "disable";
        const result = await api(`${API_PREFIX}/admin/api-client/${id}/${action}`, {method:"POST", body:"{}"});
        document.getElementById("apiKeyOutput").textContent = JSON.stringify(result, null, 2);
        await loadApiClients();
      } catch (error) {
        document.getElementById("apiKeyOutput").textContent = `状态更新失败\\n${error.message}`;
      }
    }

    async function rotateApiClient(id) {
      try {
        const result = await api(`${API_PREFIX}/admin/api-client/${id}/rotate`, {method:"POST", body:"{}"});
        document.getElementById("apiKeyOutput").textContent = JSON.stringify(result, null, 2);
        await loadApiClients();
      } catch (error) {
        document.getElementById("apiKeyOutput").textContent = `轮换失败\\n${error.message}`;
      }
    }

    async function loadApiClients() {
      const clients = await api(`${API_PREFIX}/admin/api-clients`);
      document.getElementById("apiClientTable").innerHTML = renderTable(
        ["ID","名称","前缀","状态","最后使用","操作"],
        clients.map(item => [
          item.id,
          `${item.client_name}<div class="tip">${item.client_type}</div>`,
          `<span class="mono">${item.key_prefix}</span>`,
          `<span class="status ${statusClass(item.status)}">${item.status}</span>`,
          item.last_used_at || "-",
          `<div class="actions"><button class="ghost" onclick="rotateApiClient(${item.id})">轮换</button><button class="ghost" onclick="setApiClientStatus(${item.id}, ${item.status !== "active"})">${item.status === "active" ? "禁用" : "启用"}</button></div>`
        ])
      );
    }

    async function runSearch() {
      try {
        const extensions = list(document.getElementById("searchExtensions").value);
        const body = { keyword: document.getElementById("searchKeyword").value.trim() || null, extensions: extensions.length ? extensions : null, page: 1, size: Number(document.getElementById("searchSize").value || 10) };
        const result = await api(`${API_PREFIX}/search`, {method:"POST", body: JSON.stringify(body)});
        document.getElementById("searchOutput").textContent = JSON.stringify(result, null, 2);
      } catch (error) {
        document.getElementById("searchOutput").textContent = `搜索失败\\n${error.message}`;
      }
    }

    async function refreshAll() {
      try {
        const [metrics, statuses, cache, hot, jobs, backend, sources] = await Promise.all([
          api(`${API_PREFIX}/admin/metrics`),
          api(`${API_PREFIX}/admin/source-status`),
          api(`${API_PREFIX}/admin/cache-overview`),
          api(`${API_PREFIX}/admin/hot-files`),
          api(`${API_PREFIX}/admin/scan-jobs`),
          api(`${API_PREFIX}/admin/search-backend`),
          api(`${API_PREFIX}/admin/sources`)
        ]);
        document.getElementById("kpiFiles").textContent = metrics.file_overview.active_files;
        document.getElementById("kpiSize").textContent = bytes(metrics.file_overview.total_size_bytes);
        document.getElementById("kpiCache").textContent = `${(metrics.cache_overview.hit_rate * 100).toFixed(1)}%`;
        document.getElementById("kpiSearch").textContent = `${backend.backend} / ${backend.healthy ? "healthy" : "degraded"}`;
        document.getElementById("metricsOutput").textContent = JSON.stringify(metrics, null, 2);

        const statusMap = new Map(statuses.map(item => [item.id, item]));
        document.getElementById("sourceTable").innerHTML = renderTable(
          ["ID","名称","适配器","状态","最近同步","错误","操作"],
          sources.map(item => {
            const runtime = statusMap.get(item.id) || item;
            return [
              item.id,
              `${item.name}<div class="tip">${item.username || "（未显示账号）"}</div>`,
              `<span class="mono">${item.adapter_type}</span>`,
              `<span class="status ${statusClass(runtime.status)}">${runtime.status}</span>`,
              runtime.last_sync_at || "-",
              runtime.last_error || "-",
              `<div class="actions"><button class="ghost" onclick="testSourceLogin(${item.id})">登录测试</button><button class="ghost" onclick="triggerRescan(${item.id})">重扫</button><button class="ghost" onclick="disableSource(${item.id})">禁用</button></div>`
            ];
          })
        );

        document.getElementById("scanJobs").innerHTML = renderTable(
          ["任务","Source","模式","状态","进度","错误"],
          jobs.map(item => [item.id, item.source_id, item.mode, `<span class="status ${statusClass(item.status)}">${item.status}</span>`, `${item.progress_current} / ${item.progress_total || "?"}`, item.error_message || "-"])
        );

        document.getElementById("backendStatus").innerHTML = renderTable(["指标","值"], [["backend", backend.backend], ["healthy", backend.healthy], ["document_count", backend.document_count], ["last_error", backend.last_error || "-"]]);
        document.getElementById("cacheOverview").innerHTML = renderTable(["指标","值"], [["total_entries", cache.total_entries], ["valid_entries", cache.valid_entries], ["total_hits", cache.total_hits], ["total_misses", cache.total_misses]]);
        document.getElementById("hotFiles").innerHTML = renderTable(["文件","Source","热度","下载","搜索"], hot.map(item => [item.file_name, item.source_name, item.hot_score, item.download_count, item.search_count]));
        await loadApiClients();
      } catch (error) {
        document.getElementById("metricsOutput").textContent = `加载失败\\n${error.message}`;
      }
    }

    fillLanzouSdkDefaults();
    refreshAll();
  </script>
</body>
</html>
"""
    return html.replace("__API_PREFIX__", escape(api_prefix)).replace(
        "__TOKEN__", escape(token)
    )
