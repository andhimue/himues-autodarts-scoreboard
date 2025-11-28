// Frontend/static/js/spielmodi/view_x01.js

/**
 * Helper für die neue Last-Turn Anzeige.
 */
/**
 * definiert, welche Tabellenzellen zusätzlich bei der Tabellenanzeige bei X01 dargestellt werden sollen
 * wird als Paramater an renderGameTable() übergeben
 */
const x01TableConfig = [
    // Wir nutzen wieder die Standard-Source für Punkte
    { selector: '.game-table__cell--score', source: player => player.score },
    // Die dedizierte Last-Turn-Spalte
    { selector: '.game-table__cell--last-turn', html: player => createLastTurnHtml(player) },
    
    { selector: '.game-table__cell--avg-g', html: player => createOverallAverageHtml(player, 'overall_average', true) },
    { selector: '.game-table__cell--avg-m', source: player => formatAverage(player.match_average) },
    { selector: '.game-table__cell--avg-l', source: player => formatAverage(player.leg_average) }
];

//------------------------------------------------------------------

/**
 * definiert, welche Elemente zusätzlich auf der Playercard bei X01 dargestellt werden sollen
 * wird als Paramater an renderPlayerCards() übergeben
 */
const x01CardConfig = [
    // Bei der Karte packen wir LastTurn mangels Platz in eine Zeile darunter oder ignorieren es
    // Hier: Wir fügen es in den neuen Platzhalter ein
    { selector: '.player-card__last-turn', html: player => createLastTurnHtml(player, true) },
    
    { selector: '.player-card__avg-value--g', html: player => createOverallAverageHtml(player, 'overall_average', true) },
    { selector: '.player-card__avg-value--m', source: player => formatAverage(player.match_average) },
    { selector: '.player-card__avg-value--l', source: player => formatAverage(player.leg_average) }
];

//------------------------------------------------------------------

/**
 * Helper für die neue Last-Turn Anzeige.
 */
function createLastTurnHtml(player, Card=false) {
    const score = player.last_turn_score;
    const darts = player.last_turn_darts || '';
    
    // Wenn kein Score da ist, zeigen wir ein leeres Feld oder einen Strich
    if (score === null || score === undefined) {
        return '<span style="color: #444;">-</span>';
    }

    if (Card) {
    return `
        <div class="x01-last-turn-container">
            <span class="x01-last-turn-score">Last: ${score}</span>
            <span class="x01-last-turn-darts">${darts}</span>
        </div>
    `;
    } else {
        return `
        <div class="x01-last-turn-container">
            <span class="x01-last-turn-score">${score}</span>
            <span class="x01-last-turn-darts">${darts}</span>
        </div>
    `;
    }
}

//------------------------------------------------------------------


/**
 * @summary Aktualisiert die komplette Ansicht für den Spielmodus "X01".
 * Wird von der updateDisplay()-Funktion aufgerufen.
 */
 
function updateX01View(viewModel) {
    const { match, checkout_guide, players, current_player_index } = appState;

    viewModel.details.gamemode.text = `X${match.start_score}`;
    viewModel.darts.checkoutGuide = checkout_guide || [];
    
    renderFocusArea(viewModel);

    // Standardwert ist die Tabellenanzege
    let displayMode = 'table'
    // Hole den Standardwert aus der Jinja2-Konstante
    if (typeof SHOW_PLAYER_CARD === 'undefined' || SHOW_PLAYER_CARD) displayMode = 'card';
    
    if (URL_PARAMS.has('xc')){
        displayMode = 'cards';
    } else if (URL_PARAMS.has('xt')){
        displayMode = 'table';
    }

    // --- Logik für Sichtbarkeit der Last-Turn Anzeige ---
    // 1. Standard aus Config
    let showLastPoints = (typeof SHOW_LAST_POINTS_CONFIG !== 'undefined') ? SHOW_LAST_POINTS_CONFIG : true;
    
    // 2. URL-Parameter Override
    if (URL_PARAMS.has('sl')) { // Show Last
        showLastPoints = true;
    } else if (URL_PARAMS.has('nl')) { // No Last
        showLastPoints = false;
    }

    if (displayMode === 'table') {
        UI.x01CardContainer.hide();
        UI.x01Table.show();
        renderGameTable(UI.x01Table, '#x01-table-row-template', players, current_player_index, x01TableConfig);

        // Spalte ein-/ausblenden basierend auf Config/URL
        toggleTableColumn('#x01-table', 'last-turn', showLastPoints);
    } else {
        UI.x01Table.hide();
        UI.x01CardContainer.show();
        renderPlayerCards(UI.x01CardContainer, '#x01-player-card-template', players, current_player_index, x01CardConfig);

        // Element in Karte ein-/ausblenden
        if (showLastPoints) {
            $('.player-card__last-turn').show();
        } else {
            $('.player-card__last-turn').hide();
        }
    }

    // Spalte für Gesamt-Average ein-/ausblenden
    const useDB = appState.match.use_db;
    toggleTableColumn('#x01-table', 'avg-g', useDB);

}