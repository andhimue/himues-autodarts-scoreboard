// Frontend/static/js/scoreboard_helpers.js


// Hält die einmal erstellte Instanz der Fireworks-Bibliothek
let isDisplayActive = false;
let fireworksInstance = null;

//------------------------------------------------------------------

/**
 * @summary Initialisiert die Fireworks.js-Bibliothek genau einmal ("lazy").
 * Gibt bei nachfolgenden Aufrufen die bereits erstellte Instanz zurück.
 * @returns {object|null} Die Fireworks-Instanz oder null.
 */
function _initializeFireworks() {
    // Wenn die Instanz schon existiert, gib sie einfach zurück.
    if (fireworksInstance) {
        return fireworksInstance;
    }

    // Führe die Initialisierung nur aus, wenn die Canvas-Variante genutzt wird.
    if (!USE_VIDEO_FIREWORKS && UI.fireworksCanvas.length) {
        fireworksInstance = new Fireworks.default(UI.fireworksCanvas[0], {
            autoresize: true,
            opacity: 0.5,
            acceleration: 1.05,
            friction: 0.97,
            gravity: 1.5,
            particles: 75,
            traceSpeed: 5,
            explosion: 5,
            intensity: 40,
            hue: { min: 0, max: 360 },
            mouse: { click: false, move: false, max: 1 }
        });
    }
    return fireworksInstance;
}

//------------------------------------------------------------------

/**
 * @summary Steuert die Sichtbarkeit der initialen Ansicht und des Haupt-Containers.
 * Startet die Anzeige automatisch, wenn ein Spiel beginnt.
 */
function _handleInitialViewAndAutoStart() {
    const gameIsActive = appState.players && appState.players.length > 0;

    UI.initialView.toggle(!gameIsActive);
    
    // Wenn ein Spiel aktiv ist, die Anzeige aber noch nicht manuell gestartet wurde...
    if (gameIsActive && !isDisplayActive) {
        isDisplayActive = true; // Zustand auf "aktiv" setzen
        UI.mainContainer.css('display', 'flex'); // Anzeige einblenden
    }
}

//------------------------------------------------------------------

/**
 * @summary Zeigt das Overlay für den Gewinner eines Legs, Sets oder Matches an.
 */
function _displayWinner(fireworks) {
    const { players, match, game_state, winner_info } = appState;
    const winner = players.find(p => p.name === appState.winner_info.player);
    if (!winner) return;

    const winnerNameHtml = `<span class="winner-name">${winner.name}</span>`;
    let messageType = 'Leg'; // Standardwert


    if (game_state === 'match_won' || (match.sets_to_win > 0 && winner.sets_won === match.sets_to_win)) {
        messageType = 'Match';
    } else if (match.sets_to_win > 0 && winner.legs_won === 0) {
        messageType = 'Set';
    } else if (winner_info.type === 'Bull-off') {
            messageType = 'Ausbullen';
    }

    UI.winnerTitle.html(winnerNameHtml);
    UI.winnerPlayer.html(`gewinnt das ${messageType}`);

    // Dynamische Klassen für die Farbgebung setzen
    UI.winnerPlayer.removeClass('win-type--leg win-type--set win-type--match');
    UI.winnerOverlay.removeClass('set-win-bg');
    if (winner_info.type === 'Bull-off') {
        UI.winnerPlayer.addClass(`win-type--bull`);
    } else {
        UI.winnerPlayer.addClass(`win-type--${messageType.toLowerCase()}`);
    }
    
    if (messageType === 'Set') {
        UI.winnerOverlay.addClass('set-win-bg');
    }
    
    UI.winnerOverlay.show();
    UI.gameContent.hide();

    if (game_state === 'match_won') {
        _triggerFireworks(fireworks);
    }
}

//------------------------------------------------------------------

/**
 * @summary Zeigt das Overlay für das spezifische Spielende von "Bob's 27" an.
 */
