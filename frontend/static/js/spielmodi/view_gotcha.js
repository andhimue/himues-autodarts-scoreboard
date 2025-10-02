// Frontend/static/js/spielmodi/view_gotcha.js

/**
 * @summary Aktualisiert die komplette Ansicht für den Spielmodus "Gotcha".
 * Wird von der updateDisplay()-Funktion aufgerufen.
 */

function updateGotchaView(viewModel) {
    const { match, players, current_player_index } = appState;

    viewModel.details.gamemode.text = `${match.game_mode} ${match.start_score}`;
    renderFocusArea(viewModel);

     // Standardwert ist die TAbellenanzege
    let displayMode = 'table'
    // Hole den Standardwert aus der Jinja2-Konstante
    if (typeof SHOW_PLAYER_CARD === 'undefined' || SHOW_PLAYER_CARD) displayMode = 'card';
    
    if (URL_PARAMS.has('xc')){
        displayMode = 'cards';
    } else if (URL_PARAMS.has('xt')) {
        displayMode = 'table';
    }

    if (displayMode === 'table') {
        UI.gotchaCardContainer.hide();
        UI.gotchaTable.show();
        renderGameTable(UI.gotchaTable, '#gotcha-table-row-template', players, current_player_index);
    } else {
        UI.gotchaTable.hide();
        UI.gotchaCardContainer.show();
        renderPlayerCards(UI.gotchaCardContainer, '#gotcha-player-card-template', players, current_player_index, );
    }
}