#!/bin/bash

# Farben für die Ausgabe
COLOR_RED='\033[91m'
COLOR_YELLOW='\033[93m'
COLOR_GREEN='\033[92m'
COLOR_BOLD='\033[1m'
COLOR_END='\033[0m'

echo -e "${COLOR_YELLOW}${COLOR_BOLD}--- Deinstallations-Skript für Himues Darts Scoreboard ---${COLOR_END}"
echo -e "${COLOR_RED}WARNUNG: Dieses Skript wird die systemd-Dienste stoppen und deaktivieren"
echo -e "und anschließend das gesamte Verzeichnis $(pwd) löschen.${COLOR_END}"
echo ""

# Sicherheitsabfrage
read -p "Sind Sie sicher, dass Sie fortfahren möchten? [y/N] " response
if [[ "$response" != "y" ]] && [[ "$response" != "Y" ]]; then
    echo "Abbruch."
    exit 1
fi

echo ""

# --- 1. Dienste stoppen und deaktivieren ---

# Prüfen, ob als root/sudo ausgeführt, um zwischen System- und Benutzer-Diensten zu unterscheiden
if [ "$EUID" -eq 0 ]; then
    echo "Führe als root aus. Stoppe und deaktiviere System-Dienste..."
    systemctl stop himues-scoreboard-backend.service 2>/dev/null
    systemctl stop himues-scoreboard-frontend.service 2>/dev/null
    systemctl disable himues-scoreboard-backend.service 2>/dev/null
    systemctl disable himues-scoreboard-frontend.service 2>/dev/null

    echo "Lösche Service-Dateien aus /etc/systemd/system/..."
    rm -f /etc/systemd/system/himues-scoreboard-frontend.service
    rm -f /etc/systemd/system/himues-scoreboard-backend.service

    echo "Lade systemd-Daemon neu..."
    systemctl daemon-reload
else
    echo "Führe als normaler Benutzer aus. Stoppe und deaktiviere Benutzer-Dienste..."
    systemctl --user stop himues-scoreboard-backend.service 2>/dev/null
    systemctl --user stop himues-scoreboard-frontend.service 2>/dev/null
    systemctl --user disable himues-scoreboard-backend.service 2>/dev/null
    systemctl --user disable himues-scoreboard-frontend.service 2>/dev/null

    echo "Lösche Service-Dateien aus ~/.config/systemd/user/..."
    rm -f "$HOME/.config/systemd/user/himues-scoreboard-frontend.service"
    rm -f "$HOME/.config/systemd/user/himues-scoreboard-backend.service"

    echo "Lade Benutzer-systemd-Daemon neu..."
    systemctl --user daemon-reload
fi

echo -e "${COLOR_GREEN}✅ Dienste erfolgreich entfernt.${COLOR_END}"
echo ""

# --- 2. Das Selbstzerstörungs-Verfahren ---

# Finde das Verzeichnis, in dem dieses Skript liegt
# Dies ist das Hauptverzeichnis des Projekts, das wir löschen wollen
PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

echo "Das Projektverzeichnis '${PROJECT_DIR}' wird in 2 Sekunden gelöscht."
echo "Das Skript beendet sich jetzt."

# Starte einen Hintergrundprozess, der wartet und dann das Verzeichnis löscht.
# Das '&' am Ende entkoppelt den Prozess, sodass dieses Skript sofort beendet werden kann.
( sleep 2 && rm -rf "$PROJECT_DIR" && cd ..) &

echo -e "${COLOR_GREEN}Deinstallation abgeschlossen!${COLOR_END}"
exit 0