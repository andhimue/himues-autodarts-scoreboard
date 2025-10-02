// Frontend/static/js/utils_frontend.js


/**
 * @summary Das globale UI-Objekt, das einmalig beim Laden der Seite befüllt wird.
 * Es dient als schneller Cache für alle benötigten DOM-Elemente.
 */
 
 const UI = {}; // Das globale, leere Objekt für unsere DOM-Elemente.

//------------------------------------------------------------------

/**
 * @summary Die Standard-Konfiguration für einfache Tabellen.
 * Wird von renderGameTable() als Fallback verwendet, wenn keine spezifische Konfiguration übergeben wird.
 */
 
 const DEFAULT_TABLE_CONFIG = [
    { selector: '.game-table__cell--player-name', source: player => player.name },
    { selector: '.game-table__cell--score',       source: player => player.score },
    { 
        selector: '.game-table__cell--legs-sets', 
        html: player => createLegsSetsHtml(player)
    }
];

//------------------------------------------------------------------

/**
 * @summary Die Standard-Konfiguration für einfache Spieler-Karten.
 */
 
 const DEFAULT_CARD_CONFIG = [
    { selector: '.player-card__name',   source: player => player.name },
    { selector: '.player-card__score',  source: player => player.score },
    { 
        selector: '.player-card__legs-sets', 
        html: player => createLegsSetsHtml(player)
    }
];

//------------------------------------------------------------------

/**
 * @summary Definiert die Datenstruktur für den oberen Fokus-Bereich der Anzeige.
 * Jedes `game-update` erzeugt ein neues ViewModel, das beschreibt, WAS angezeigt werden soll.
 */
 
 class FocusAreaViewModel {
    constructor() {
        // Entspricht dem Block .info-area__details
        this.details = {
            gamemode: {
                text: '',
                visible: true
            },
            
            gamerules: {
                html: '',
                visible: true
            }
        };

        // Entspricht dem Block .info-area__focus
        this.focus = {
            player_name: {
                visible: false,
                text: ''
            },
            score: {
                visible: true,
                text: ''
            },
            
            score_label: { text: 'Punkte', visible: false },
            graphic: {
                visible: false,
                target: null,
                mode: 'Full'
            }
        };
        
        // Entspricht dem Block .info-area__darts
        this.darts = {
            visible: true,
            turnInfo: {},
            checkoutGuide: []
        };

        // Zustand für Overlays
        this.isBusted = false;
    }
}

//------------------------------------------------------------------

/**
 * @summary Erstellt und befüllt ein Basis-ViewModel mit den Standard-Daten aus dem globalen appState.
 * @returns {FocusAreaViewModel} Ein vor-befülltes ViewModel-Objekt.
 */
 
function createBaseViewModel() {
    const viewModel = new FocusAreaViewModel();
    const { match, turn, players, current_player_index } = appState;

    if (!match) return viewModel;
    const currentPlayer = players[current_player_index];

    // Details befüllen (mit korrekten camelCase-Namen)
    viewModel.details.gamemode.text = match.game_mode;
    
    let rules = [];
    if (match.sets_to_win > 0) rules.push(`First to ${match.sets_to_win} Sets / ${match.legs_to_win} Legs`);
    else if (match.legs_to_win > 0) rules.push(`First to ${match.legs_to_win} Legs`);
    if (match.in_mode && match.in_mode !== 'Straight') rules.push(`${match.in_mode}-In`);
    if (match.out_mode && match.out_mode !== 'Straight') rules.push(`${match.out_mode}-Out`);
    if (match.max_rounds > 0) rules.push(`Runde: ${turn.current_round}/${match.max_rounds}`);
    viewModel.details.gamerules.html = rules.join('<br>');

    // Fokus-Bereich befüllen
    if (currentPlayer) {
        viewModel.focus.player_name.text = currentPlayer.name;
        viewModel.focus.score.text = currentPlayer.score;
    }

    // Darts befüllen
    viewModel.darts.turnInfo = turn || {};
    viewModel.isBusted = turn ? turn.busted : false;

    return viewModel;
}


//------------------------------------------------------------------

