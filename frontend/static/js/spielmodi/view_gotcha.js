// Frontend/static/js/spielmodi/view_gotcha.js

/**
 * @summary Aktualisiert die komplette Ansicht für den Spielmodus "Gotcha".
 * Wird von der updateDisplay()-Funktion aufgerufen.
 */

function updateGotchaView(viewModel) {
    const { match, players, current_player_index } = appState;

    viewModel.details.gamemode.text = `${match.game_mode} ${match.start_score}`;
    renderFocusArea(viewModel);

    let displayMode = 'table';
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('xc')) displayMode = 'cards';

    if (displayMode === 'table') {
        UI.gotchaCardContainer.hide();
        UI.gotchaTable.show();
        renderGameTable(UI.gotchaTable, '#gotcha-table-row-template', players, current_player_index);
    } else {
        UI.gotchaTable.hide();
        UI.gotchaCardContainer.show();
        renderPlayerCards(UI.gotchaCardContainer, '#gotcha-player-card-template');
    }
}