import json

# Namen für die Eingabe- und Ausgabedateien
input_filename = 'match-data.json'
output_filename = 'output_formatted.json'

print(f"Lese Daten aus '{input_filename}'...")
print(f"Schreibe formatierte Daten in '{output_filename}'...")

# Öffne beide Dateien gleichzeitig
# 'encoding="utf-8"' ist wichtig, falls Umlaute oder andere Sonderzeichen vorkommen
with open(input_filename, 'r', encoding='utf-8') as infile, \
     open(output_filename, 'w', encoding='utf-8') as outfile:
    
    # Gehe die Eingabedatei Zeile für Zeile durch
    for line in infile:
        # Überspringe leere Zeilen, falls vorhanden
        if not line.strip():
            continue

        try:
            # 1. Lade den JSON-String aus der Zeile in ein Python-Dictionary
            data = json.loads(line)
            data['data']['host'] = {}
            # 2. Wandle das Python-Dictionary zurück in einen formatierten JSON-String
            #    - indent=4 sorgt für die schöne Einrückung mit 4 Leerzeichen
            #    - ensure_ascii=False stellt sicher, dass Umlaute (ä, ö, ü) korrekt dargestellt werden
            formatted_json = json.dumps(data, indent=4, ensure_ascii=False)

            # 3. Schreibe den formatierten String in die Ausgabedatei
            outfile.write(formatted_json)
            
            # Füge eine neue Zeile hinzu, um die JSON-Objekte zu trennen
            outfile.write('\n############################\n')

        except json.JSONDecodeError:
            print(f"Warnung: Eine Zeile konnte nicht als JSON geparst werden und wurde übersprungen:\n{line}")

print("Fertig! ✅")