/**
 * @summary Orchestriert das Rendering des oberen Fokus-Bereichs.
 * Ruft zuerst updateSharedFocusArea auf und zeichnet dann bei Bedarf die SVG-Grafik.
 * @param {FocusAreaViewModel} viewModel Das zu rendernde ViewModel.
 */
 
 function renderFocusArea(viewModel) {
    updateSharedFocusArea(viewModel);

    // Greift jetzt auf die neuen, sauberen Eigenschaften im focus-Objekt zu
    if (viewModel.focus.graphic.visible && viewModel.focus.graphic.target) {
        const target = viewModel.focus.graphic.target;
        const mode = viewModel.focus.graphic.mode;

        if (target === 'Double' || target === 'Triple') {
            drawTargetRings(target); 
        } else if (target === 'Bullseye') {
            drawTargetSegment('Bull', 'Double');
        } else {
            drawTargetSegment(target, mode);
        }
    }
}

//------------------------------------------------------------------

/**
 * @summary Rendert die Anzeige für die drei geworfenen Darts oder den Checkout-Guide.
 * @param {jQuery|string} containerOrSelector Das Ziel-Container-Element.
 * @param {object} turnInfo Das turn-Objekt aus dem appState.
 * @param {Array} checkoutGuide Die Liste der Checkout-Vorschläge.
 */
 
 function renderDartsDisplay(containerOrSelector, turnInfo, checkoutGuide = []) {
    // PRÜFUNG: Ist das übergebene Element schon ein jQuery-Objekt oder nur ein String?
    // Wenn es ein String ist, führe die Suche mit $(...) aus.
    const container = (typeof containerOrSelector === 'string') 
        ? $(containerOrSelector) 
        : containerOrSelector;

    container.empty();

    const darts_thrown = turnInfo.throws || [];
    const pfeilGrafik = `<div class="dart"><img class="checkout-guide-arrow" src="/static/images/Pfeil.svg"></div>`;
    for (let i = 0; i < 3; i++) {
        let dartHtml = '';
        if (i < darts_thrown.length) {
            let dart = darts_thrown[i];

            // Logik zur Anpassung des Anzeigenamens für geworfene Darts
            let displayName = dart.segment.name;
            if (displayName === "Bull") {
                displayName = "👁";
            } else if (displayName === "25") {
                displayName = "Bull";
            }
            dartHtml = `<div class="dart dart-thrown"><div class="dart-value">${displayName}</div></div>`;

        } else {
            const guideIndex = i - darts_thrown.length;
            if (checkoutGuide && checkoutGuide.length > guideIndex) {
                let guide = checkoutGuide[guideIndex];
                if (guide.is_image) {
                    dartHtml = pfeilGrafik;
                } else {
                    // Dieselbe Logik auch für den Checkout-Guide anwenden
                    let guideName = guide.name;
                    if (guideName === "Bull") {
                        guideName = "👁";
                    } else if (guideName === "25") {
                        guideName = "Bull";
                    }
                    dartHtml = `<div class="dart dart-checkout-guide"><div class="dart-value">${guideName}</div></div>`;
                }
            } else {
                dartHtml = pfeilGrafik;
            }
         }
        container.append(dartHtml);
    }
}

//------------------------------------------------------------------

/**
 * @summary Aktualisiert die  HTML-Elemente im Fokus-Bereich basierend auf dem ViewModel.
 * @param {FocusAreaViewModel} viewModel Der "Bauplan" mit den anzuzeigenden Daten.
 */
 
function updateSharedFocusArea(viewModel) {
    const shouldBeVisible = viewModel.focus.player_name.visible || 
                            viewModel.focus.score.visible;
    UI.infoArea.toggle(shouldBeVisible);
    UI.gameModeDisplay.text(viewModel.details.gamemode.text).toggle(viewModel.details.gamemode.visible);
    UI.gameRulesDisplay.html(viewModel.details.gamerules.html).toggle(viewModel.details.gamerules.visible);
    UI.focusPlayerName.text(viewModel.focus.player_name.text).toggle(viewModel.focus.player_name.visible);
    UI.focusScore.html(viewModel.focus.score.text).toggle(viewModel.focus.score.visible);
    UI.focusScoreLabel.text(viewModel.focus.score_label.text).toggle(viewModel.focus.score_label.visible);
    
    UI.bustOverlaysContainer.toggle(viewModel.isBusted);
    
    //wird hier anders umgesetzt um die unnötige Ausführung von renderDartsDisplay() zu vermeiden, wenn der Bereich sowieso nciht angezeigt werden soll.
    if (viewModel.darts.visible) {
        // Nur wenn sichtbar, zeige den Container an UND rendere den Inhalt
        UI.dartsDisplay.show();
        renderDartsDisplay(UI.dartsDisplay, viewModel.darts.turnInfo, viewModel.darts.checkoutGuide);
    } else {
        // Sonst blende den Container aus
        UI.dartsDisplay.hide();
    }

}

//------------------------------------------------------------------
// Hilfsfunktion zum Injezieren des Icons in den Wrapper

