import csv
from models import Constituency

def load_constituencies(file_path):
    constituencies = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        next(reader)  # Pomiń nagłówek
        for row in reader:
            number = int(row[0])
            size = int(row[1])
            past_support = {
                'td': float(row[2].replace(',', '.')),
                'nl': float(row[3].replace(',', '.')),
                'pis': float(row[4].replace(',', '.')),
                'konf': float(row[5].replace(',', '.')),
                'ko': float(row[6].replace(',', '.')),
            }
            constituencies.append(Constituency(number, size, past_support))
    return constituencies