function _displayBobs27EndState() {
    const { game_state, players } = appState;
    if (game_state === 'busted') {
        UI.winnerTitle.text("Bob's 27 Verloren");
        UI.winnerPlayer.text("Punktestand ist unter 1 gefallen");
    } else { // game_over
        UI.winnerTitle.text("Bob's 27 Beendet");
        const finalScore = players.length > 0 ? players[0].score : 'N/A';
        UI.winnerPlayer.text(`Finaler Punktestand: ${finalScore}`);
    }
    UI.winnerOverlay.show();
    UI.gameContent.hide();
}

//------------------------------------------------------------------

/**
 * @summary Zeigt das Overlay für ein Unentschieden beim Ausbullen an.
 */
function _displayBullOffTie() {
    UI.winnerTitle.text("Unentschieden!");
    UI.winnerPlayer.text("Das Ausbullen wird wiederholt.");
    UI.winnerOverlay.addClass('tie-bg').show();
    UI.gameContent.hide();
}

//------------------------------------------------------------------

/**
 * @summary Startet die passende Feuerwerk-Animation (Video oder Canvas).
 */
function _triggerFireworks(fireworks) {
    if (USE_VIDEO_FIREWORKS) {
        UI.fireworksVideo.show();
        UI.fireworksVideo.get(0).play();
    } else if (fireworks) {
        UI.fireworksCanvas.show();
        fireworks.start();
    } else {
        console.error("FEHLER: Canvas-Feuerwerk sollte starten, aber die Instanz ist null oder undefined!");
    }
}

//------------------------------------------------------------------

/**
 * @summary Stoppt alle laufenden Feuerwerk-Animationen.
 */
function _stopFireworks(fireworks) {
    if (USE_VIDEO_FIREWORKS) {
        UI.fireworksVideo.get(0).pause();
        UI.fireworksVideo.hide();
    } else if (fireworks && fireworks.running) {
        fireworks.stop();
        UI.fireworksCanvas.hide();
    }
}

//------------------------------------------------------------------

/**
 * @summary Speichert die neuesten Daten vom Server im globalen appState.
 * @param {object} data Der komplette Spielzustand vom Backend.
 */
 
function _cacheLatestServerState(data) {
    appState = data;
}

//------------------------------------------------------------------

/**
 * @summary Zeichnet die gesamte Spielansicht (Tabellen, Fokus-Bereich etc.) neu,
 * basierend auf dem aktuellen globalen appState. Agiert als Router.
 */
 
function _routeToGameViewUpdater() {
    // Liest Informationen aus dem globalen appState
    const players = appState.players || [];
    const mode = appState.match ? appState.match.game_mode : null;
    console.log(backendConnected ? "verbunden" : "nicht verbunden")
    if (backendConnected) {
        if (players.length > 0) {
            UI.statusMessage.hide();
            UI.mainContainer.css('display', 'flex');
            UI.gameDetails.show();

            // Leere den Grafik-Container bei JEDEM Update, um alte Grafiken zu entfernen.
            UI.focusSegmentGraphic.empty();

            // Das ViewModel wird hier ZENTRAL erstellt
            const viewModel = createBaseViewModel();

            // 1. Alle Ansichts-Container ausblenden
            for (const key in VIEW_HANDLERS) {
                $(VIEW_HANDLERS[key].container).hide();
            }

            // 2. Den passenden Handler für den aktuellen Spielmodus finden
            const handler = VIEW_HANDLERS[mode];

            if (handler) {
                // 3. Nur den korrekten Container anzeigen und die zugehörige Update-Funktion aufrufen
                $(handler.container).show();
                // Das ViewModel wird als Parameter ÜBERGEBEN. Weitere Daten liest die Funktion aus appState
                handler.updater(viewModel);
            } else {
                // Fallback für nicht unterstützte Modi
                UI.statusMessage.text(`Spielmodus '${mode}' wird nicht unterstützt.`).show();
            }
        } else {
            // Logik, wenn kein Spiel aktiv ist (bleibt unverändert)
    //        UI.statusMessage.text('Warte auf ein neues Match...').show();
    //        UI.mainContainer.hide();
    //        UI.gameDetails.hide();
    //        UI.bustOverlaysContainer.hide();
    //        UI.initialView.show();
            // Logik für KEIN aktives Spiel (Zustand 2)
            UI.mainContainer.hide();
            UI.initialView.show();

            // Setzt die finale Statusmeldung, wenn alles verbunden ist und kein Spiel läuft.
            UI.statusMessage.text('Verbunden! Warte auf Match...').show();

        }
    } else {
        //backend nicht verbunden
        _BackendOffline()
    }
}