/**
 * @summary Fügt das Owner- oder Registered-Icon in den dafür vorgesehenen Wrapper ein.
 * Wird intern von renderGameTable aufgerufen.
 * @param {jQuery} wrapperElement Das .avg-cell-wrapper Element.
 * @param {object} player Das Spieler-Objekt.
 */
function _addPlayerStatusIcon(wrapperElement, player) {
    let iconHtml = '';
    if (player.player_type === 'owner') {
        iconHtml = '<img class="player-status-icon" src="/static/images/owner.png" title="Board-Owner" />';
    } else if (player.player_type === 'registered') {
        iconHtml = '<img class="player-status-icon" src="/static/images/registered.png" title="Registrierter Spieler" />';
    }

    if (iconHtml) {
        wrapperElement.append(iconHtml);
    }
}

//------------------------------------------------------------------

//Die Tabellen im unteren Bereich

/**
 * @summary Rendert eine Spiel-Tabelle dynamisch. Merged eine optionale, benutzerdefinierte 
 * Konfiguration mit der Standard-Konfiguration.
 * Jede Tabelle enthält standardmäßig die Felder Spieler. Punkte, Legs.
 * das kann über den Parameter customConfig=[] dynamisch erweitert werden.
 * - Wenn man in customConfig einen Eintrag mit einem selector übergibst, der bereits in der DEFAULT_TABLE_CONFIG existiert 
 *   (z.B. .game-table__cell--score), wird der Standard-Eintrag komplett durch den neuen ersetzt.
 * - Direkt löschen kannst man ein Feld nicht, da die DEFAULT_TABLE_CONFIG immer als Basis dient. 
 *   Aber man kann den gleichen Überschreib-Mechanismus nutzen, um ein Feld leer zu lassen, indem man ihm eine leere Zeichenkette zuweist.
 *   Beispiel:
 *       Wir möchten für einen Spielmodus die Score-Spalte komplett ausblenden (bzw. leeren).
 *         const myCustomConfig = [
 *           // Überschreibe den Standard für die Score-Spalte und setze den Inhalt auf "leer"
 *           { 
 *             selector: '.game-table__cell--score', 
 *             source: player => '' // Gib immer einen leeren String zurück
 *           }
 *         ];
 *       angezeigt wird die Spalte aber trotzdem.
 *
 * @param {jQuery|string} tableOrSelector Das <table>-Element.
 * @param {string} templateSelector Die ID des <template>-Tags für eine Zeile.
 * @param {Array} players Die Liste der Spieler-Objekte.
 * @param {number} currentPlayerIndex Der Index des aktiven Spielers.
 * @param {Array} [customConfig=[]] Eine optionale, spezifische Konfiguration für die Spalten.
 */
 
