# Frontend/modules/core/config_editor.py

import os
import re
import subprocess
import logging
from . import shared_state_frontend as g

CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config_frontend.py')

def is_running_as_service():
    """Prüft, ob die Anwendung als systemd-Dienst läuft."""
    return os.getenv('INVOCATION_ID') is not None

def parse_config_file():
    """
    Parst die config_frontend.py und erstellt eine strukturierte Liste
    für die dynamische Formular-Generierung. Unterstützt jetzt auch mehrzeilige Dictionaries.
    """
    structure = []
    current_section = None
    is_next_line_hidden = False
    
    # Zustandsvariablen für Multiline-Parsing
    in_multiline_dict = False
    multiline_var_name = None
    multiline_buffer = []
    multiline_comment = ''

    with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    def finalize_section(section):
        if section and section.get('variables'):
            structure.append(section)

    for line in lines:
        line_stripped = line.strip()

        # 1. Multiline-Logik: Wir sind mitten in einem Dictionary-Block
        if in_multiline_dict:
            multiline_buffer.append(line) # Original-Einrückung behalten
            if line_stripped == '}' or line_stripped.startswith('}'):
                # Block zu Ende
                full_value = "".join(multiline_buffer)
                
                # Zur aktuellen Sektion hinzufügen
                current_section['variables'].append({
                    'name': multiline_var_name,
                    'value': full_value,
                    'type': 'dictionary', # Neuer Typ
                    'comment': multiline_comment
                })
                
                # Reset
                in_multiline_dict = False
                multiline_var_name = None
                multiline_buffer = []
                multiline_comment = ''
            continue

        # 2. Standard-Logik
        if line_stripped.startswith('# @hidden'):
            is_next_line_hidden = True
            continue

        if is_next_line_hidden:
            is_next_line_hidden = False
            continue

        if not line_stripped or line_stripped.startswith('import') or '.py' in line_stripped:
            finalize_section(current_section)
            current_section = None
            continue

        if line_stripped.startswith('# '):
            header_text = line_stripped.strip('# ').strip()
            if current_section and current_section.get('type') == 'section' and not current_section.get('variables'):
                current_section['title'] += ' ' + header_text
            else:
                finalize_section(current_section)
                current_section = {'type': 'section', 'title': header_text, 'variables': []}
            continue
        
        match = re.match(r'^([A-Z_][A-Z0-9_]*)\s*=\s*(.*)', line_stripped)
        if match:
            var_name = match.group(1)
            raw_value = match.group(2).strip()
            
            inline_comment = ''
            if '#' in raw_value:
                parts = raw_value.split('#', 1)
                raw_value = parts[0].strip()
                inline_comment = parts[1].strip()

            # SPEZIALFALL: Start eines Dictionary-Blocks (endet mit {)
            if raw_value == '{':
                if current_section is None:
                    current_section = {'type': 'section', 'title': 'Allgemein', 'variables': []}
                
                in_multiline_dict = True
                multiline_var_name = var_name
                multiline_comment = inline_comment
                multiline_buffer.append("{\n") # Startet den Buffer neu
                continue

            value_type = 'string'
            value = raw_value
            
            if raw_value.lower() in ['true', 'false']:
                value_type = 'boolean'
                value = raw_value.lower() == 'true'
            elif raw_value.isdigit():
                value_type = 'integer'
                value = int(raw_value)
            elif raw_value.startswith('[') and raw_value.endswith(']'):
                value_type = 'list'
                value = raw_value.strip('[]').replace('"', '').replace("'", "")
            # Einfaches einzeiliges Dict
            elif raw_value.startswith('{') and raw_value.endswith('}'):
                value_type = 'dictionary'
                value = raw_value
            else:
                value = raw_value.strip('\'"')

            if current_section is None:
                current_section = {'type': 'section', 'title': 'Allgemein', 'variables': []}

            current_section['variables'].append({
                'name': var_name,
                'value': value,
                'type': value_type,
                'comment': inline_comment
            })

    finalize_section(current_section)
    return structure