//------------------------------------------------------------------

function _BackendOffline() {
    UI.mainContainer.hide();

    // 2. Setze den globalen Zustand zurück, um einen sauberen Neustart zu gewährleisten.
    appState = {};

    // 3. Zeige den Startbildschirm mit der Fehlermeldung an.
    UI.initialView.show();
    UI.statusMessage.text('Verbindung zum Backend verloren. Versuche Neuverbindung...');
    UI.statusMessage.show(); // Sicherstellen, dass die Statuszeile sichtbar ist

    // 4. Blende die (jetzt veraltete) Liste der Spielmodi aus.
    UI.modesOverview.hide();

    // 5. Stoppe sicherheitshalber alle Animationen
    //_stopFireworks(_initializeFireworks());
    _stopFireworks(fireworksInstance);

}

//------------------------------------------------------------------

    /**
     * @summary Verarbeitet Events wie Match-Start/-Ende, Gewinner-Anzeige oder Busts.
     * Diese Funktion kümmert sich um alles, was nicht direkt die Spielstandsanzeige betrifft.
     * Analysiert den Spielzustand und ruft die passende Hilfsfunktion
     * zur Anzeige von Overlays, Gewinner-Nachrichten und anderen Benachrichtigungen auf.
    */
    function _processGameNotifications() {
        const fireworks = _initializeFireworks();

        _handleInitialViewAndAutoStart();

        const { game_state, match } = appState;
        const gameMode = match ? match.game_mode : null;

        // Setzt Overlays und Hintergründe für jeden normalen Wurf zurück
        UI.winnerOverlay.hide().removeClass('tie-bg');
        UI.gameContent.show();
        _stopFireworks(fireworks); // Stellt sicher, dass Feuerwerk immer gestoppt wird

        // Dispatcher, der die passende Funktion für den aktuellen Zustand aufruft
        if (gameMode === "Bob's 27" && (game_state === 'game_over' || game_state === 'busted')) {
            _displayBobs27EndState();
        } else if (game_state === 'leg_won' || game_state === 'match_won') {
            _displayWinner(fireworks);
        } else if (game_state === 'bull_off_tie') {
            _displayBullOffTie();
        }
    }

//------------------------------------------------------------------

/**
 * @summary Initialisiert den Startbildschirm. Füllt die Liste der Spielmodi
 * und registriert die Event-Listener für den Start-Button und den Vollbildmodus.
 */
function _setupInitialScreen() {
    // Füllt die Liste der verfügbaren Spielmodi auf dem Startbildschirm.
    if (typeof SUPPORTED_GAME_MODES !== 'undefined' && SUPPORTED_GAME_MODES.length > 0) {
        UI.modesLabel.text("Verfügbare Modi:");
        UI.modesList.empty(); // Vorherigen Inhalt leeren
        UI.statusMessage.text('Verbunden! Warte auf Match...');
        SUPPORTED_GAME_MODES.forEach(mode => {
            const modeElement = $('<span>').addClass('game-mode-item').text(mode);
            UI.modesList.append(modeElement);
        });
        
        UI.modesOverview.show();
     }

    // --- Event-Handler für UI-Interaktionen ---
    UI.startButton.on('click', function() {
        isDisplayActive = true; // Zustand auf "aktiv" setzen
        UI.mainContainer.css('display', 'flex').hide();
        
        // Vollbild-Logik
        const elem = document.documentElement;
        if (elem.requestFullscreen) { elem.requestFullscreen(); }
        else if (elem.mozRequestFullScreen) { elem.mozRequestFullScreen(); }
        else if (elem.webkitRequestFullscreen) { elem.webkitRequestFullscreen(); }
        else if (elem.msRequestFullscreen) { elem.msRequestFullscreen(); }
    });

    document.addEventListener('fullscreenchange', () => {
        UI.body.toggleClass('hide-cursor', !!document.fullscreenElement);
    });
}
