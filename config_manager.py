import os
import json

# Fester Pfad im Benutzerverzeichnis (unabhängig davon, wo die .exe liegt!)
# Entspricht z.B. C:\Users\DeinName\FlowTrackerData unter Windows
BASE_DIR = os.path.join(os.path.expanduser("~"), "FlowTrackerData")

# Alle Dateien werden fest mit diesem Ordner verknüpft
DATEI_EINSTELLUNGEN = os.path.join(BASE_DIR, "einstellungen.json")
DATEI_KOMMENTARE = os.path.join(BASE_DIR, "kommentare.csv")
DATEI_AKTIVITAETEN = os.path.join(BASE_DIR, "aktivitaeten.csv")
DATEI_FENSTER = os.path.join(BASE_DIR, "fenster.csv")
DATEI_AKT_LISTE = os.path.join(BASE_DIR, "aktivitaeten_liste.txt")
DATEI_VORLAGEN = os.path.join(BASE_DIR, "vorlagen.txt")
DATEI_FAECHER = os.path.join(BASE_DIR, "faecher.txt")
DATEI_EVENTS = os.path.join(BASE_DIR, "events.txt")
DATEI_EVENT_LOGS = os.path.join(BASE_DIR, "event_logs.csv")

def init_projekt():
    # 1. Prüfen und Erstellen des Hauptordners, falls er nicht existiert
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)

    # 2. Standard-Textdateien mit Startwerten füllen, falls sie neu sind
    standard_aktivitaeten = "Productivity\nBreak\nLunch\n"
    standard_vorlagen = "Deep Work\nCoding Session\nExam Prep\n"
    standard_faecher = "Math\nProgramming\nPhysics\n"
    standard_events = "Coffee Break\nDistraction\nPhone Call\n"

    dateien_standards = [
        (DATEI_AKT_LISTE, standard_aktivitaeten),
        (DATEI_VORLAGEN, standard_vorlagen),
        (DATEI_FAECHER, standard_faecher),
        (DATEI_EVENTS, standard_events)
    ]

    for dateipfad, inhalt in dateien_standards:
        if not os.path.exists(dateipfad):
            with open(dateipfad, "w", encoding="utf-8") as f:
                f.write(inhalt)

    # 3. Einstellungen initialisieren, falls nicht vorhanden
    if not os.path.exists(DATEI_EINSTELLUNGEN):
        standard_einstellungen = {
            "lern_erinnerung_minuten": 45,
            "pausenbenachrichtigung": True,
            "aktivitaetentracker": True
        }
        speichere_einstellungen(standard_einstellungen)

def lade_einstellungen():
    if os.path.exists(DATEI_EINSTELLUNGEN):
        try:
            with open(DATEI_EINSTELLUNGEN, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {
        "lern_erinnerung_minuten": 25,
        "pausenbenachrichtigung": True,
        "aktivitaetentracker": False
    }

def speichere_einstellungen(einstellungen):
    with open(DATEI_EINSTELLUNGEN, "w", encoding="utf-8") as f:
        json.dump(einstellungen, f, indent=4)