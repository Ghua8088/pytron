INSPECTOR_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pytron Inspector</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #20232a;
            --sidebar: #282c34;
            --surface: #32363e;
            --border: #3d424a;
            --text: #ffffff;
            --text-dim: #9da5b4;
            --accent: #61dafb;
            --success: #4caf50;
            --error: #f44336;
            --warning: #ff9800;
            --header-h: 40px;
            --font-main: 'Inter', -apple-system, sans-serif;
            --font-code: 'JetBrains Mono', 'Fira Code', monospace;
        }

        * { box-sizing: border-box; }
        body {
            margin: 0; padding: 0;
            background: var(--bg);
            color: var(--text);
            font-family: var(--font-main);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }

        /* --- Header --- */
        header {
            height: var(--header-h);
            background: var(--sidebar);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            padding: 0 12px;
            z-index: 100;
        }

        .brand {
            font-weight: 600;
            font-size: 12px;
            color: var(--accent);
            margin-right: 24px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        nav { display: flex; height: 100%; }
        .nav-item {
            padding: 0 16px;
            height: 100%;
            display: flex;
            align-items: center;
            font-size: 13px;
            color: var(--text-dim);
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: 0.1s;
        }
        .nav-item:hover { color: var(--text); }
        .nav-item.active {
            color: var(--accent);
            border-bottom-color: var(--accent);
        }

        /* --- Layout --- */
        main { flex: 1; display: flex; overflow: hidden; }
        .view { display: none; width: 100%; height: 100%; }
        .view.active { display: flex; }

        /* --- Elements / State View (React Style) --- */
        .state-layout { display: flex; width: 100%; height: 100%; }
        .state-tree-pane {
            width: 40%;
            border-right: 1px solid var(--border);
            overflow-y: auto;
            background: var(--bg);
        }
        .state-props-pane {
            flex: 1;
            overflow-y: auto;
            background: var(--sidebar);
            padding: 16px;
        }

        .tree-node-wrap { padding: 2px 0; }
        .tree-row {
            display: flex;
            align-items: center;
            padding: 4px 8px;
            cursor: pointer;
            font-family: var(--font-code);
            font-size: 12px;
            border-radius: 4px;
            margin: 0 4px;
        }
        .tree-row:hover { background: var(--surface); }
        .tree-row.selected { background: #373940; border-left: 2px solid var(--accent); }

        .toggle-icon {
            width: 16px; height: 16px;
            display: flex; align-items: center; justify-content: center;
            color: var(--text-dim);
            margin-right: 4px;
            font-size: 10px;
        }

        .tag-bracket { color: var(--text-dim); }
        .tag-name { color: var(--accent); }

        /* --- Props Inspector --- */
        .props-section { margin-bottom: 24px; }
        .props-title {
            font-size: 11px;
            text-transform: uppercase;
            color: var(--text-dim);
            font-weight: 700;
            margin-bottom: 8px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 4px;
        }
        .prop-row {
            display: flex;
            font-family: var(--font-code);
            font-size: 12px;
            margin-bottom: 4px;
        }
        .prop-key { color: #d2a8ff; margin-right: 8px; }
        .prop-val { color: var(--text); }
        .prop-val.string { color: #a5d6ff; }
        .prop-val.number { color: #ffab70; }
        .prop-val.boolean { color: #79c0ff; }

        /* --- Console --- */
        .console-view { flex-direction: column; background: #1e1e1e; }
        #console-output {
            flex: 1;
            overflow-y: auto;
            padding: 8px;
            display: flex;
            flex-direction: column;
        }
        .console-line {
            display: flex;
            padding: 4px 8px;
            border-bottom: 1px solid rgba(255,255,255,0.03);
            font-family: var(--font-code);
            font-size: 12px;
            line-height: 1.4;
        }
        .line-meta { color: var(--text-dim); width: 80px; font-size: 10px; flex-shrink: 0; }
        .line-content { flex: 1; white-space: pre-wrap; }

        .level-ERROR { color: var(--error); border-left: 3px solid var(--error); background: rgba(244, 67, 54, 0.05); }
        .level-WARNING { color: var(--warning); border-left: 3px solid var(--warning); }

        .console-input-area {
            height: 40px;
            background: var(--sidebar);
            border-top: 1px solid var(--border);
            display: flex;
            align-items: center;
            padding: 0 12px;
        }
        .prompt { color: var(--accent); margin-right: 8px; font-weight: 700; }
        #console-input {
            flex: 1;
            background: transparent;
            border: none;
            color: var(--text);
            font-family: var(--font-code);
            font-size: 12px;
            outline: none;
        }

        /* --- IPC / Network --- */
        .table-wrap { padding: 16px; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; }
        th { text-align: left; padding: 12px 8px; color: var(--text-dim); border-bottom: 2px solid var(--border); text-transform: uppercase; font-size: 10px; }
        td { padding: 10px 8px; border-bottom: 1px solid var(--border); font-family: var(--font-code); }

        /* --- Stats Widgets --- */
        .dashboard-view { padding: 16px; overflow-y: auto; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
        .card { background: var(--sidebar); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
        .card-header { font-size: 11px; font-weight: 700; color: var(--text-dim); text-transform: uppercase; margin-bottom: 16px; }

        .progress-bg { height: 6px; background: var(--bg); border-radius: 3px; overflow: hidden; margin: 8px 0; }
        .progress-fill { height: 100%; background: var(--accent); transition: 0.3s; }

        /* --- Scrollbar --- */
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #3e4451; border-radius: 5px; border: 2px solid var(--bg); }
        ::-webkit-scrollbar-thumb:hover { background: #4b5262; }

        .btn-small {
            background: var(--surface); border: 1px solid var(--border); color: var(--text);
            padding: 2px 8px; border-radius: 4px; font-size: 10px; cursor: pointer;
        }
        .btn-small:hover { background: var(--accent); color: var(--bg); }
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"></path></svg>
            PYTRON
        </div>
        <nav>
            <div class="nav-item active" onclick="showView('elements')">Elements</div>
            <div class="nav-item" onclick="showView('console')">Console</div>
            <div class="nav-item" onclick="showView('network')">Network</div>
            <div class="nav-item" onclick="showView('stats')">Stats</div>
        </nav>
        <div id="uptime-display" style="margin-left:auto; font-size:11px; color:var(--text-dim); margin-right: 15px;">Uptime: 0s</div>
        <button id="trace-toggle" class="btn-small" style="margin-right: 8px;" onclick="toggleTrace()">Trace IPC: OFF</button>
    </header>

    <main>
        <!-- ELEMENTS (State Tree) -->
        <div id="elements" class="view active state-layout">
            <div class="state-tree-pane" id="state-tree-container"></div>
            <div class="state-props-pane" id="state-props-container">
                <div class="props-title">Props</div>
                <div id="props-content">Select a node to inspect state</div>
            </div>
        </div>

        <!-- CONSOLE -->
        <div id="console" class="view console-view">
            <div id="console-output"></div>
            <div class="console-input-area">
                <span class="prompt">>>></span>
                <input type="text" id="console-input" placeholder="Execute Python..." spellcheck="false">
            </div>
        </div>

        <!-- NETWORK (IPC) -->
        <div id="network" class="view">
            <div class="table-wrap">
                <div style="margin-bottom: 15px; display: flex; gap: 10px;">
                    <button class="btn-small" onclick="runPing()">Run Diagnostic Ping</button>
                    <span id="ping-status" style="font-size: 11px; align-self: center;"></span>
                </div>
                <table>
                    <thead>
                        <tr><th>Time</th><th>Method</th><th>Latency</th><th>Status</th></tr>
                    </thead>
                    <tbody id="ipc-body"></tbody>
                </table>
            </div>
        </div>

        <!-- STATS -->
        <div id="stats" class="view dashboard-view">
            <div class="grid">
                <div class="card">
                    <div class="card-header">Engine Performance</div>
                    <div class="stat-row">CPU <span class="stat-val" id="cpu-val">0%</span></div>
                    <div class="progress-bg"><div id="cpu-bar" class="progress-fill"></div></div>
                    <div class="stat-row">Memory <span class="stat-val" id="mem-val">0 MB</span></div>
                    <div class="stat-row">Threads <span class="stat-val" id="thread-val">0</span></div>
                </div>
                <div class="card">
                    <div class="card-header">Active Windows</div>
                    <div id="win-list"></div>
                </div>
                <div class="card">
                    <div class="card-header">Environment</div>
                    <div id="env-list"></div>
                </div>
            </div>
        </div>
    </main>

    <script>
        let currentView = 'elements';
        let selectedPath = 'App.State';
        const expandedPaths = new Set(['App.State']);
        let fullData = null;

        function showView(name) {
            currentView = name;
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            document.getElementById(name).classList.add('active');

            // Highlight nav
            const navs = document.querySelectorAll('.nav-item');
            navs.forEach(n => { if(n.innerText.toLowerCase() === name) n.classList.add('active'); });

            refreshData();
        }

        async function refreshData() {
            try {
                const data = await pytron.inspector_get_data();
                fullData = data;

                document.getElementById('uptime-display').innerText = `PID: ${data.stats.pid} | Uptime: ${data.stats.uptime}s`;

                if (currentView === 'elements') renderState();
                if (currentView === 'console') refreshLogs();
                if (currentView === 'network') renderIPC();
                if (currentView === 'stats') renderStats();
            } catch (e) {}
        }

        // --- State Tree ---
        function renderState() {
            const container = document.getElementById('state-tree-container');
            container.innerHTML = '';
            container.appendChild(createTreeNode(fullData.state, 'App.State', 'App.State'));
            renderProps();
        }

        function createTreeNode(val, key, path) {
            const wrap = document.createElement('div');
            wrap.className = 'tree-node-wrap';

            const isObj = typeof val === 'object' && val !== null;
            const expanded = expandedPaths.has(path);
            const isSelected = selectedPath === path;

            const row = document.createElement('div');
            row.className = `tree-row ${isSelected ? 'selected' : ''}`;
            row.style.paddingLeft = (path.split('.').length * 12) + 'px';

            row.onclick = (e) => {
                e.stopPropagation();
                selectedPath = path;
                renderState();
            };

            const toggle = document.createElement('span');
            toggle.className = 'toggle-icon';
            toggle.innerHTML = isObj ? (expanded ? '▼' : '▶') : '';
            toggle.onclick = (e) => {
                e.stopPropagation();
                if (expanded) expandedPaths.delete(path);
                else expandedPaths.add(path);
                renderState();
            };

            row.appendChild(toggle);

            const label = document.createElement('span');
            label.innerHTML = `<span class="tag-bracket">&lt;</span><span class="tag-name">${key}</span><span class="tag-bracket">&gt;</span>`;
            row.appendChild(label);

            wrap.appendChild(row);

            if (isObj && expanded) {
                for (let k in val) {
                    wrap.appendChild(createTreeNode(val[k], k, `${path}.${k}`));
                }
            }
            return wrap;
        }

        function renderProps() {
            const container = document.getElementById('props-content');
            let target = fullData.state;
            const parts = selectedPath.split('.').slice(1);

            for (let p of parts) {
                if (target && target[p] !== undefined) target = target[p];
            }

            container.innerHTML = '';
            if (typeof target === 'object' && target !== null) {
                for (let k in target) {
                    const row = document.createElement('div');
                    row.className = 'prop-row';
                    const val = target[k];
                    const type = typeof val;
                    row.innerHTML = `<span class="prop-key">${k}:</span><span class="prop-val ${type}">${JSON.stringify(val)}</span>`;
                    container.appendChild(row);
                }
            } else {
                container.innerHTML = `<div class="prop-row"><span class="prop-key">value:</span><span class="prop-val">${JSON.stringify(target)}</span></div>`;
            }
        }

        // --- Console ---
        async function refreshLogs() {
            const logs = await pytron.inspector_get_logs();
            const out = document.getElementById('console-output');
            const atBottom = out.scrollHeight - out.scrollTop <= out.clientHeight + 50;

            out.innerHTML = logs.map(l => `
                <div class="console-line level-${l.level}">
                    <div class="line-meta">${l.time}</div>
                    <div class="line-content">${escapeHtml(l.msg)}</div>
                </div>
            `).join('');

            if (atBottom) out.scrollTop = out.scrollHeight;
        }

        document.getElementById('console-input').onkeydown = async (e) => {
            if (e.key === 'Enter') {
                const cmd = e.target.value;
                if (!cmd) return;
                e.target.value = '';
                await pytron.inspector_eval(cmd);
                refreshLogs();
            }
        };

        // --- IPC ---
        function renderIPC() {
            const body = document.getElementById('ipc-body');
            body.innerHTML = fullData.ipc_history.slice().reverse().map(h => `
                <tr>
                    <td>${h.time}</td>
                    <td style="color:var(--accent)">${h.function}</td>
                    <td>${h.duration}ms</td>
                    <td class="${h.error?'ipc-status-err':'ipc-status-ok'}">${h.error?'ERROR':'OK'}</td>
                </tr>
            `).join('');
        }

        // --- Stats ---
        function renderStats() {
            const s = fullData.stats;
            document.getElementById('cpu-val').innerText = s.process_cpu.toFixed(1) + '%';
            document.getElementById('cpu-bar').style.width = Math.min(s.process_cpu, 100) + '%';
            document.getElementById('mem-val').innerText = s.process_mem + ' MB';
            document.getElementById('thread-val').innerText = s.threads;

            document.getElementById('win-list').innerHTML = fullData.windows.map(w => `
                <div class="stat-row" style="padding: 4px 0; border-bottom: 1px solid var(--border)">
                    <span>${w.title} <small style="color:var(--text-dim)">(${w.dimensions[0]}x${w.dimensions[1]})</small></span>
                    <button class="btn-small" onclick="pytron.inspector_window_action(${w.id}, 'center')">Center</button>
                </div>
            `).join('');

            document.getElementById('env-list').innerHTML = `
                <div class="stat-row">Platform <span class="stat-val">${s.platform}</span></div>
                <div class="stat-row">Python PID <span class="stat-val">${s.pid}</span></div>
            `;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        let isTraceOn = false;
        async function toggleTrace() {
            isTraceOn = !isTraceOn;
            document.getElementById('trace-toggle').innerText = `Trace IPC: ${isTraceOn ? 'ON' : 'OFF'}`;
            document.getElementById('trace-toggle').style.borderColor = isTraceOn ? 'var(--accent)' : 'var(--border)';

            // Tell ALL windows to enable verbose logging
            await pytron.publish('pytron:set-verbose', isTraceOn);
        }

        async function runPing() {
            const status = document.getElementById('ping-status');
            status.innerText = "Pinging...";
            try {
                const res = await pytron.ping();
                status.innerText = `[${res.status}] Latency: ${res.latency}ms | State Sync: ${res.hasState?'YES':'NO'}`;
                status.style.color = res.status === 'OK' ? 'var(--success)' : 'var(--error)';
            } catch(e) {
                status.innerText = "Ping Failed: " + e.message;
                status.style.color = 'var(--error)';
            }
        }

        setInterval(refreshData, 2000);
        refreshData();
    </script>
</body>
</html>
    """
