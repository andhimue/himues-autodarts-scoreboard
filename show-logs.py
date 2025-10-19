#!/usr/bin/env python3
# show-logs.py

import curses
import subprocess
import threading
import queue
import os
import sys
from datetime import datetime

# --- Konfiguration ---
BACKEND_SERVICE = "himues-scoreboard-backend.service"
FRONTEND_SERVICE = "himues-scoreboard-frontend.service"

# --- Farbdefinitionen für Curses ---
class CursesColor:
    HEADER = 1
    BACKEND_TEXT = 2
    FRONTEND_TEXT = 3
    INFO_TEXT = 4

def log_reader(proc, log_queue, name):
    """Liest die Ausgabe eines Prozesses Zeile für Zeile und stellt sie in eine Queue."""
    try:
        # bufsize=1 im Popen-Aufruf ist entscheidend, damit hier sofort Zeilen ankommen
        for line in iter(proc.stdout.readline, ''):
            timestamp = datetime.now().strftime('%H:%M:%S')
            log_queue.put(f"[{timestamp} {name}] {line}")
    except Exception:
        pass

def draw_window(win, title, color_pair, lines):
    """Zeichnet ein Fenster mit Rahmen, Titel und dem Log-Inhalt."""
    win.erase()
    win.border()
    win.addstr(0, 2, f" {title} (Drücke 'q' zum Beenden) ", curses.color_pair(CursesColor.HEADER) | curses.A_BOLD)
    
    height, width = win.getmaxyx()
    max_lines = height - 2
    
    start_index = max(0, len(lines) - max_lines)
    for i, line in enumerate(lines[start_index:]):
        display_line = line.strip().replace('\t', '    ')[:width - 2]
        try:
            win.addstr(i + 1, 2, display_line, curses.color_pair(color_pair))
        except curses.error:
            # Ignoriere Fehler, die auftreten, wenn eine Zeile am Rand geschrieben wird
            pass
    win.refresh()

def main(stdscr):
    """Hauptfunktion zur Initialisierung und Steuerung der Curses-Anwendung."""
    curses.curs_set(0)
    stdscr.nodelay(1)
    curses.start_color()
    curses.init_pair(CursesColor.HEADER, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(CursesColor.BACKEND_TEXT, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(CursesColor.FRONTEND_TEXT, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(CursesColor.INFO_TEXT, curses.COLOR_WHITE, curses.COLOR_BLACK)

    height, width = stdscr.getmaxyx()
    split_row = height // 2
    
    backend_win = curses.newwin(split_row, width, 0, 0)
    frontend_win = curses.newwin(height - split_row, width, split_row, 0)
    
    # Automatische Diensterkennung basierend auf dem ausführenden Benutzer
    if os.geteuid() == 0:
        journal_cmd = ["journalctl", "-f", "-u"]
        service_type_msg = "System-Dienste (als root ausgeführt)"
    else:
        journal_cmd = ["journalctl", "--user", "-f", "-u"]
        service_type_msg = "Benutzer-Dienste"
    
    status_line = f"Modus: {service_type_msg}. Starte Logs..."
    backend_lines = [status_line]
    frontend_lines = [status_line]
    
    draw_window(backend_win, "Backend Logs", CursesColor.INFO_TEXT, backend_lines)
    draw_window(frontend_win, "Frontend Logs", CursesColor.INFO_TEXT, frontend_lines)
    curses.napms(1500)

    try:
        # bufsize=1 (line-buffered) ist entscheidend für Live-Output
        backend_proc = subprocess.Popen(journal_cmd + [BACKEND_SERVICE], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        frontend_proc = subprocess.Popen(journal_cmd + [FRONTEND_SERVICE], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    except FileNotFoundError:
        curses.endwin()
        print(f"\nFehler: Befehl 'journalctl' nicht gefunden. Bitte sicherstellen, dass er installiert ist.")
        sys.exit(1)

    backend_queue = queue.Queue()
    frontend_queue = queue.Queue()

    backend_thread = threading.Thread(target=log_reader, args=(backend_proc, backend_queue, 'BACK'))
    frontend_thread = threading.Thread(target=log_reader, args=(frontend_proc, frontend_queue, 'FRONT'))
    
    backend_thread.daemon = True
    frontend_thread.daemon = True
    
    backend_thread.start()
    frontend_thread.start()
    
    backend_lines = []
    frontend_lines = []
    
    while True:
        key = stdscr.getch()
        if key == ord('q'):
            break

        try:
            while not backend_queue.empty():
                backend_lines.append(backend_queue.get_nowait())
            while not frontend_queue.empty():
                frontend_lines.append(frontend_queue.get_nowait())
        except queue.Empty:
            pass

        draw_window(backend_win, "Backend Logs", CursesColor.BACKEND_TEXT, backend_lines)
        draw_window(frontend_win, "Frontend Logs", CursesColor.FRONTEND_TEXT, frontend_lines)

        curses.napms(100)

    backend_proc.terminate()
    frontend_proc.terminate()

if __name__ == "__main__":
    if not sys.stdout.isatty():
        print("Fehler: Dieses Skript muss in einem interaktiven Terminal ausgeführt werden.")
        sys.exit(1)
        
    try:
        curses.wrapper(main)
    except curses.error as e:
        print(f"\nEin Curses-Fehler ist aufgetreten: {e}")
        print("Stelle sicher, dass dein Terminal die Fenstergröße unterstützt.")
    except KeyboardInterrupt:
        print("\nAnzeige beendet.")