function renderGameTable(tableOrSelector, templateSelector, players, currentPlayerIndex, customConfig = []) {
    // Den Namen des aktiven Spielers merken, BEVOR die Liste sortiert wird.
    const activePlayerName = (players && players.length > currentPlayerIndex) ? players[currentPlayerIndex].name : null;

    // Abhängig von der variablen in config_frontend.py oder des URL-Parameters ?sg
    // wird entweder die stabile Sortier-Reihenfolge der Spieler über ein komplettes Game hinweg
    // oder die Spielerreihenfolge, welche das Backend liefert genutzt.
    //Die Spielerliste im übergebenen Datenpaket ist imemr in Server-Reihenfolge
    
    // 1. Hole den Standardwert aus der Jinja2-Konstante
    let performStableSorting = (typeof FORCE_STABLE_SORTING === 'undefined' || FORCE_STABLE_SORTING);
    
    // 2. URL-Parameter überschreiben den Standardwert.
    // Wir greifen auf die globale Konstante URL_PARAMS zu (deklariert in scoreboard_helpers.js).
    if (URL_PARAMS.has('rn')) { // Server Native (keine stabile Sortierung)
        performStableSorting = false;
    } else if (URL_PARAMS.has('rs')) { // Stable Global (erzwingt stabile Sortierung)
        performStableSorting = true;
    }
    
    // Bei true wird die stabile Reihenfolge verwendet, bei false die Serverreihenfolge
    if (performStableSorting) {
        // Spielerliste anhand der `display_order` aus dem Event sortieren
        if (players && players.length > 0 && players[0].display_order !== null) {
            players.sort((a, b) => a.display_order - b.display_order);
        }
    }
    
    const tableElement  = (typeof tableOrSelector === 'string') 
        ? $(tableOrSelector) 
        : tableOrSelector;

    // Erstelle eine Map aus der Standard-Konfiguration für einfaches Mergen
    const finalConfigMap = new Map(DEFAULT_TABLE_CONFIG.map(item => [item.selector, item]));

    // Füge die benutzerdefinierte Konfiguration hinzu oder überschreibe Standard-Einträge
    customConfig.forEach(item => {
        finalConfigMap.set(item.selector, item);
    });

    const finalConfig = Array.from(finalConfigMap.values());
    
    // Erstelle <tbody>, falls es nicht existiert
    const tableBody = tableElement.find('tbody').length 
        ? tableElement.find('tbody') 
        : $('<tbody></tbody>').appendTo(tableElement);

    const template = $(templateSelector).prop('content');
    tableBody.empty();

    players.forEach((player, index) => {
        const newRow = $(template).clone();

        // Gehe durch die finale, gemergte Konfiguration
        finalConfig.forEach(config => {
            const element = newRow.find(config.selector);
            if (element.length > 0) {
                // HINZUGEFÜGT: Überprüfe, ob die Zelle Icons unterstützen soll und füge den Wrapper ein
                const usesIcons = config.tdClass && config.tdClass.includes('avg-with-icon');
                
                let content = '';
                if (config.source) {
                    content = config.source(player);
                } else if (config.html) {
                    content = config.html(player);
                }

                if (usesIcons) {
                    // Erzeuge den Wrapper für Text und Icon und füge den Text in ein separates Span ein
                    element.html(`<div class="avg-cell-wrapper"><span class="avg-cell-text">${content}</span></div>`);
                    // Füge das Icon hinzu, nachdem der Text im Wrapper platziert wurde
                    _addPlayerStatusIcon(element.find('.avg-cell-wrapper'), player);
                } else {
                    element.html(content);
                }


                if (config.tdClass) {
                    element.addClass(config.tdClass);
                }
            }
        });

        // Die Logik für die aktive Spielerzeile bleibt separat
        if (player.name === activePlayerName) {
            newRow.find('tr').addClass('active-player-row');
        }


        tableBody.append(newRow);
    });

    // Gib die jQuery-Objekte der gerade hinzugefügten Zeilen (<tr>) zurück.
    return tableBody.children();

}

//------------------------------------------------------------------

/**
 * @summary Rendert die Spieler-Karten dynamisch, basierend auf Konfigurationen.
 *
 * @param {jQuery|string} containerOrSelector Der Ziel-Container für die Karten.
 * @param {string} templateSelector Die ID des <template>-Tags für eine Karte.
 * @param {Array} players Die Liste der Spieler-Objekte.
 * @param {number} currentPlayerIndex Der Index des aktiven Spielers.
 * @param {Array} [customConfig=[]] Eine optionale Konfiguration für zusätzliche Felder.
 */
 
function renderPlayerCards(containerOrSelector, templateSelector, players, currentPlayerIndex, customConfig = []) {
    const containerElement = (typeof containerOrSelector === 'string') 
        ? $(containerOrSelector) 
        : containerOrSelector;

    const activePlayerName = (players && players.length > currentPlayerIndex) ? players[currentPlayerIndex].name : null;

    // Abhängig von der variablen in config_frontend.py oder des URL-Parameters ?sg
    // wird entweder die stabile Sortier-Reihenfolge der Spieler über ein komplettes Game hinweg
    // oder die Spielerreihenfolge, welche das Backend liefert genutzt.
    //Die Spielerliste im übergebenen Datenpaket ist imemr in Server-Reihenfolge
    
    // 1. Hole den Standardwert aus der Jinja2-Konstante
    let performStableSorting = (typeof FORCE_STABLE_SORTING === 'undefined' || FORCE_STABLE_SORTING);
    
    // 2. URL-Parameter überschreiben den Standardwert.
    // Wir greifen auf die globale Konstante URL_PARAMS zu (deklariert in scoreboard_helpers.js).
    if (URL_PARAMS.has('rn')) { // Server Native (keine stabile Sortierung)
        performStableSorting = false;
    } else if (URL_PARAMS.has('rs')) { // Stable Global (erzwingt stabile Sortierung)
        performStableSorting = true;
    }
    
    // Bei true wird die stabile Reihenfolge verwendet, bei false die Serverreihenfolge
    if (performStableSorting) {
        // Spielerliste anhand der `display_order` aus dem Event sortieren
        if (players && players.length > 0 && players[0].display_order !== null) {
            players.sort((a, b) => a.display_order - b.display_order);
        }
    }

    const finalConfigMap = new Map(DEFAULT_CARD_CONFIG.map(item => [item.selector, item]));
    customConfig.forEach(item => {
        finalConfigMap.set(item.selector, item);
    });
    const finalConfig = Array.from(finalConfigMap.values());

    const template = $(templateSelector).prop('content');
    containerElement.empty();

    // Über die sortierte Liste iterieren
    players.forEach((player) => {
        const cardFragment = $(template).clone();

        finalConfig.forEach(config => {
            const element = cardFragment.find(config.selector);
            if (element.length > 0) {
                if (config.source) {
                    element.text(config.source(player));
                } else if (config.html) {
                    element.html(config.html(player));
                }
            }
        });

        // HINZUGEFÜGT: Logik zur Icon-Injektion in den neuen Platzhalter
        const iconContainer = cardFragment.find('.player-card__status-icon');
        if (iconContainer.length) {
            let iconHtml = '';
            if (player.player_type === 'owner') {
                iconHtml = '<img src="/static/images/owner.png" title="Board-Owner" />';
            } else if (player.player_type === 'registered') {
                iconHtml = '<img src="/static/images/registered.png" title="Registrierter Spieler" />';
            }
            iconContainer.html(iconHtml);
        }
        // ENDE NEUE LOGIK

        // Die Hervorhebung erfolgt jetzt durch Namensvergleich.
        if (player.name === activePlayerName) {
            cardFragment.children('.player-card').addClass('player-card--is-active');
        }
        containerElement.append(cardFragment);
    });
}
//------------------------------------------------------------------

