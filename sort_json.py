import json

def sortiere_konten(kontenplan):
    kontenplan["Konten"] = sorted(kontenplan["Konten"], key=lambda k: k["Kontonummer"])

def sortiere_kontenplaene(kontenplaene):
    for kontenplan in kontenplaene:
        sortiere_konten(kontenplan)

def sortiere_und_speichere_json(dateipfad):
    with open(dateipfad, 'r') as f:
        data = json.load(f)
    sortiere_kontenplaene(data["Kontoplan"])
    with open(dateipfad, 'w') as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    sortiere_und_speichere_json('kontoplan.json')
