// Frontend/static/js/spielmodi/view_countup.js

/**
 * definiert, welche Tabellenzellen zus�tzlich bei der Tabellenanzeige bei Count Up dargestellt werden sollen
 * wird als Paramater an renderGameTable() �bergeben
 */

const countUpTableConfig = [
    { selector: '.game-table__cell--avg-g', html: p => createOverallAverageHtml(p, 'overall_ppr', false) },
    { selector: '.game-table__cell--leg-avg',   source: player => parseFloat(player.leg_average || 0).toFixed(2) },
    { selector: '.game-table__cell--match-avg', source: player => parseFloat(player.match_average || 0).toFixed(2) }
];

/**
 * @summary Aktualisiert die komplette Ansicht f�r den Spielmodus "Count Up".
 * Wird von der updateDisplay()-Funktion aufgerufen.
 */

function updateCountUpView(viewModel) {
    const { players, current_player_index } = appState;
    
    renderFocusArea(viewModel);
    renderGameTable('#countup-table', '#countup-row-template', players, current_player_index, countUpTableConfig);

    const useDB = appState.match.use_db;
    toggleTableColumn('#countup-table', 'avg-g', useDB);

}