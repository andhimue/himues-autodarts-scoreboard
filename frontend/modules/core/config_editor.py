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
    für die dynamische Formular-Generierung.
    """
    structure = []
    current_section = None
    is_next_line_hidden = False

    with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    def finalize_section(section):
        if section and section.get('variables'):
            structure.append(section)

    for line in lines:
        line = line.strip()

        if line.startswith('# @hidden'):
            is_next_line_hidden = True
            continue

        if is_next_line_hidden:
            is_next_line_hidden = False
            continue

        if not line or line.startswith('import') or '.py' in line:
            finalize_section(current_section)
            current_section = None
            continue

        if line.startswith('# '):
            header_text = line.strip('# ').strip()
            if current_section and current_section.get('type') == 'section' and not current_section.get('variables'):
                current_section['title'] += ' ' + header_text
            else:
                finalize_section(current_section)
                current_section = {'type': 'section', 'title': header_text, 'variables': []}
            continue
        
        match = re.match(r'^([A-Z_][A-Z0-9_]*)\s*=\s*(.*)', line)
        if match:
            var_name = match.group(1)
            raw_value = match.group(2).strip()
            
            inline_comment = ''
            if '#' in raw_value:
                parts = raw_value.split('#', 1)
                raw_value = parts[0].strip()
                inline_comment = parts[1].strip()

            value_type = 'string'
            if raw_value.lower() in ['true', 'false']:
                value_type = 'boolean'
                value = raw_value.lower() == 'true'
            elif raw_value.isdigit():
                value_type = 'integer'
                value = int(raw_value)
            elif raw_value.startswith('[') and raw_value.endswith(']'):
                value_type = 'list'
                value = raw_value.strip('[]').replace('"', '').replace("'", "")
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
    Speichert die Formulardaten zurück in die config_frontend.py und
    behält dabei Kommentare und Struktur bei.
    """
    with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        match = re.match(r'^([A-Z_][A-Z0-9_]*)\s*=', line.strip())
        if match:
            var_name = match.group(1)
            original_value = line.split('=', 1)[1].split('#')[0].strip()

            if var_name in form_data:
                new_value = form_data.get(var_name)
                
                inline_comment = ''
                if '#' in line:
                    inline_comment = ' # ' + line.split('#', 1)[1].strip()
                
                if original_value.lower() in ['true', 'false']:
                    formatted_value = 'True' if new_value == 'on' else 'False'
                elif original_value.isdigit():
                    formatted_value = str(new_value)
                elif original_value.startswith('['):
                    items = [f'"{item.strip()}"' for item in new_value.split(',') if item.strip()]
                    formatted_value = f"[{', '.join(items)}]"
                else:
                    formatted_value = f'"{new_value}"'
                
                indentation = re.match(r'^\s*', line).group(0)
                new_lines.append(f"{indentation}{var_name} = {formatted_value}{inline_comment}\n")
            else:
                if original_value.lower() in ['true', 'false']:
                    inline_comment = ' # ' + line.split('#', 1)[1].strip() if '#' in line else ''
                    indentation = re.match(r'^\s*', line).group(0)
                    new_lines.append(f"{indentation}{var_name} = False{inline_comment}\n")
                else:
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