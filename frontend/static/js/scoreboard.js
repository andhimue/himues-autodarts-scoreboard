// Frontend/static/js/scoreboard.js

/**
 * @summary Das globale State-Objekt. Enthält immer den letzten, vollständigen
 * Spielzustand, der vom Server gesendet wurde. Dient als "Single Source of Truth".
 */
 
let appState = {};              // Das zentrale State-Objekt
let backendConnected = false;

let playerOrder = [];

let socket = null;

//--------------------------------------------------------------------

// Befüllt das globale UI-Objekt mit Referenzen auf alle benötigten DOM-Elemente.
// Dies geschieht einmalig, um die Performance zu verbessern und die Wartbarkeit zu erhöhen.

Object.assign(UI, {
   
    // Globale Elemente
    fireworksCanvas: $('#fireworks-canvas'),
    fireworksVideo: $('#fireworks-video'),
    body: $('body'),

    // Initial-Ansicht
    initialView: $('#initial-view'),
    startButton: $('#initial-view__start-button'),
    statusMessage: $('#initial-view__status'),
    modesOverview: $('#initial-view__modes'),
    modesLabel: $('#initial-view__modes-label'),
    modesList: $('#initial-view__modes-list'),

    // --- Haupt-Container für das Spiel ---
    mainContainer: $('#main-container'),
    gameSpecificArea: $('#game-specific-area'),

    // --- Info-Bereich (oberer Block) & dessen Overlays ---
    infoArea: $('#info-area'),
    gameContent: $('#info-area__content'),
    winnerOverlay: $('#info-area__overlay--winner'),
    winnerTitle: $('#info-area__overlay-title'),
    winnerPlayer: $('#info-area__overlay-text'),
    bustOverlaysContainer: $('#bust-overlay-container'),
    bustOverlayLeft: $('#bust-overlay-left'),
    bustOverlayRight: $('#bust-overlay-right'),

    // --- Details & Fokus innerhalb des Info-Bereichs ---
    gameDetails: $('#info-area__details'),
    gameModeDisplay: $('#info-area__details-gamemode'),
    gameRulesDisplay: $('#info-area__details-gamerules'),
    
    focusArea: $('#info-area__focus'),
    focusPlayerName: $('#info-area__focus-player-name'),
    focusScore: $('#info-area__focus-score'),
    focusScoreLabel: $('#info-area__focus-score-label'),
    focusSegmentGraphic: $('#info-area__focus-graphic'),
    dartsDisplay: $('#info-area__darts'),
       

    // --- Spezifische Container für X01/Gotcha (falls noch benötigt) ---
    x01CardContainer: $('#x01-view-container .player-cards-section'),
    x01Table: $('#x01-table'),
    gotchaCardContainer: $('#gotcha-view-container .player-cards-section'),
    gotchaTable: $('#gotcha-table'),
    cricketTable: $('#cricket-table'),
    tacticsTable: $('#tactics-table')

});

//--------------------------------------------------------------------

/**
 * @summary Der Dispatcher für die Ansichten. Mappt einen Spielmodus-Namen
 * auf die zuständige Update-Funktion und den Container.
 */
 
 const VIEW_HANDLERS = {
    'X01':              { updater: updateX01View,               container: '#x01-view-container' },
    'Cricket':          { updater: updateCricketView,           container: '#cricket-view-container' },
    'Tactics':          { updater: updateCricketView,           container: '#cricket-view-container' },
    'Bermuda':          { updater: updateBermudaView,           container: '#bermuda-view-container' },
    'Shanghai':         { updater: updateShanghaiView,          container: '#shanghai-view-container' },
    'Gotcha':           { updater: updateGotchaView,            container: '#gotcha-view-container' },
    'ATC':              { updater: updateATCView,               container: '#atc-view-container' },
    'RTW':              { updater: updateRTWView,               container: '#rtw-view-container' },
    'Random Checkout':  { updater: updateRandomCheckoutView,    container: '#random-checkout-view-container' },
    'Bull-off':         { updater: updateBullOffView,           container: '#bull-off-view-container' },
    'CountUp':          { updater: updateCountUpView,           container: '#countup-view-container' },
    'Segment Training': { updater: updateSegmentTrainingView,   container: '#segment-training-view-container' },
    "Bob's 27":         { updater: updateBobs27View,            container: '#bobs27-view-container' }
};

//--------------------------------------------------------------------

/**
 * @summary Haupt-Initialisierungsfunktion, die nach dem Laden des DOMs ausgeführt wird.
 */
 
 $(document).ready(function() {
    
    // --- Socket.IO Event-Handler ---
    socket = io();

    // Initiales UI-Setup wird an die Hilfsfunktion delegiert
    _setupInitialScreen();

    //-------------------------------------------------------------

    socket.on('connect', () => {
        console.log('Erfolgreich mit dem Flask-SocketIO-Server verbunden!');
        // Zeigt an, dass das Frontend nun versucht, das Backend zu erreichen.
    });

    socket.on('connect_error', (err) => {
        console.error('Verbindungsfehler zum Flask-SocketIO-Server:', err);
        UI.statusMessage.text('Verbindungsfehler zum Frontend-Server!');
    });

    //-------------------------------------------------------------

    socket.on('backend_connected', (data) => {
        console.info("backend_connected")
        // Sobald dieses Event vom Frontend-Server kommt, wissen wir,
        // dass die Verbindung zum Backend steht und die Daten da sind.
        backendConnected = true

        UI.statusMessage.text('Verbunden! Warte auf Match...');

        // 2. Füllt die Spielmodi und rendert die Liste neu
        if (data && data.modes) {
            // Die globale JS-Variable wird aktualisiert
            SUPPORTED_GAME_MODES.length = 0; // Leert das Array
            Array.prototype.push.apply(SUPPORTED_GAME_MODES, data.modes);
            
            // Die Funktion zum Neuzeichnen der Liste wird aufgerufen
            _setupInitialScreen();
        }
    });
    
    //-------------------------------------------------------------

    socket.on('backend_disconnected', () => {
        console.info("backend_disconnected")
        console.warn('Vom Frontend-Server gemeldet: Verbindung zum Backend verloren!');

        backendConnected = false

        _BackendOffline()

    });


    //-------------------------------------------------------------

    /**
     * @summary Der zentrale Einstiegspunkt, wenn ein Update vom Server kommt.
     * Orchestriert den gesamten Update-Prozess.
     */
    socket.on('status_update', (data) => {
        console.log('Neuer Status vom Server empfangen:', data);

        // SCHRITT 1: Immer zuerst den globalen Zustand aktualisieren
        _cacheLatestServerState(data);
        
        // SCHRITT 2: Auf spezielle Events reagieren (Overlays, Feuerwerk, etc.)
        _processGameNotifications();
        
        // SCHRITT 3: Den finalen Zustand auf dem Bildschirm zeichnen
        _routeToGameViewUpdater();
    });

});

//------------------------------------------------------------------


