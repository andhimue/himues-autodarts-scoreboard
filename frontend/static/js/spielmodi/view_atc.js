// Frontend/static/js/spielmodi/view_atc.js

/**
 * definiert, welche Tabellenzellen zusätzlich bei der Tabellenanzeige bei "Around the Clock" dargestellt werden sollen
 * wird als Paramater an renderGameTable() übergeben
 */

const atcTableConfig = [
    // GEÄNDERT: Ruft jetzt die neue Formatierungsfunktion auf
    { 
        selector: '.game-table__cell--target',
        source: player => formatAtcTarget(player.current_target, appState.match.scoring_mode) 
    },
    { selector: '.game-table__cell--avg-g',       source: player => player.overall_hit_rate > 0 ? `${(player.overall_hit_rate * 100).toFixed(0)}%` : '-' },
    { selector: '.game-table__cell--match-hr',    source: player => `${(player.match_hit_rate * 100).toFixed(0)}%` },
    { selector: '.game-table__cell--leg-hr',      source: player => `${(player.leg_hit_rate * 100).toFixed(0)}%` }
];
/**
 * @summary Aktualisiert die komplette Ansicht für den Spielmodus "Around the Clock".
 * Wird von der updateDisplay()-Funktion aufgerufen.
 */

function updateATCView(viewModel) {
    const { players, match, current_player_index } = appState;
    const currentPlayer = players[current_player_index];

    viewModel.details.gamemode.text = "Around the Clock";

    let detailsHtml = `
        <div class="setting-row">
            <span class="setting-label">Reihenfolge:</span>
            <span class="setting-value">${match.order}</span>
        </div>
        <div class="setting-row">
            <span class="setting-label">Modus:</span>
            <span class="setting-value">${match.scoring_mode}</span>
        </div>
    `;

    // Füge die "Hits pro Ziel"-Zeile nur hinzu, wenn der Wert vorhanden und größer 0 ist.
    if (match.hits_per_target > 0) {
        detailsHtml += `
            <div class="setting-row">
                <span class="setting-label">Hits pro Ziel:</span>
                <span class="setting-value">${match.hits_per_target}</span>
            </div>
        `;
    }

    viewModel.details.gamerules.html = detailsHtml;

    // Logik zur Erstellung des detaillierten Anzeigetextes
    const targetSegment = currentPlayer.current_target;
    const targetMode = match.scoring_mode;

    const mainDisplayText = formatAtcTarget(currentPlayer.current_target, match.scoring_mode);

    viewModel.focus.score.text = mainDisplayText;

    viewModel.focus.graphic.visible = true;
    viewModel.focus.graphic.target = currentPlayer.current_target;
    viewModel.focus.graphic.mode = match.scoring_mode ? match.scoring_mode : 'Single';

    renderFocusArea(viewModel);
    renderGameTable('#atc-table', '#atc-row-template', players, current_player_index, atcTableConfig);

    // Spalte ein-/ausblenden, je nachdem ob die Datenbank im Backend genutzt wird oder nicht.
    const useDB = appState.match.use_db;
    toggleTableColumn('#atc-table', 'avg-g', useDB);
}

//Eine wiederverwendbare Funktion zur Formatierung des Ziels
function formatAtcTarget(targetSegment, targetMode) {
    if (!targetSegment) return "?";

    let displayText = targetSegment;
    if (targetSegment === 'Bull') {
        // Für ATC ist Bullseye (D-Bull) normalerweise kein explizites Ziel,
        // daher wird es vereinfacht. Kann bei Bedarf angepasst werden.
        displayText = 'Bull';
    } else if (targetSegment !== '?') {
        if (targetMode === 'Triple') {
            displayText = 'T' + targetSegment;
        } else if (targetMode === 'Double') {
            displayText = 'D' + targetSegment;
        } else if (targetMode === 'Outer Single') {
            displayText = 'OS' + targetSegment;
        }
    }
    return displayText;
}