// Frontend/static/js/spielmodi/view_segment_training.js

/**
 * definiert, welche Tabellenzellen zusätzlich bei der Tabellenanzeige bei Segment-Training dargestellt werden sollen
 * wird als Paramater an renderGameTable() übergeben
 */

const segmentTrainingTableConfig = [
    { selector: '.game-table__cell--darts-thrown',  source: player => player.darts_thrown_leg },
    { selector: '.game-table__cell--avg-g', source: player => player.overall_hit_rate > 0 ? `${(player.overall_hit_rate * 100).toFixed(1)}%` : '-' },
    { selector: '.game-table__cell--leg-hitrate',   source: player => `${(player.leg_hit_rate * 100).toFixed(1)}%` },
    { selector: '.game-table__cell--match-hitrate', source: player => `${(player.match_hit_rate * 100).toFixed(1)}%` }
];

/**
 * @summary Aktualisiert die komplette Ansicht für den Spielmodus "Game Training".
 * Wird von der updateDisplay()-Funktion aufgerufen.
 */

function updateSegmentTrainingView(viewModel) {
    const { match, turn, players, current_player_index } = appState;
    const endsAfterText = `Ziel: ${match.ends_after_value} ${match.ends_after_type === 'hits' ? 'Treffer' : 'Darts'}`;

    viewModel.details.gamerules.html = `Segment: ${turn.target.segment} (${turn.target.mode})<br>${endsAfterText}`;

    let mainDisplayText = turn.target.segment;
    if (turn.target.segment === 'Bull') {
        if (turn.target.mode === 'Single' || turn.target.mode === 'Outer Single') mainDisplayText = 'Bull';
        else if (turn.target.mode === 'Double' || turn.target.mode === 'Triple') mainDisplayText = 'Bullseye';
    } else {
        if (turn.target.mode === 'Triple') mainDisplayText = 'T' + turn.target.segment;
        else if (turn.target.mode === 'Double') mainDisplayText = 'D' + turn.target.segment;
        else if (turn.target.mode === 'Outer Single') mainDisplayText = 'OS' + turn.target.segment;
    }
    viewModel.focus.score.text = mainDisplayText;

    viewModel.focus.graphic.visible = true;
    viewModel.focus.graphic.target = turn.target.segment;
    viewModel.focus.graphic.mode = turn.target.mode;

    renderFocusArea(viewModel);
    renderGameTable('#segment-training-table', '#segment-training-row-template', players, current_player_index, segmentTrainingTableConfig);

    // Spalte je nach DB-Nutzung ein-/ausblenden
    const useDB = appState.match.use_db;
    toggleTableColumn('#segment-training-table', 'avg-g', useDB);
}
