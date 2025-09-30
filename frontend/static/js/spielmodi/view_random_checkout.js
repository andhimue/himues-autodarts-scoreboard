// Frontend/static/js/spielmodi/view_random_checkout.js

/**
 * @summary Aktualisiert die komplette Ansicht für den Spielmodus "Random Checkout".
 * Wird von der updateDisplay()-Funktion aufgerufen.
 */

function updateRandomCheckoutView(viewModel) {
    const { players, checkout_guide, current_player_index } = appState;
 
    // Passe das ViewModel an
    viewModel.darts.checkoutGuide = checkout_guide || [];
    
    // Rendere den Fokus-Bereich (inkl. Grafik)
    renderFocusArea(viewModel);

    // Rendere die Tabelle
    renderGameTable(
        '#random-checkout-table', 
        '#random-checkout-row-template', 
        players, 
        current_player_index
    );
}