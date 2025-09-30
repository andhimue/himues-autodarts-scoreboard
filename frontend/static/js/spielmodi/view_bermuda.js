// Frontend/static/js/spielmodi/view_bermuda.js

/**
 * @summary Aktualisiert die komplette Ansicht für den Spielmodus "Bermuda".
 * Wird von der updateDisplay()-Funktion aufgerufen.
 */

function updateBermudaView(viewModel) {
    const { players, turn, current_player_index } = appState;

    viewModel.focus.score.text = turn.target;
    viewModel.focus.graphic.visible = true;
    viewModel.focus.graphic.target = turn.target;
    
    renderFocusArea(viewModel);
    renderGameTable('#bermuda-table', '#bermuda-row-template', players, current_player_index);
}