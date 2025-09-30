$(document).ready(function() {
    const socket = io();
    let dashboardInterval = null;

    // --- Hilfsfunktionen zum Senden von Befehlen (unverändert) ---
    const commandCallbacks = {};
    let commandId = 0;
    function sendCommand(action, params, callback) {
        if (socket && socket.connected) {
            commandId++;
            if (callback) commandCallbacks[commandId] = callback;
            socket.emit('command', { action, params, callback_id: commandId });
        } else if (callback) {
            callback({ error: "Socket ist nicht verbunden." });
        }
    }
    socket.on('command_response', (response) => {
        const { callback_id, data } = response;
        if (commandCallbacks[callback_id]) {
            commandCallbacks[callback_id](data);
            delete commandCallbacks[callback_id];
        }
    });

    // --- Verbindungshandler (unverändert) ---
    socket.on('connect', () => {
        console.log('Verbunden mit dem Backend-Server!');
        startDashboardInterval();
    });

    socket.on('disconnect', () => {
        console.log('Verbindung zum Backend verloren!');
        stopDashboardInterval();
    });

    // --- Aktions-Buttons (unverändert) ---
    $('#start-board-btn').on('click', () => sendCommand('start_board'));
    $('#stop-board-btn').on('click', () => sendCommand('stop_board'));
    $('#reset-board-btn').on('click', () => sendCommand('reset_board'));
    $('#calibrate-board-btn').on('click', () => sendCommand('calibrate_board'));

    /**
     * @summary Ruft alle benötigten Daten vom Backend ab und aktualisiert die Tabelle.
     */
    function updateDashboard() {
        // Führe alle 5 Anfragen parallel aus
        const configPromise = new Promise(resolve => sendCommand('get_config', {}, resolve));
        const statsPromise = new Promise(resolve => sendCommand('get_stats', {}, resolve));
        const camsStatePromise = new Promise(resolve => sendCommand('get_cams_state', {}, resolve));
        const boardAddressPromise = new Promise(resolve => sendCommand('get_board_address', {}, resolve));
        const camsStatsPromise = new Promise(resolve => sendCommand('get_cams_stats', {}, resolve)); // HIER: Der fehlende Aufruf

        // Warte, bis alle 5 Antworten da sind
        Promise.all([configPromise, statsPromise, camsStatePromise, boardAddressPromise, camsStatsPromise]).then((results) => {
            const [config, stats, camsState, boardAddress, camsStats] = results;
            renderTable(config, stats, camsState, boardAddress, camsStats);
        });
    }

    /**
     * @summary Zeichnet die HTML-Tabelle mit den gesammelten Daten.
     */
    function renderTable(config, stats, camsState, boardAddress, camsStats) {
        const tableBody = $('#dashboard-table');
        if (!config || !stats || !camsState || !boardAddress || !camsStats) {
            tableBody.html('<tbody><tr><td>Lade Daten...</td></tr></tbody>');
            return;
        }

        const formatBool = (value) => value ? '<span class="status-true">Ja</span>' : '<span class="status-false">Nein</span>';
        const fullAddress = boardAddress.board_manager_address || 'N/A';
        const linkHtml = fullAddress !== 'N/A' ? `<a href="${fullAddress}" target="_blank" style="color: #8ab4f8;">${fullAddress}</a>` : 'N/A';

        let html = '<tbody>';
        
        // --- ALLGEMEINE INFORMATIONEN ---
        html += `<tr><td>Board ID</td><td>${config.auth?.board_id || 'N/A'}</td></tr>`;
        html += `<tr><td>Host IP:Port</td><td>${linkHtml}</td></tr>`;
        // HIER: Verwende die genauere Auflösung aus cams_stats
        html += `<tr><td>Auflösung (B x H)</td><td>${camsStats.resolution?.width || 'N/A'} x ${camsStats.resolution?.height || 'N/A'}</td></tr>`;
        
        // --- FPS-WERTE ---
        html += `<tr><td>Max. FPS</td><td>${config.cam?.fps_max || 'N/A'}</td></tr>`;
        html += `<tr><td>Durchschnitts-FPS</td><td>${stats.fps?.toFixed(1) || 'N/A'}</td></tr>`;

        // --- KAMERA-TABELLE ---
        const numCams = config.cam?.cams?.length || 0;
        for (let i = 0; i < numCams; i++) {
            // HIER: Greife auf das fps-Array aus dem camsStats-Objekt zu
            const camFps = camsStats.fps?.[i] ?? '0';
            const isRotated = config.cam?.rotate_180?.[i] ?? false;
            const camDevice = config.cam?.cams?.[i] || `Kamera ${i}`;
            html += `<tr>
                        <td>${camDevice}</td>
                        <td>${camFps} FPS / Rotiert: <span class="status-true">${isRotated ? 'Ja' : 'Nein'}</span></td>
                     </tr>`;
        }
        
        // --- ZUSTAND & EINSTELLUNGEN ---
        html += `<tr><td>Kameras geöffnet</td><td>${formatBool(camsState.isOpened)}</td></tr>`;
        html += `<tr><td>Kameras aktiv</td><td>${formatBool(camsState.isRunning)}</td></tr>`;
        html += `<tr><td>Standby-Minuten</td><td>${config.motion?.standby_minutes || 'N/A'}</td></tr>`;
        html += `<tr><td>Kalibrierung bei Start</td><td>${formatBool(config.cam?.auto_calibrate_on_start)}</td></tr>`;
        html += `<tr><td>Kalibrierung bei Kamera-Änderung</td><td>${formatBool(config.cam?.auto_calibrate)}</td></tr>`;
        html += `<tr><td>Auto-Distortion</td><td><span class="status-true">${config.cam?.auto_distortion ? 'Ja' : 'Nein'}</span></td></tr>`;

        html += '</tbody>';
        tableBody.html(html);
    }
    
    function startDashboardInterval() {
        stopDashboardInterval();
        updateDashboard(); // Einmal sofort ausführen
        dashboardInterval = setInterval(updateDashboard, 1000); // Dann jede Sekunde
    }

    function stopDashboardInterval() {
        clearInterval(dashboardInterval);
    }
});