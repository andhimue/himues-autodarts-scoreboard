// Frontend/static/js/spielmodi/view_rtw.js

/**
 * @summary Aktualisiert die komplette Ansicht für den Spielmodus "Round the World".
 * Wird von der updateDisplay()-Funktion aufgerufen.
 */

function updateRTWView(viewModel) {
    const { players, turn, current_player_index, match } = appState;

    viewModel.details.gamemode.text = "Round the World";

    const detailsHtml = `
        <div class="setting-row">
            <span class="setting-label">Reihenfolge:</span>
            <span class="setting-value">${match.order}</span>
        </div>
    `;
    viewModel.details.gamerules.html = detailsHtml;

    viewModel.focus.score.text = turn.target;
    viewModel.focus.graphic.visible = true;
    viewModel.focus.graphic.target = turn.target;

    renderFocusArea(viewModel);
    renderGameTable('#rtw-table', '#rtw-row-template', players, current_player_index);
}