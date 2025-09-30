// Frontend/static/js/spielmodi/view_cricket.js

/**
 * definiert, welche Tabellenzellen zusätzlich bei der Tabellenanzeige bei Cricket dargestellt werden sollen
 * wird als Paramater an renderGameTable() übergeben
 */
const cricketTableConfig = [
    { selector: '.game-table__cell--hits-15',   html: p => createHitCellHtml(p, '15') },
    { selector: '.game-table__cell--hits-16',   html: p => createHitCellHtml(p, '16') },
    { selector: '.game-table__cell--hits-17',   html: p => createHitCellHtml(p, '17') },
    { selector: '.game-table__cell--hits-18',   html: p => createHitCellHtml(p, '18') },
    { selector: '.game-table__cell--hits-19',   html: p => createHitCellHtml(p, '19') },
    { selector: '.game-table__cell--hits-20',   html: p => createHitCellHtml(p, '20') },
    { selector: '.game-table__cell--hits-bull', html: p => createHitCellHtml(p, 'bull') },
    { selector: '.game-table__cell--avg-g',     html: p => createOverallAverageHtml(p, 'overall_mpr') },
    { selector: '.game-table__cell--mpr',       source: p => parseFloat(p.mpr || 0).toFixed(2) }
];

/**
 * definiert, welche Tabellenzellen zusätzlich bei der Tabellenanzeige bei Tactics dargestellt werden sollen
 * wird als Paramater an renderGameTable() übergeben
 */
const tacticsTableConfig = [
    ...cricketTableConfig, // Übernimmt alle Felder von der Cricket-Konfiguration
    { selector: '.game-table__cell--hits-10',   html: p => createHitCellHtml(p, '10') },
    { selector: '.game-table__cell--hits-11',   html: p => createHitCellHtml(p, '11') },
    { selector: '.game-table__cell--hits-12',   html: p => createHitCellHtml(p, '12') },
    { selector: '.game-table__cell--hits-13',   html: p => createHitCellHtml(p, '13') },
    { selector: '.game-table__cell--hits-14',   html: p => createHitCellHtml(p, '14') }
];

/**
 * @summary Aktualisiert die komplette Ansicht für den Spielmodus "Cricket oder Tactics".
 * Wird von der updateDisplay()-Funktion aufgerufen.
 */
function updateCricketView(viewModel) {
    renderFocusArea(viewModel);

    const { match, players, current_player_index } = appState;

    // Entscheide, welche Tabelle und Konfiguration basierend auf den Zielen verwendet wird
    const isTactics = match.targets.length > 7;

    const tableId = isTactics ? '#tactics-table' : '#cricket-table';
    const templateId = isTactics ? '#tactics-row-template' : '#cricket-row-template';
    const config = isTactics ? tacticsTableConfig : cricketTableConfig;

    // Blende die nicht verwendete Tabelle aus und die richtige ein
    UI.cricketTable.toggle(!isTactics);
    UI.tacticsTable.toggle(isTactics);

    // Rufe die Standard-Render-Funktion mit den richtigen Parametern auf
    renderGameTable(
        tableId,
        templateId,
        players,
        current_player_index,
        config
    );

    // Blende die "ø Gesamt"-Spalte bei Bedarf aus
    const useDB = appState.match.use_db;
    toggleTableColumn(tableId, 'avg-g', useDB);
}

// Hilfsfunktion, um den HTML-Inhalt für die Treffer-Zellen zu erzeugen
function createHitCellHtml(player, target) {
    const hits = player.hits[target] || 0;
    return `<div class="cricket-hit-mark cricket-hit-${Math.min(hits, 3)}"></div>`;
}