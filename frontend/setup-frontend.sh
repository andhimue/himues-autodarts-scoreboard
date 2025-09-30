#!/bin/bash

# Stellt sicher, dass das Skript bei einem Fehler abbricht
#set -e

# === Teil 1: Systemweite Installation (benötigt root-Rechte) ===
echo "Phase 1: Systemweite Installation von Node.js und npm (sudo wird benötigt)..."

# Überprüfe, ob Node.js bereits installiert ist
if ! command -v node > /dev/null; then
    echo "Node.js nicht gefunden. Installiere Node.js und npm..."
    #debian enthält nur node.js 18, vite hätte gerne >= 20
    curl -sL https://deb.nodesource.com/setup_22.x | sudo -E bash -
    sudo apt-get update
    sudo apt-get install -y nodejs npm
else
    echo "Node.js ist bereits installiert. Überspringe Installation."
fi

echo ""
echo "System-Voraussetzungen sind erfüllt."
echo "--------------------------------------------------"
echo ""


# === Teil 2: Projektspezifische Installation (als normaler Benutzer) ===
echo "Phase 2: Lokale Projekt-Abhängigkeiten installieren..."

# Initialisiere das npm-Projekt, falls noch keine package.json existiert
if [ ! -f "package.json" ]; then
    echo "Erstelle package.json..."
    npm init -y
else
    echo "package.json existiert bereits."
fi

# Installiere die dev-Abhängigkeiten
echo "Installiere Vite und @vitejs/plugin-legacy..."
npm install vite @vitejs/plugin-legacy --save-dev

echo ""
echo "--------------------------------------------------"
echo "✅ Frontend-Setup erfolgreich abgeschlossen!"
echo "Du kannst jetzt den Entwicklungs-Server starten mit: npm run dev"
echo "Oder die produktive Version bauen mit: npm run build"