def save_config_file(form_data):
    """
    Speichert die Formulardaten zurück in die config_frontend.py.
    """
    with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    skip_mode = False # Flag, um alte Multiline-Blöcke zu überspringen

    for line in lines:
        # Wenn wir im Skip-Modus sind (weil wir gerade ein Dict ersetzt haben),
        # ignorieren wir alle Zeilen bis zur schließenden Klammer.
        if skip_mode:
            if line.strip() == '}' or line.strip().startswith('}'):
                skip_mode = False
            continue

        match = re.match(r'^([A-Z_][A-Z0-9_]*)\s*=', line.strip())
        if match:
            var_name = match.group(1)
            
            # Prüfen, ob die ORIGINALE Zeile den Start eines Blocks war
            original_value_start = line.split('=', 1)[1].strip().split('#')[0].strip()
            if original_value_start == '{':
                skip_mode = True # Aktiviere Skip-Modus für die nächsten Zeilen

            if var_name in form_data:
                new_value = form_data.get(var_name)
                
                # Kommentar aus der Originalzeile retten
                inline_comment = ''
                if '#' in line:
                    parts = line.split('#', 1)
                    if len(parts) > 1:
                        inline_comment = ' # ' + parts[1].strip()
                
                formatted_value = f'"{new_value}"' # Default: String mit Quotes

                # Typ-Erkennung für das korrekte Format
                # 1. Boolean
                if new_value == 'on': # Checkbox sendet 'on'
                    formatted_value = 'True'
                # 2. Explizit False (wenn Checkbox nicht gesendet wurde, wird das hier im else-Block unten behandelt)
                elif new_value.isdigit():
                    formatted_value = str(new_value)
                # 3. Listen
                elif ',' in new_value and not new_value.strip().startswith('{'):
                     # Simple Heuristik: Wenn Komma und keine geschweifte Klammer -> Liste
                     # Das ist nicht perfekt, reicht aber für die einfachen Listen hier
                     items = [f'"{item.strip()}"' for item in new_value.split(',') if item.strip()]
                     formatted_value = f"[{', '.join(items)}]"
                # 4. Dictionaries (JSON-artig)
                elif new_value.strip().startswith('{'):
                    # WICHTIG: Dictionaries werden RAW gespeichert, ohne Anführungszeichen!
                    formatted_value = new_value
                
                # Boolean False Handling für Checkboxen, die NICHT im form_data sind, 
                # wird weiter unten im 'else' Block des var_name Checks gemacht? 
                # Nein, hier iterieren wir über die Datei. Wenn var_name im File ist, 
                # MUSS er im form_data sein, außer es ist eine unchecked Checkbox.
                
                # Korrektur für Checkboxen (Boolean False):
                # HTML Formulare senden unchecked Checkboxen NICHT.
                # Wir müssen erkennen, ob es vorher ein Boolean war.
                # Das ist hier schwierig ohne den alten Typ zu kennen.
                # WORKAROUND: Wir verlassen uns darauf, dass Checkboxen im HTML ein hidden input als Fallback haben
                # oder wir prüfen den String.
                
                # Da wir hier den alten Typ nicht sicher kennen (nur String parsing), 
                # und save_config_file stateless ist, übernehmen wir den Wert so wie er kommt.
                # config_editor.html sollte hidden inputs für booleans nutzen oder wir fangen es ab.
                
                indentation = re.match(r'^\s*', line).group(0)
                new_lines.append(f"{indentation}{var_name} = {formatted_value}{inline_comment}\n")
            
            else:
                # Variable ist im File, aber nicht im POST-Request.
                # Das passiert typischerweise bei unchecked Checkboxen (Boolean False).
                # Wir prüfen, ob der Originalwert nach Boolean aussieht.
                original_val_clean = line.split('=', 1)[1].split('#')[0].strip()
                if original_val_clean.lower() in ['true', 'false']:
                    inline_comment = ' # ' + line.split('#', 1)[1].strip() if '#' in line else ''
                    indentation = re.match(r'^\s*', line).group(0)
                    new_lines.append(f"{indentation}{var_name} = False{inline_comment}\n")
                else:
                    # Wenn es kein Boolean war und fehlt, behalten wir die alte Zeile (sollte nicht passieren)
                    new_lines.append(line)
        else:
            new_lines.append(line)

    with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)


def restart_service():
    """
    Löst einen Neustart des systemd-Dienstes aus, wenn die Anwendung
    als solcher läuft.
    """
    if is_running_as_service():
        try:
            user = os.getenv('USER')
            if user == 'root':
                subprocess.run(["systemctl", "restart", "himues-scoreboard-frontend.service"], check=True)
                return "Dienst wird neu gestartet. Die Seite wird in Kürze neu geladen."
            else:
                user_env = os.environ.copy()
                subprocess.run(
                    ["systemctl", "--user", "restart", "himues-scoreboard-frontend.service"],
                    check=True, env=user_env
                )
                return "Dienst wird neu gestartet. Die Seite wird in Kürze neu geladen."
        except Exception as e:
            logging.error(f"Fehler beim Neustart des Dienstes: {e}")
            return f"Fehler beim Neustart des Dienstes: {e}"
    else:
        return "Konfiguration gespeichert. Bitte starte die Anwendung manuell neu, damit die Änderungen wirksam werden."