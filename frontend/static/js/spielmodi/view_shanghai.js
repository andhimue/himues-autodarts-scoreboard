// Frontend/static/js/spielmodi/view_shanghai.js


/**
 * @summary Aktualisiert die komplette Ansicht für den Spielmodus "Shanghai".
 * Wird von der updateDisplay()-Funktion aufgerufen.
 */
 
function updateShanghaiView(viewModel) {
    const { players, turn, current_player_index } = appState;

    viewModel.focus.score.text = turn.target;
    viewModel.focus.graphic.visible = true;
    viewModel.focus.graphic.target = turn.target;
    
    renderFocusArea(viewModel);
    renderGameTable('#shanghai-table', '#shanghai-row-template', players, current_player_index);
}