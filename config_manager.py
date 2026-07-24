import json
import os
import csv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_DIR = os.path.join(DATA_DIR, "config")
LOGS_DIR = os.path.join(DATA_DIR, "logs")

DATEI_KOMMENTARE = os.path.join(LOGS_DIR, "session_kommentare.csv")
DATEI_AKTIVITAETEN = os.path.join(LOGS_DIR, "session_aktivitaeten.csv")
DATEI_FENSTER = os.path.join(LOGS_DIR, "session_fenster.csv")
DATEI_EVENT_LOGS = os.path.join(LOGS_DIR, "session_events.csv")

DATEI_AKT_LISTE = os.path.join(CONFIG_DIR, "meine_aktivitaeten.txt")
DATEI_VORLAGEN = os.path.join(CONFIG_DIR, "meine_vorlagen.txt")
DATEI_CONFIG = os.path.join(CONFIG_DIR, "einstellungen.json")
DATEI_FAECHER = os.path.join(CONFIG_DIR, "faecher.txt")
DATEI_EVENTS = os.path.join(CONFIG_DIR, "events.txt")

def init_projekt():
    if not os.path.exists(CONFIG_DIR): os.makedirs(CONFIG_DIR)
    if not os.path.exists(LOGS_DIR): os.makedirs(LOGS_DIR)

    standard = {
        "lern_erinnerung_minuten": 25, 
        "eye_tracking_aktiv": False,
        "blick_warnung_aktiv": False
    }

    if not os.path.exists(DATEI_CONFIG):
        with open(DATEI_CONFIG, "w", encoding="utf-8") as f:
            json.dump(standard, f, indent=4)
    
    # Feste Standard-Aktivitäten auf Englisch
    if not os.path.exists(DATEI_AKT_LISTE):
        with open(DATEI_AKT_LISTE, "w", encoding="utf-8") as f:
            f.write("Productivity\nBreak\nLunch\nOther\nAdmin")
            
    if not os.path.exists(DATEI_VORLAGEN):
        with open(DATEI_VORLAGEN, "w", encoding="utf-8") as f:
            f.write("Exam preparation\nHomework\nVocabulary learning\nProject work")
            
    if not os.path.exists(DATEI_FAECHER):
        with open(DATEI_FAECHER, "w", encoding="utf-8") as f:
            f.write("Math\nGerman\nEnglish\nComputer Science")

    if not os.path.exists(DATEI_EVENTS):
        with open(DATEI_EVENTS, "w", encoding="utf-8") as f:
            f.write("Distraction\nFetched coffee\nWrote down question\nSearched material")

    if not os.path.exists(DATEI_EVENT_LOGS):
        with open(DATEI_EVENT_LOGS, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Session_ID", "Activity", "Event", "Timestamp"])

def lade_einstellungen():
    standard = {
        "lern_erinnerung_minuten": 25, 
        "eye_tracking_aktiv": False, 
        "blick_warnung_aktiv": False
    }
    try:
        with open(DATEI_CONFIG, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict): raise ValueError
            
            # Alte Score-Einträge bereinigen, falls vorhanden
            geaendert = False
            for alter_schluessel in ["score_min", "score_max"]:
                if alter_schluessel in data:
                    del data[alter_schluessel]
                    geaendert = True
            if geaendert:
                speichere_einstellungen(data)
                
            return data
    except:
        speichere_einstellungen(standard)
        return standard

def speichere_einstellungen(data):
    with open(DATEI_CONFIG, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)