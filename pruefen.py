"""Prüft Kundendaten und trennt gültige von fehlerhaften Zeilen."""
import argparse
import csv
import json
import re
from pathlib import Path

FIELDS = ['kunden_id', 'name', 'email', 'umsatz_eur']


def pruefen(source, output):
    # Erst vollständig lesen und Schema prüfen, dann Ergebnisse schreiben.
    with source.open(encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file, delimiter=';')
        if reader.fieldnames != FIELDS:
            raise ValueError('Erwartete Spalten in dieser Reihenfolge: ' + ';'.join(FIELDS))
        rows = list(reader)
    output.mkdir(parents=True, exist_ok=True)
    seen = set()
    good, bad = [], []
    for number, raw in enumerate(rows, 2):
        row = {key: (raw.get(key) or '').strip() for key in FIELDS}
        errors = []
        if None in raw or any(raw.get(key) is None for key in FIELDS):
            errors.append('Falsche Anzahl von Feldern')
        if not row['kunden_id']:
            errors.append('Kunden-ID fehlt')
        elif row['kunden_id'] in seen:
            errors.append('Doppelte Kunden-ID')
        if row['kunden_id']:
            seen.add(row['kunden_id'])
        if not row['name']:
            errors.append('Name fehlt')
        row['email'] = row['email'].lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', row['email']):
            errors.append('E-Mail-Format ungültig')
        amount = row['umsatz_eur'].replace(',', '.')
        if not re.fullmatch(r'\d+(?:\.\d{1,2})?', amount):
            errors.append('Umsatz muss eine nichtnegative Zahl mit maximal zwei Nachkommastellen sein')
        else:
            euros, _, cents = amount.partition('.')
            row['umsatz_eur'] = str(int(euros)) + '.' + cents.ljust(2, '0')
        if errors:
            bad.append({'datensatz': number, 'fehler': ' | '.join(errors),
                        'original_json': json.dumps(raw, ensure_ascii=False)})
        else:
            good.append(row)
    for name, fields, records in [
        ('bereinigt.csv', FIELDS, good),
        ('fehler.csv', ['datensatz', 'fehler', 'original_json'], bad),
    ]:
        with (output / name).open('w', encoding='utf-8-sig', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fields, delimiter=';')
            writer.writeheader()
            writer.writerows(records)
    summary = {'gesamt': len(rows), 'gueltig': len(good), 'abgelehnt': len(bad)}
    (output / 'bericht.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('datei', type=Path)
    parser.add_argument('--ausgabe', type=Path, default=Path('ausgabe'))
    args = parser.parse_args()
    # Verhindert das Überschreiben einer Eingabedatei durch eine Ausgabedatei.
    targets = [args.ausgabe / n for n in ('bereinigt.csv', 'fehler.csv', 'bericht.json')]
    if args.datei.resolve() in [p.resolve() for p in targets]:
        parser.error('Eingabe und Ausgabe dürfen nicht dieselbe Datei sein.')
    try:
        print(json.dumps(pruefen(args.datei, args.ausgabe), ensure_ascii=False))
    except (OSError, ValueError, csv.Error) as error:
        parser.exit(1, f'Fehler: {error}\n')


if __name__ == '__main__':
    main()