/**
 * @summary Erstellt den HTML-Code für die Legs/Sets-Anzeige.
 * @param {object} player Das Spieler-Objekt.
 * @returns {string} Den fertigen HTML-String.
 */
 
 function createLegsSetsHtml(player) {
    const { match } = appState;
    let innerHtml = `<div class="legs-won" title="Gewonnene Legs">${player.legs_won}</div>`;
    if (match && match.sets_to_win > 0) {
        innerHtml += `<div class="sets-won" title="Gewonnene Sets">${player.sets_won}</div>`;
    }
    // Erzeugt immer den Wrapper mit der korrekten Klasse
    return `<div class="legs-sets-container">${innerHtml}</div>`;
}

//------------------------------------------------------------------

/**
 * @summary Formatiert einen Average-Wert für die Anzeige.
 * Gibt den Wert auf zwei Nachkommastellen formatiert zurück.
 * Wenn der Wert 0, null oder ungültig ist, wird ein Bindestrich '-' zurückgegeben.
 * @param {number|string} avg Der zu formatierende Average-Wert.
 * @returns {string} Der formatierte String (z.B. "42.17") oder ein Bindestrich.
 */
 
function formatAverage(avg) {
    const num = parseFloat(avg);
    return (num && num > 0) ? num.toFixed(2) : '-';
}

//------------------------------------------------------------------

// NEU: Diese Funktion formatiert den Average UND fügt das Icon hinzu.
function createOverallAverageHtml(player, key = 'overall_average', showIcons = false) {
    const averageText = formatAverage(player[key]);
    let iconHtml = '';

    if (showIcons) {
        if (player.player_type === 'owner') {
            iconHtml = '<img class="player-status-icon" src="/static/images/owner.png" title="Board-Owner" />';
        } else if (player.player_type === 'registered') {
            iconHtml = '<img class="player-status-icon" src="/static/images/registered.png" title="Registrierter Spieler" />';
        }
    }
    // HINZUGEFÜGT: Ein Wrapper und ein separates Span für den Text
    return `<div class="avg-cell-wrapper">
                <span class="avg-cell-text">${averageText}</span>
                ${iconHtml}
            </div>`;
}

/**
 * @summary Blendet eine komplette Tabellenspalte (Header und Zellen) ein oder aus.
 * @param {string} tableSelector Der CSS-Selector für die Tabelle (z.B. '#x01-table').
 * @param {string} columnIdentifier Ein eindeutiger Bezeichner für die Spalte (z.B. 'avg-g').
 * @param {boolean} shouldShow `true` zum Einblenden, `false` zum Ausblenden.
 */
function toggleTableColumn(tableSelector, columnIdentifier, shouldShow) {
    const headerSelector = `.game-table__header--${columnIdentifier}`;
    const cellSelector = `.game-table__cell--${columnIdentifier}`;
    
    // Wähle sowohl Header als auch Zellen innerhalb der spezifischen Tabelle aus
    $(tableSelector).find(headerSelector + ', ' + cellSelector).toggle(shouldShow);
}