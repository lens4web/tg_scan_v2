<?php
session_start();

// === ЗАДАЙТЕ ВАШ ПАРОЛЬ ЗДЕСЬ ===
$PASSWORD = 'admin123';

// Обработка выхода
if (isset($_GET['logout'])) {
    session_destroy();
    header("Location: " . $_SERVER['PHP_SELF']);
    exit;
}

// Обработка входа
if (isset($_POST['password'])) {
    if ($_POST['password'] === $PASSWORD) {
        $_SESSION['logged_in'] = true;
        header("Location: " . $_SERVER['PHP_SELF']);
        exit;
    } else {
        $error = "Incorrect password!";
    }
}
?>
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TG Scanner | Control Panel</title>
    <style>
        :root {
            --primary: #4F46E5;
            --primary-hover: #4338CA;
            --danger: #EF4444;
            --danger-hover: #DC2626;
            --bg: #F3F4F6;
            --card-bg: #FFFFFF;
            --text-main: #111827;
            --text-muted: #6B7280;
            --border: #E5E7EB;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: var(--bg); color: var(--text-main); line-height: 1.5; padding: 20px; }
        
        .container { max-width: 900px; margin: 0 auto; }
        
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid var(--border); }
        .header h1 { font-size: 24px; font-weight: 700; color: var(--text-main); }
        
        .card { background: var(--card-bg); border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); margin-bottom: 24px; margin-top: 2em; }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .card-header h2 { font-size: 18px; font-weight: 600; display: flex; align-items: center; gap: 10px; }
        
        label { display: block; font-size: 14px; font-weight: 600; margin-bottom: 6px; margin-top: 12px; color: #374151; }
        input[type="text"], input[type="password"], input[type="number"], textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 14px; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; transition: border-color 0.2s; margin-bottom: 4px; }
        input:focus, textarea:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1); }
        textarea { resize: vertical; min-height: 80px; }
        
        .hint { font-size: 12px; color: var(--text-muted); margin-bottom: 16px; }
        
        .btn { display: inline-flex; align-items: center; justify-content: center; padding: 10px 18px; font-size: 14px; font-weight: 600; border-radius: 8px; border: none; cursor: pointer; transition: all 0.2s; }
        .btn-primary { background-color: var(--primary); color: white; }
        .btn-primary:hover { background-color: var(--primary-hover); }
        .btn-danger { background-color: white; color: var(--danger); border: 1px solid var(--danger); padding: 6px 12px; font-size: 12px;}
        .btn-danger:hover { background-color: #FEF2F2; }
        .btn-outline { background-color: white; color: var(--primary); border: 2px dashed var(--border); width: 100%; padding: 16px; font-size: 16px; }
        .btn-outline:hover { border-color: var(--primary); background-color: #EEF2FF; }

        .actions { position: sticky; bottom: 20px; background: rgba(255, 255, 255, 0.9); padding: 16px; border-radius: 12px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); backdrop-filter: blur(8px); display: flex; justify-content: space-between; align-items: center; border: 1px solid var(--border); z-index: 100; margin-top: 2em; }
        
        .debugger { background: #1F2937; color: #10B981; font-family: monospace; padding: 16px; border-radius: 8px; font-size: 12px; max-height: 200px; overflow-y: auto; margin-top: 24px; }
        .log-error { color: #EF4444; }
        .log-info { color: #3B82F6; }

        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

        @media (max-width: 600px) {
            .card { padding: 16px; }
            .grid-2 { grid-template-columns: 1fr; }
            .header { flex-direction: column; align-items: flex-start; gap: 10px; }
            .actions { flex-direction: column; gap: 10px; text-align: center; }
            .actions .btn { width: 100%; }
        }
    </style>
</head>
<body>

<?php
// === ЕСЛИ ПОЛЬЗОВАТЕЛЬ НЕ АВТОРИЗОВАН — ПОКАЗЫВАЕМ ТОЛЬКО ФОРМУ ВХОДА ===
if (!isset($_SESSION['logged_in']) || $_SESSION['logged_in'] !== true): 
?>
<div class="container" style="max-width: 400px; margin-top: 15vh;">
    <div class="card" style="text-align: center;">
        <h2 style="margin-bottom: 20px; font-size: 20px;">🔒 TG Scanner Login</h2>
        <form method="POST">
            <input type="password" name="password" placeholder="Enter password..." required autofocus>
            <?php if (isset($error)) echo "<div style='color: var(--danger); font-size: 14px; margin-top: 10px;'>$error</div>"; ?>
            <button type="submit" class="btn btn-primary" style="width: 100%; margin-top: 20px;">Login</button>
        </form>
    </div>
</div>
</body>
</html>
<?php 
exit; // Останавливаем выполнение страницы, чтобы не загружать саму панель
endif; 
// === ЕСЛИ АВТОРИЗОВАН — ИДЕТ КОД ВАШЕЙ ПАНЕЛИ ===
?>

<div class="container">
    <div class="header">
        <h1>TG Scanner</h1>
        <div>
            <span style="font-size: 14px; color: var(--text-muted); margin-right: 15px;">Control Panel v2.1</span>
            <a href="?logout=1" style="color: var(--danger); text-decoration: none; font-size: 14px; font-weight: 600;">Log Out 🚪</a>
        </div>
    </div>

    <div class="card">
        <div class="card-header"><h2>🚫 Global Stop Words</h2></div>
        <label>Ignored across all folders (comma separated):</label>
        <textarea id="global_stop_words" placeholder="agency, ads..."></textarea>
    </div>

    <div id="folders_container"></div>

    <button class="btn btn-outline" onclick="addNewFolder()">+ Add new folder to scan</button>

    <div class="card" id="system_card">
        <div class="card-header"><h2>⚙️ System Settings</h2></div>
        
        <label>Global Notify ID (Chat/User ID for alerts):</label>
        <input type="password" id="sys_notify_id" placeholder="-100...">
        <div class="hint">Target chat for all alerts. Hidden for security.</div>

        <div class="grid-2">
            <div>
                <label>API ID:</label>
                <input type="number" id="sys_api_id" placeholder="12345678">
            </div>
            <div>
                <label>API Hash:</label>
                <input type="password" id="sys_api_hash" placeholder="abcd1234efgh5678...">
            </div>
        </div>
    </div>

    <div class="actions">
        <div id="status_msg" style="font-weight: 600; color: #059669;">Standing by...</div>
        <button class="btn btn-primary" onclick="saveConfig()">💾 Save Configuration</button>
    </div>

    <div style="margin-top: 40px;">
        <h3 style="font-size: 14px; color: var(--text-muted); margin-bottom: 8px;">🖥 Debug Log</h3>
        <div class="debugger" id="debug_log"></div>
    </div>
</div>

<script>
    const API_URL = 'api.php';
    let currentConfig = { system: {}, global_stop_words: [], folders: [] };

    function logDebug(message, type = 'normal') {
        const logBox = document.getElementById('debug_log');
        const time = new Date().toLocaleTimeString();
        let colorClass = '';
        if (type === 'error') colorClass = 'log-error';
        if (type === 'info') colorClass = 'log-info';
        
        const safeMsg = typeof message === 'object' ? JSON.stringify(message, null, 2) : message;
        logBox.innerHTML += `<div class="${colorClass}">[${time}] ${safeMsg.replace(/</g, '&lt;')}</div>`;
        logBox.scrollTop = logBox.scrollHeight;
    }

    function arrayToString(arr) {
        if (!arr) return "";
        return arr.map(item => Array.isArray(item) ? item.join(" + ") : item).join(", ");
    }

    function stringToArray(str) {
        if (!str.trim()) return [];
        return str.split(',').map(item => {
            let val = item.trim();
            if (val.includes('+')) {
                return val.split('+').map(p => p.trim()).filter(p => p !== "");
            }
            return val;
        }).filter(item => item !== "" && item.length > 0);
    }

    function renderFolders() {
        const container = document.getElementById('folders_container');
        container.innerHTML = '';
        
        currentConfig.folders.forEach((folder, index) => {
            const html = `
                <div class="card" id="folder_card_${index}">
                    <div class="card-header">
                        <h2>📁 Folder: <input type="text" id="f_name_${index}" value="${folder.folder_name || ''}" placeholder="e.g. AdB" style="width: auto; font-size: 18px; margin-left: 10px; border-color: transparent; border-bottom-color: var(--border); border-radius: 0;"></h2>
                        <button class="btn btn-danger" onclick="deleteFolder(${index})">Delete</button>
                    </div>

                    <label>Keywords (comma separated):</label>
                    <textarea id="f_keys_${index}" placeholder="rent, wifi + adapter">${arrayToString(folder.keywords)}</textarea>
                    <div class="hint">Use '+' for compound phrases: <b>wifi + adapter</b></div>

                    <label>Local Stop Words (folder specific):</label>
                    <textarea id="f_stops_${index}" placeholder="no fee">${arrayToString(folder.stop_words)}</textarea>
                </div>
            `;
            container.insertAdjacentHTML('beforeend', html);
        });
    }

    function addNewFolder() {
        currentConfig.folders.push({
            folder_name: "New_Folder",
            keywords: [],
            stop_words: []
        });
        renderFolders();
        logDebug("Added new folder to UI", "info");
    }

    function deleteFolder(index) {
        if (confirm("Delete this folder?")) {
            currentConfig.folders.splice(index, 1);
            renderFolders();
            logDebug(`Folder ${index} deleted`, "info");
        }
    }

    async function loadConfig() {
        logDebug("Fetching data from: " + API_URL, "info");
        try {
            const res = await fetch(API_URL);
            const rawText = await res.text();
            
            try {
                currentConfig = JSON.parse(rawText);
                logDebug("JSON parsed successfully.");
                
                if(currentConfig.system) {
                    document.getElementById('sys_api_id').value = currentConfig.system.api_id || '';
                    document.getElementById('sys_api_hash').value = currentConfig.system.api_hash || '';
                    document.getElementById('sys_notify_id').value = currentConfig.system.notify_id || '';
                }

                document.getElementById('global_stop_words').value = arrayToString(currentConfig.global_stop_words);
                
                if (!currentConfig.folders) currentConfig.folders = [];
                renderFolders();
                
                document.getElementById('status_msg').innerText = "✅ Data loaded";
            } catch (parseError) {
                logDebug("JSON PARSE ERROR!", "error");
                logDebug("Server returned:", "error");
                logDebug(rawText, "error");
                document.getElementById('status_msg').innerHTML = "<span style='color:red'>Server Error. See log.</span>";
            }
        } catch (e) {
            logDebug("Network error: " + e.message, "error");
        }
    }

    async function saveConfig() {
        document.getElementById('status_msg').innerText = "⏳ Saving...";
        logDebug("Collecting data...", "info");
        
        try {
            const notifyVal = document.getElementById('sys_notify_id').value.trim();
            
            currentConfig.system = {
                // Имя сессии фиксируем жестко (согласно вашему предыдущему удалению поля из HTML)
                session_name: currentConfig.system.session_name || "my_account",
                api_id: Number(document.getElementById('sys_api_id').value),
                api_hash: document.getElementById('sys_api_hash').value.trim(),
                notify_id: notifyVal ? Number(notifyVal) : ""
            };

            currentConfig.global_stop_words = stringToArray(document.getElementById('global_stop_words').value);
            
            currentConfig.folders.forEach((folder, index) => {
                const fname = document.getElementById(`f_name_${index}`);
                if (fname) folder.folder_name = fname.value.trim();

                const fkeys = document.getElementById(`f_keys_${index}`);
                if (fkeys) folder.keywords = stringToArray(fkeys.value);
                
                const fstops = document.getElementById(`f_stops_${index}`);
                if (fstops) folder.stop_words = stringToArray(fstops.value);
                
                if (folder.notify_id !== undefined) {
                    delete folder.notify_id;
                }
            });

            logDebug("Sending POST request...", "info");
            
            const res = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(currentConfig)
            });
            
            const rawText = await res.text();
            
            try {
                const result = JSON.parse(rawText);
                if (result.success) {
                    logDebug("Success: " + result.message);
                    document.getElementById('status_msg').innerText = '✅ Saved successfully!';
                } else {
                    logDebug("API Error: " + result.error, "error");
                    document.getElementById('status_msg').innerHTML = "<span style='color:red'>" + result.error + "</span>";
                }
            } catch (e) {
                logDebug("SAVE ERROR: Server returned non-JSON:", "error");
                logDebug(rawText, "error");
                document.getElementById('status_msg').innerHTML = "<span style='color:red'>Server Error. See log.</span>";
            }
            
        } catch (e) {
            logDebug("Critical save error: " + e.message, "error");
        }
    }

    window.onload = loadConfig;
</script>

</body>
</html>