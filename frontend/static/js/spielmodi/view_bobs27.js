// Frontend/static/js/spielmodi/view_bobs27.js

/**
 * definiert, welche Tabellenzellen zusätzlich bei der Tabellenanzeige bei Bob's 27 dargestellt werden sollen
 * wird als Paramater an renderGameTable() übergeben
 */

const bobs27TableConfig = [
    { selector: '.game-table__cell--target', source: player => appState.turn.target }
];

/**
 * @summary Aktualisiert die komplette Ansicht für den Spielmodus "Bob's 27".
 * Wird von der updateDisplay()-Funktion aufgerufen.
 */

function updateBobs27View(viewModel) {
    const { players, turn, current_player_index, match } = appState;

    modus = match.scoring_mode
    if (modus == "Allow Negative Score") { modus = "Negativ erl."}
    const detailsHtml = `
        <div class="setting-row">
            <span class="setting-label">Reihenfolge:</span>
            <span class="setting-value">${match.order}</span>
        </div>
        <div class="setting-row">
            <span class="setting-label">Modus:</span>
            <span class="setting-value">${modus}</span>
        </div>
    `;
    viewModel.details.gamerules.html = detailsHtml;

    viewModel.focus.score.text = turn.target;
    viewModel.focus.graphic.visible = true;
    viewModel.focus.graphic.target = turn.target.replace('D', '');
    viewModel.focus.graphic.mode = 'Double';
    
    renderFocusArea(viewModel);
    renderGameTable('#bobs27-table', '#bobs27-row-template', players, current_player_index, bobs27TableConfig);
}