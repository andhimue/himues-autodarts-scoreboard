// Frontend/static/js/spielmodi/view_x01.js

/**
 * definiert, welche Tabellenzellen zusätzlich bei der Tabellenanzeige bei X01 dargestellt werden sollen
 * wird als Paramater an renderGameTable() übergeben
 */
const x01TableConfig = [
    // KORREKTUR: 'true' wird explizit übergeben, um die Icons zu aktivieren
    { selector: '.game-table__cell--avg-g',       html: player => createOverallAverageHtml(player, 'overall_average', true) },
    { selector: '.game-table__cell--avg-m', source: player => formatAverage(player.match_average) },
    { selector: '.game-table__cell--avg-l', source: player => formatAverage(player.leg_average) }
];

//------------------------------------------------------------------

/**
 * definiert, welche Elemente zusätzlich auf der Playercard bei X01 dargestellt werden sollen
 * wird als Paramater an renderPlayerCards() übergeben
 */
const x01CardConfig = [
    // KORREKTUR: 'true' wird explizit übergeben, um die Icons zu aktivieren
    { selector: '.player-card__avg-value--g', html: player => createOverallAverageHtml(player, 'overall_average', true) },
    { selector: '.player-card__avg-value--m', source: player => formatAverage(player.match_average) },
    { selector: '.player-card__avg-value--l', source: player => formatAverage(player.leg_average) }
];

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

    // Standardwert ist die TAbellenanzege
    let displayMode = 'table'
    // Hole den Standardwert aus der Jinja2-Konstante
    if (typeof SHOW_PLAYER_CARD === 'undefined' || SHOW_PLAYER_CARD) displayMode = 'card';
    
    if (URL_PARAMS.has('xc')){
        displayMode = 'cards';
    } else if (URL_PARAMS.has('xt')){
        displayMode = 'table';
    }

console.log(displayMode)

    if (displayMode === 'table') {
        UI.x01CardContainer.hide();
        UI.x01Table.show();
        renderGameTable(UI.x01Table, '#x01-table-row-template', players, current_player_index, x01TableConfig);
    } else {
        UI.x01Table.hide();
        UI.x01CardContainer.show();
        renderPlayerCards(UI.x01CardContainer, '#x01-player-card-template', players, current_player_index, x01CardConfig);
    }

    // Spalte für Gesamt-Average ein-/ausblenden
    const useDB = appState.match.use_db;
    toggleTableColumn('#x01-table', 'avg-g', useDB);

}

