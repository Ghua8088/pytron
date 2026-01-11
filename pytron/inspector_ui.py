INSPECTOR_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pytron Inspector</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0d1117;
            --surface: #161b22;
            --border: #30363d;
            --text: #c9d1d9;
            --text-dim: #8b949e;
            --accent: #58a6ff;
            --success: #3fb950;
            --error: #f85149;
            --warning: #d29922;
            --header-h: 40px; /* Slimmer header like Chrome DevTools */
        }

        * { box-sizing: border-box; }
        body {
            margin: 0;
            padding: 0;
            background: var(--bg);
            color: var(--text);
            font-family: 'Inter', -apple-system, sans-serif;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }

        /* Tabs bar - Chrome Style */
        header {
            height: var(--header-h);
            background: #1f2428;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            padding: 0;
            user-select: none;
        }

        .brand {
            padding: 0 16px;
            font-weight: 700;
            font-size: 11px;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 1px;
            border-right: 1px solid var(--border);
            height: 100%;
            display: flex;
            align-items: center;
        }

        nav {
            display: flex;
            height: 100%;
        }

        .nav-item {
            padding: 0 16px;
            display: flex;
            align-items: center;
            font-size: 12px;
            cursor: pointer;
            color: var(--text-dim);
            border-right: 1px solid transparent;
            border-left: 1px solid transparent;
            height: 100%;
            transition: all 0.1s;
        }

        .nav-item:hover { color: var(--text); background: rgba(255,255,255,0.05); }
        .nav-item.active {
            color: var(--text);
            background: var(--bg);
            border-left: 1px solid var(--border);
            border-right: 1px solid var(--border);
            border-bottom: 1px solid var(--bg);
            margin-bottom: -1px;
            z-index: 10;
        }

        main {
            flex: 1;
            overflow: hidden;
            position: relative;
        }

        .view {
            display: none;
            height: 100%;
            width: 100%;
            overflow: auto;
        }

        .view.active { display: flex; flex-direction: column; }

        /* Generic Container */
        .content-padding { padding: 16px; }

        /* Dashboard Grid */
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 16px;
            padding: 16px;
        }

        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 12px;
        }

        .card-title {
            font-size: 11px;
            font-weight: 700;
            color: var(--text-dim);
            text-transform: uppercase;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .stat-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 6px;
            font-size: 12px;
        }

        .stat-val { font-weight: 600; color: var(--accent); font-family: 'Fira Code', monospace; }

        /* Badges */
        .badge {
            font-size: 10px;
            padding: 1px 6px;
            border-radius: 10px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .badge-success { background: rgba(63, 185, 80, 0.15); color: var(--success); border: 1px solid rgba(63, 185,  green, 0.2); }
        .badge-error { background: rgba(248, 81, 73, 0.15); color: var(--error); border: 1px solid rgba(248, 81, 73, 0.2); }

        /* Console Style REPL & Logs */
        .console-container {
            flex: 1;
            background: var(--bg);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .console-output {
            flex: 1;
            overflow-y: auto;
            font-family: 'Fira Code', monospace;
            font-size: 12px;
            padding: 8px;
            border-bottom: 1px solid var(--border);
        }

        .console-line {
            padding: 3px 6px;
            border-bottom: 1px solid rgba(255,255,255,0.02);
            display: flex;
            gap: 8px;
        }
        .console-line:hover { background: rgba(255,255,255,0.02); }
        .line-time { color: var(--text-dim); min-width: 65px; }
        .line-level { font-weight: 700; min-width: 50px; }
        .level-DEBUG { color: var(--text-dim); }
        .level-INFO { color: var(--accent); }
        .level-WARNING { color: var(--warning); }
        .level-ERROR { color: var(--error); }

        .console-input-area {
            height: 32px;
            background: var(--surface);
            display: flex;
            align-items: center;
            padding: 0 8px;
            gap: 8px;
        }
        .console-prompt { color: var(--accent); font-weight: 700; font-size: 13px; margin-top: -2px; }
        .console-input {
            flex: 1;
            background: transparent;
            border: none;
            color: var(--text);
            font-family: 'Fira Code', monospace;
            font-size: 12px;
            outline: none;
        }

        /* IPC List */
        .ipc-table { width: 100%; border-collapse: collapse; font-family: 'Fira Code', monospace; font-size: 11px; }
        .ipc-table th { text-align: left; padding: 6px 12px; background: #1f2428; color: var(--text-dim); border-bottom: 1px solid var(--border); }
        .ipc-table td { padding: 4px 12px; border-bottom: 1px solid var(--border); }
        .ipc-status-ok { color: var(--success); }
        .ipc-status-err { color: var(--error); }

        /* Utility */
        .btn { background: var(--border); border: 1px solid #444c56; color: var(--text); font-size: 11px; padding: 2px 8px; border-radius: 3px; cursor: pointer; }
        .btn:hover { background: #444c56; }
        
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 5px; border: 2px solid var(--bg); }
        ::-webkit-scrollbar-thumb:hover { background: #484f58; }

        /* State Tree */
        .tree-node { margin-left: 12px; border-left: 1px solid rgba(255,255,255,0.05); padding-left: 8px; }
        .tree-header { cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 1px 0; }
        .tree-header:hover { background: rgba(255,255,255,0.03); }
        .tree-key { color: #79c0ff; }
        .tree-val-str { color: #a5d6ff; }
        .tree-toggle { display: inline-block; width: 10px; font-size: 8px; color: var(--text-dim); }
    </style>
</head>
<body>
    <header>
        <div class="brand">Pytron Kit</div>
        <nav>
            <div class="nav-item active" onclick="switchView('dashboard')">Elements</div>
            <div class="nav-item" onclick="switchView('console')">Console</div>
            <div class="nav-item" onclick="switchView('network')">Network (IPC)</div>
            <div class="nav-item" onclick="switchView('application')">Application</div>
        </nav>
        <div style="margin-left: auto; padding-right: 12px; font-size: 10px; color: var(--text-dim);">
            <span id="uptime-display">Uptime: 0s</span>
        </div>
    </header>

    <main>
        <!-- ELEMENTS VIEW (Dashboard/Trees) -->
        <div id="view-dashboard" class="view active">
            <div class="dashboard-grid">
                <div class="card">
                    <div class="card-title">Performance Metrics</div>
                    <div class="stat-row">CPU <span id="cpu-num" class="stat-val">0.0%</span></div>
                    <div style="height:4px; background:var(--border); margin-bottom:12px; border-radius:2px; overflow:hidden;">
                        <div id="cpu-bar" style="width:0%; height:100%; background:var(--accent); transition: width 0.3s;"></div>
                    </div>
                    <div class="stat-row">Memory (RSS) <span id="mem-num" class="stat-val">0MB</span></div>
                    <div class="stat-row">Threads <span id="thread-num" class="stat-val">0</span></div>
                </div>

                <div class="card">
                    <div class="card-title">Active Windows</div>
                    <div id="window-list"></div>
                </div>

                <div class="card" style="grid-column: span 1;">
                    <div class="card-title">Plugin Status</div>
                    <div id="plugin-list" class="stat-row" style="flex-direction:column; gap:4px;"></div>
                </div>
            </div>
            
            <div class="content-padding" style="border-top:1px solid var(--border);">
                <div class="card-title">Reactive State Tree</div>
                <div id="state-tree" style="font-family:'Fira Code', monospace; font-size:12px;"></div>
            </div>
        </div>

        <!-- CONSOLE VIEW (Combined Logs & REPL) -->
        <div id="view-console" class="view">
            <div class="console-container">
                <div id="console-output" class="console-output"></div>
                <div class="console-input-area">
                    <span class="console-prompt">›</span>
                    <input type="text" id="console-input" class="console-input" placeholder="Enter Python command..." autocomplete="off">
                </div>
            </div>
        </div>

        <!-- NETWORK VIEW (IPC) -->
        <div id="view-network" class="view">
            <table class="ipc-table">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Method</th>
                        <th>Status</th>
                        <th>Duration</th>
                    </tr>
                </thead>
                <tbody id="ipc-body"></tbody>
            </table>
        </div>

        <!-- APPLICATION VIEW (Environment) -->
        <div id="view-application" class="view content-padding">
            <div class="card">
                <div class="card-title">Environment Information</div>
                <div id="env-details"></div>
            </div>
        </div>
    </main>

    <script>
        let currentView = 'dashboard';
        let refreshTimer = null;

        function switchView(name) {
            currentView = name;
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(v => v.classList.remove('active'));
            document.getElementById(`view-${name}`).classList.add('active');
            
            // Find nav item by visible text for simpler matching
            const navs = document.querySelectorAll('.nav-item');
            navs.forEach(n => {
                if(n.innerText.toLowerCase().includes(name === 'dashboard' ? 'elements' : name)) n.classList.add('active');
            });
            refreshData();
        }

        async function refreshData() {
            const data = await window.inspector_get_data();
            updateUptime(data.stats);
            
            if(currentView === 'dashboard') {
                updatePerformance(data.stats);
                updateWindows(data.windows);
                updatePlugins(data.plugins);
                renderStateTree(data.state);
            } else if (currentView === 'network') {
                updateIPC(data.ipc_history);
            } else if (currentView === 'application') {
                updateEnvironment(data.stats);
            }
            
            // Logs are updated separately or on console view
            if(currentView === 'console') refreshLogs();
        }

        function updateUptime(s) {
            if(!s) return;
            document.getElementById('uptime-display').innerText = `Uptime: ${s.uptime}s | PID: ${s.pid}`;
        }

        function updatePerformance(s) {
            if(!s) return;
            document.getElementById('cpu-num').innerText = s.process_cpu.toFixed(1) + '%';
            document.getElementById('cpu-bar').style.width = Math.min(s.process_cpu, 100) + '%';
            document.getElementById('mem-num').innerText = s.process_mem + ' MB';
            document.getElementById('thread-num').innerText = s.threads;
        }

        function updateWindows(wins) {
            const container = document.getElementById('window-list');
            container.innerHTML = wins.map(w => `
                <div style="border-bottom:1px solid var(--border); padding:6px 0; display:flex; justify-content:space-between; align-items:center;">
                    <div style="overflow:hidden">
                        <div style="font-size:12px; font-weight:600; color:var(--text);">${w.title}</div>
                        <div style="font-size:10px; color:var(--text-dim); white-space:nowrap; text-overflow:ellipsis; overflow:hidden; width:180px;">${w.url}</div>
                        <div style="font-size:9px; color:var(--accent);">${w.dimensions[0]}x${w.dimensions[1]}</div>
                    </div>
                    <div style="display:flex; gap:4px;">
                        <button class="btn" onclick="winAction(${w.id}, '${w.visible?'hide':'show'}')">${w.visible?'Hide':'Show'}</button>
                    </div>
                </div>
            `).join('');
        }

        function updatePlugins(plugins) {
            const container = document.getElementById('plugin-list');
            container.innerHTML = plugins.map(p => `
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:12px;">${p.name} <small style="color:var(--text-dim)">v${p.version||'?'}</small></span>
                    <span class="badge ${p.status === 'loaded' ? 'badge-success' : 'badge-error'}">${p.status}</span>
                </div>
            `).join('');
        }

        function updateIPC(history) {
            const body = document.getElementById('ipc-body');
            body.innerHTML = history.slice().reverse().map(e => `
                <tr>
                    <td>${e.time}</td>
                    <td><span style="color:var(--warning)">${e.function}</span></td>
                    <td><span class="${e.error ? 'ipc-status-err' : 'ipc-status-ok'}">${e.error ? 'FAILED' : 'OK'}</span></td>
                    <td>${e.duration}ms</td>
                </tr>
            `).join('');
        }

        function updateEnvironment(s) {
            const container = document.getElementById('env-details');
            container.innerHTML = `
                <div class="stat-row">Platform <span class="stat-val">${s.platform}</span></div>
                <div class="stat-row">Python Version <span class="stat-val">${navigator.userAgent.includes('Python') ? 'Inside Runtime' : 'Native'}</span></div>
            `;
        }

        // --- Console / Logs logic ---
        async function refreshLogs() {
            const logs = await window.inspector_get_logs();
            const container = document.getElementById('console-output');
            const atBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 40;
            
            container.innerHTML = logs.map(l => `
                <div class="console-line">
                    <span class="line-time">${l.time}</span>
                    <span class="line-level level-${l.level}">${l.level}</span>
                    <span class="line-msg">${escapeHtml(l.msg)}</span>
                </div>
            `).join('');
            
            if(atBottom) container.scrollTop = container.scrollHeight;
        }

        const cin = document.getElementById('console-input');
        const cout = document.getElementById('console-output');
        cin.onkeydown = async (e) => {
            if(e.key === 'Enter') {
                const cmd = cin.value.trim();
                if(!cmd) return;
                cin.value = '';
                
                // Add to output immediately
                const userLine = document.createElement('div');
                userLine.className = 'console-line';
                userLine.innerHTML = `<span style="color:var(--accent); font-weight:700;">»</span> <span style="font-style:italic;">${escapeHtml(cmd)}</span>`;
                cout.appendChild(userLine);
                
                try {
                    const res = await window.inspector_eval(cmd);
                    const resLine = document.createElement('div');
                    resLine.className = 'console-line';
                    if(res.error) {
                        resLine.innerHTML = `<span style="color:var(--error)">✖ ${escapeHtml(res.error)}</span>`;
                    } else {
                        resLine.innerHTML = `<span style="color:var(--success)">◀</span> <span>${escapeHtml(JSON.stringify(res.result, null, 2))}</span>`;
                    }
                    cout.appendChild(resLine);
                } catch(err) {
                    const errLine = document.createElement('div');
                    errLine.className = 'console-line';
                    errLine.innerHTML = `<span style="color:var(--error)">✖ ${escapeHtml(err.toString())}</span>`;
                    cout.appendChild(errLine);
                }
                cout.scrollTop = cout.scrollHeight;
            }
        };

        // --- Window Action ---
        async function winAction(id, action) {
            await window.inspector_window_action(id, action);
            refreshData();
        }

        // --- State Tree Renderer ---
        function renderStateTree(state) {
            const container = document.getElementById('state-tree');
            container.innerHTML = '';
            container.appendChild(createTreeNode(state, 'App.State', true));
        }

        function createTreeNode(val, key, expanded = false) {
            const div = document.createElement('div');
            const isObj = typeof val === 'object' && val !== null;
            
            const header = document.createElement('div');
            header.className = 'tree-header';
            header.innerHTML = `
                <span class="tree-toggle">${isObj ? (expanded ? '▼' : '▶') : ' '}</span>
                <span class="tree-key">${key}</span>: 
                <span class="${typeof val === 'string' ? 'tree-val-str' : ''}">${isObj ? (Array.isArray(val) ? `Array(${val.length})` : 'Object') : JSON.stringify(val)}</span>
            `;
            
            const content = document.createElement('div');
            content.className = 'tree-node';
            content.style.display = expanded ? 'block' : 'none';
            
            if(isObj) {
                header.onclick = () => {
                    const shown = content.style.display === 'block';
                    content.style.display = shown ? 'none' : 'block';
                    header.querySelector('.tree-toggle').innerText = shown ? '▶' : '▼';
                };
                for(let k in val) content.appendChild(createTreeNode(val[k], k));
            }
            
            div.appendChild(header);
            div.appendChild(content);
            return div;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Start polling
        setInterval(refreshData, 1000);
    </script>
</body>
</html>
"""
