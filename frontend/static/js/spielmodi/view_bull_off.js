// Frontend/static/js/spielmodi/view_bull_off.js

/**
 * @summary Aktualisiert die komplette Ansicht für den Spielmodus "Bull-Off".
 * Wird von der updateDisplay()-Funktion aufgerufen.
 */

const bullOffTableConfig = [
    { selector: '.game-table__cell--player-name', source: player => player.name },
    { selector: '.game-table__cell--score',       source: player => player.score }
];

/**
 * @summary Aktualisiert die komplette Ansicht für den Spielmodus "Bull-Off".
 * Obwohl das ja ein Auswahlspiel für den Startspieler bei 2 Spielern ist,
 * wird das als eigener Game-Modus behandelt, der VOR dem eigenlichen Spiel aufgerufen wird.
 * Wird von der updateDisplay()-Funktion aufgerufen.
 */

function updateBullOffView(viewModel) {
    const { players, current_player_index } = appState;

    viewModel.focus.score.text = "Ausbullen";
    viewModel.darts.visible = false;
    viewModel.details.gamemode.visible = false;
    renderFocusArea(viewModel);
    renderGameTable('#bull-off-table', '#bull-off-row-template', players, current_player_index, bullOffTableConfig);
}