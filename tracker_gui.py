import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import time
import csv
from datetime import datetime
import os
import ctypes
import json

try:
    from plyer import notification
    PLYER_INSTALLIERT = True
except ImportError:
    PLYER_INSTALLIERT = False

# Tracking-Dateien
DATEI_KOMMENTARE = "session_kommentare.csv"
DATEI_AKTIVITAETEN = "session_aktivitaeten.csv"
DATEI_FENSTER = "session_fenster.csv"

# Konfigurations-Dateien
DATEI_AKT_LISTE = "meine_aktivitaeten.txt"
DATEI_VORLAGEN = "meine_vorlagen.txt"
DATEI_CONFIG = "einstellungen.json"

def lade_einstellungen():
    """Lädt die Einstellungen. Fügt neue Standardwerte hinzu, falls sie fehlen."""
    standard_einstellungen = {
        "lern_erinnerung_minuten": 25,
        "score_min": 1,
        "score_max": 5
    }
    
    if not os.path.exists(DATEI_CONFIG):
        with open(DATEI_CONFIG, "w", encoding="utf-8") as f:
            json.dump(standard_einstellungen, f, indent=4)
        return standard_einstellungen
    else:
        try:
            with open(DATEI_CONFIG, "r", encoding="utf-8") as f:
                geladen = json.load(f)
                # Prüfen, ob alle Standard-Schlüssel vorhanden sind (für Updates)
                fehlende_keys = False
                for key, val in standard_einstellungen.items():
                    if key not in geladen:
                        geladen[key] = val
                        fehlende_keys = True
                
                # Wenn neue Keys hinzugefügt wurden, direkt abspeichern
                if fehlende_keys:
                    with open(DATEI_CONFIG, "w", encoding="utf-8") as f:
                        json.dump(geladen, f, indent=4)
                        
                return geladen
        except Exception:
            return standard_einstellungen

def setup_dateien():
    if not os.path.exists(DATEI_KOMMENTARE):
        with open(DATEI_KOMMENTARE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Session_ID", "Datum", "Kommentar"])
            
    if not os.path.exists(DATEI_AKTIVITAETEN):
        with open(DATEI_AKTIVITAETEN, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Session_ID", "Aktivitaet", "Start_Uhrzeit", "Dauer_Minuten", "Score"])

    if not os.path.exists(DATEI_FENSTER):
        with open(DATEI_FENSTER, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Session_ID", "Aktivitaet", "Programm", "Fenster_Titel", "Dauer_Sekunden"])

    if not os.path.exists(DATEI_AKT_LISTE):
        schreibe_textdatei(DATEI_AKT_LISTE, ["Lernen", "Pause", "Mittag", "Sonstiges", "Orga"])
            
    if not os.path.exists(DATEI_VORLAGEN):
        schreibe_textdatei(DATEI_VORLAGEN, ["Klausurvorbereitung", "Hausaufgaben", "Vokabeln lernen", "Projektarbeit"])

def lese_textdatei(dateiname):
    werte = []
    if os.path.exists(dateiname):
        with open(dateiname, "r", encoding="utf-8") as f:
            for zeile in f:
                bereinigt = zeile.strip()
                if bereinigt:
                    werte.append(bereinigt)
    return werte

def schreibe_textdatei(dateiname, liste):
    with open(dateiname, "w", encoding="utf-8") as f:
        for item in liste:
            f.write(f"{item}\n")

def hole_aktives_fenster_info():
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd: return "Unbekannt", "Desktop / Unbekannt"
        
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        titel = buf.value.strip() or "Ohne Titel"

        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        h_process = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        
        programm_name = "System/Unbekannt"
        if h_process:
            exe_path_buf = ctypes.create_unicode_buffer(260)
            size = ctypes.c_ulong(260)
            if ctypes.windll.kernel32.QueryFullProcessImageNameW(h_process, 0, exe_path_buf, ctypes.byref(size)):
                programm_name = os.path.basename(exe_path_buf.value) 
            ctypes.windll.kernel32.CloseHandle(h_process)
        return programm_name, titel
    except Exception:
        return "Fehler", "Fehler beim Lesen"

class FlowTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Flow Tracker")
        self.root.geometry("550x650") 
        self.root.eval('tk::PlaceWindow . center')
        
        self.root.protocol("WM_DELETE_WINDOW", self.beim_schliessen)
        setup_dateien()
        self.einstellungen = lade_einstellungen()
        
        self.session_id = ""
        self.aktuelle_aktivitaet = None
        self.aktivitaet_startzeit = 0
        self.aktivitaet_start_uhrzeit = ""
        self.timer_laeuft = False
        self.erinnerung_gesendet = False 
        self.fenster_zeiten = {}
        
        # Alle Frames (Ansichten) anlegen
        self.home_frame = tk.Frame(self.root)
        self.settings_frame = tk.Frame(self.root)
        self.kommentar_frame = tk.Frame(self.root)
        self.haupt_frame = tk.Frame(self.root)
        
        # UI Elemente in den Frames bauen
        self.erstelle_home_ui()
        self.erstelle_settings_ui()
        self.erstelle_kommentar_ui()
        # Das Haupt-UI wird dynamisch beim Starten einer Session aufgebaut,
        # da es die aktuellen Aktivitäten laden muss.
        
        # Startansicht anzeigen
        self.zeige_frame(self.home_frame)

    def zeige_frame(self, frame_anzeigen):
        """Versteckt alle Frames und zeigt nur das gewünschte an."""
        for frame in [self.home_frame, self.settings_frame, self.kommentar_frame, self.haupt_frame]:
            frame.pack_forget()
        frame_anzeigen.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

    # --- 1. HOME SCREEN ---
    def erstelle_home_ui(self):
        tk.Label(self.home_frame, text="🧠 Flow Tracker", font=("Helvetica", 28, "bold")).pack(pady=(50, 40))
        
        tk.Button(self.home_frame, text="▶ Session Starten", font=("Helvetica", 14), bg="lightgreen", width=20, height=2,
                  command=lambda: self.zeige_frame(self.kommentar_frame)).pack(pady=10)
                  
        tk.Button(self.home_frame, text="⚙️ Einstellungen", font=("Helvetica", 14), bg="lightgray", width=20, height=2,
                  command=lambda: self.zeige_frame(self.settings_frame)).pack(pady=10)

    # --- 2. EINSTELLUNGEN ---
    def erstelle_settings_ui(self):
        tk.Label(self.settings_frame, text="Einstellungen", font=("Helvetica", 20, "bold")).pack(pady=(0, 10))
        
        # Notebook für Tabs
        self.notebook = ttk.Notebook(self.settings_frame)
        self.notebook.pack(expand=True, fill=tk.BOTH, pady=10)
        
        # Tabs erstellen
        self.tab_allg = tk.Frame(self.notebook, padx=10, pady=10)
        self.tab_akt = tk.Frame(self.notebook, padx=10, pady=10)
        self.tab_vorl = tk.Frame(self.notebook, padx=10, pady=10)
        
        self.notebook.add(self.tab_allg, text="Allgemein (Werte)")
        self.notebook.add(self.tab_akt, text="Aktivitäten")
        self.notebook.add(self.tab_vorl, text="Vorlagen")
        
        # -- Tab 1: Allgemein (Variablen) --
        self.setting_entries = {}
        row = 0
        for key, val in self.einstellungen.items():
            # Schlüssel formatieren (z.B. "lern_erinnerung_minuten" -> "Lern Erinnerung Minuten")
            anzeige_name = key.replace("_", " ").title() + ":"
            tk.Label(self.tab_allg, text=anzeige_name, font=("Helvetica", 12)).grid(row=row, column=0, sticky="w", pady=10)
            
            entry = tk.Entry(self.tab_allg, font=("Helvetica", 12), width=10)
            entry.insert(0, str(val))
            entry.grid(row=row, column=1, padx=20, pady=10)
            self.setting_entries[key] = entry
            row += 1
            
        tk.Button(self.tab_allg, text="💾 Variablen Speichern", bg="lightblue", font=("Helvetica", 10),
                  command=self.speichere_variablen).grid(row=row, column=0, columnspan=2, pady=20)
                  
        # -- Tab 2 & 3: Listen-Manager (Aktivitäten und Vorlagen) --
        self.baue_listen_manager(self.tab_akt, DATEI_AKT_LISTE)
        self.baue_listen_manager(self.tab_vorl, DATEI_VORLAGEN)
        
        # Zurück Button (unten)
        tk.Button(self.settings_frame, text="⬅ Zurück zum Home", font=("Helvetica", 12), 
                  command=lambda: self.zeige_frame(self.home_frame)).pack(pady=10)

    def baue_listen_manager(self, tab, dateiname):
        """Baut ein Listbox-UI mit Hinzufügen/Löschen für Textdateien."""
        listbox = tk.Listbox(tab, font=("Helvetica", 12), height=10, selectmode=tk.EXTENDED)
        listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Liste füllen
        werte = lese_textdatei(dateiname)
        for w in werte: listbox.insert(tk.END, w)
            
        eingabe_frame = tk.Frame(tab)
        eingabe_frame.pack(fill=tk.X, pady=5)
        
        entry_neu = tk.Entry(eingabe_frame, font=("Helvetica", 12))
        entry_neu.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        
        def hinzufuegen():
            wert = entry_neu.get().strip()
            if wert:
                listbox.insert(tk.END, wert)
                entry_neu.delete(0, tk.END)
                self.speichere_liste(dateiname, listbox)
                
        def loeschen():
            # Rückwärts löschen, damit sich die Indizes nicht verschieben
            auswahl = listbox.curselection()
            for i in reversed(auswahl):
                listbox.delete(i)
            self.speichere_liste(dateiname, listbox)

        entry_neu.bind("<Return>", lambda e: hinzufuegen())
        tk.Button(eingabe_frame, text="Hinzufügen", command=hinzufuegen).pack(side=tk.LEFT)
        tk.Button(tab, text="Ausgewählte löschen", fg="red", command=loeschen).pack(pady=5)

    def speichere_variablen(self):
        for key, entry in self.setting_entries.items():
            wert = entry.get()
            try:
                # Alle aktuellen Variablen sind Zahlen
                self.einstellungen[key] = int(wert) 
            except ValueError:
                messagebox.showerror("Fehler", f"Bitte für '{key}' nur ganze Zahlen eingeben!")
                return
                
        with open(DATEI_CONFIG, "w", encoding="utf-8") as f:
            json.dump(self.einstellungen, f, indent=4)
        messagebox.showinfo("Erfolg", "Einstellungen wurden gespeichert!")

    def speichere_liste(self, dateiname, listbox):
        werte = listbox.get(0, tk.END)
        schreibe_textdatei(dateiname, werte)

    # --- 3. SESSION KOMMENTAR ---
    def erstelle_kommentar_ui(self):
        tk.Label(self.kommentar_frame, text="Neues Lern-Vorhaben:", font=("Helvetica", 14, "bold")).pack(pady=(10, 20))
        tk.Label(self.kommentar_frame, text="Wähle eine Vorlage oder tippe selbst:").pack()
        
        self.entry_kommentar = ttk.Combobox(self.kommentar_frame, font=("Helvetica", 12), width=30)
        self.entry_kommentar.pack(pady=10)
        self.entry_kommentar.bind("<Return>", lambda event: self.starte_session())
        
        tk.Button(self.kommentar_frame, text="🚀 Timer Starten", bg="lightblue", font=("Helvetica", 12), 
                  command=self.starte_session).pack(pady=20)
                  
        tk.Button(self.kommentar_frame, text="Abbrechen", font=("Helvetica", 10), 
                  command=lambda: self.zeige_frame(self.home_frame)).pack()

    def starte_session(self):
        kommentar = self.entry_kommentar.get().strip()
        if not kommentar:
            messagebox.showwarning("Fehlt", "Bitte gib einen Kommentar ein oder wähle einen aus.")
            return
            
        jetzt = datetime.now()
        self.session_id = jetzt.strftime("%Y%m%d_%H%M%S")
        datum = jetzt.strftime("%Y-%m-%d")
        
        with open(DATEI_KOMMENTARE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([self.session_id, datum, kommentar])
            
        self.erstelle_haupt_ui() # Baut das Timer UI frisch auf (mit ggf. neuen Buttons)
        self.zeige_frame(self.haupt_frame)

    # --- 4. SESSION TIMER ---
    def erstelle_haupt_ui(self):
        # Altes Timer UI löschen, falls wir eine zweite Session am selben Tag starten
        for widget in self.haupt_frame.winfo_children():
            widget.destroy()
            
        self.lbl_status = tk.Label(self.haupt_frame, text="Klicke eine Aktivität, um zu starten", font=("Helvetica", 12), fg="gray")
        self.lbl_status.pack(pady=(0, 10))
        
        self.lbl_timer = tk.Label(self.haupt_frame, text="00:00", font=("Helvetica", 48, "bold"))
        self.lbl_timer.pack(pady=10)
        
        self.lbl_benachrichtigung = tk.Label(self.haupt_frame, text="", font=("Helvetica", 10, "bold"), fg="red")
        self.lbl_benachrichtigung.pack(pady=5)
        
        btn_frame = tk.Frame(self.haupt_frame)
        btn_frame.pack(pady=20)
        
        self.buttons = {}
        aktivitaeten = lese_textdatei(DATEI_AKT_LISTE)
        
        # Flexibles Raster für Buttons (egal ob 4, 5 oder 10 Aktivitäten)
        spalten = 2
        for i, akt in enumerate(aktivitaeten):
            btn = tk.Button(btn_frame, text=akt, font=("Helvetica", 12), width=12, height=2,
                            command=lambda a=akt: self.wechsle_aktivitaet(a))
            row = i // spalten
            col = i % spalten
            btn.grid(row=row, column=col, padx=5, pady=5)
            self.buttons[akt] = btn
            
        tk.Button(self.haupt_frame, text="⏹ Session komplett beenden", fg="red", font=("Helvetica", 10),
                  command=self.session_beenden).pack(pady=30)

    def wechsle_aktivitaet(self, neue_aktivitaet):
        if neue_aktivitaet == self.aktuelle_aktivitaet:
            return
            
        if self.aktuelle_aktivitaet is not None:
            self.speichere_aktuelle_aktivitaet()
            
        self.aktuelle_aktivitaet = neue_aktivitaet
        self.aktivitaet_startzeit = time.time()
        self.aktivitaet_start_uhrzeit = datetime.now().strftime("%H:%M:%S")
        self.fenster_zeiten = {}
        self.erinnerung_gesendet = False
        self.lbl_benachrichtigung.config(text="")
        self.einstellungen = lade_einstellungen() # Immer frisch laden
        
        self.lbl_status.config(text=f"Aktuell: {neue_aktivitaet}", fg="black", font=("Helvetica", 12, "bold"))
        self.lbl_timer.config(text="00:00")
        
        for name, btn in self.buttons.items():
            if name == neue_aktivitaet:
                btn.config(bg="lightgreen")
            else:
                btn.config(bg="SystemButtonFace")
                
        if not self.timer_laeuft:
            self.timer_laeuft = True
            self.aktualisiere_timer()

    def speichere_aktuelle_aktivitaet(self):
        end_zeit = time.time()
        dauer_sekunden = end_zeit - self.aktivitaet_startzeit
        dauer_minuten = round(dauer_sekunden / 60, 2)
        score = ""
        
        if "lernen" in self.aktuelle_aktivitaet.lower():
            s_min = self.einstellungen.get("score_min", 1)
            s_max = self.einstellungen.get("score_max", 5)
            
            # askinteger ist perfekt hierfür, da es min/max validiert und bei Fehlern selbst meckert
            abfrage = simpledialog.askinteger("Score", 
                                              f"Wie fokussiert war dieses Lernen?\n(Zahl von {s_min} bis {s_max})", 
                                              minvalue=s_min, maxvalue=s_max, parent=self.root)
            if abfrage is not None:
                score = abfrage
            
        with open(DATEI_AKTIVITAETEN, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([self.session_id, self.aktuelle_aktivitaet, self.aktivitaet_start_uhrzeit, dauer_minuten, score])

        with open(DATEI_FENSTER, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for (programm, titel), sekunden in self.fenster_zeiten.items():
                if sekunden > 0:
                    writer.writerow([self.session_id, self.aktuelle_aktivitaet, programm, titel, sekunden])

    def sende_erinnerung(self, minuten):
        nachricht = f"Du lernst schon seit {minuten} Minuten.\nZeit für eine kurze Pause!"
        self.lbl_benachrichtigung.config(text="⏰ " + nachricht)
        
        if PLYER_INSTALLIERT:
            try:
                notification.notify(
                    title="Flow Tracker Erinnerung", message=nachricht,
                    app_name="Flow Tracker", timeout=10
                )
            except Exception: pass

    def aktualisiere_timer(self):
        if not self.timer_laeuft: return
        
        vergangen_sekunden = int(time.time() - self.aktivitaet_startzeit)
        minuten = vergangen_sekunden // 60
        sekunden = vergangen_sekunden % 60
        
        if minuten >= 60:
            self.lbl_timer.config(text=f"{minuten//60:02d}:{minuten%60:02d}:{sekunden:02d}")
        else:
            self.lbl_timer.config(text=f"{minuten:02d}:{sekunden:02d}")
            
        if "lernen" in self.aktuelle_aktivitaet.lower():
            ziel_minuten = self.einstellungen.get("lern_erinnerung_minuten", 25)
            if minuten >= ziel_minuten and not self.erinnerung_gesendet:
                self.sende_erinnerung(ziel_minuten)
                self.erinnerung_gesendet = True
            
        programm, titel = hole_aktives_fenster_info()
        schluessel = (programm, titel)
        self.fenster_zeiten[schluessel] = self.fenster_zeiten.get(schluessel, 0) + 1
            
        self.root.after(1000, self.aktualisiere_timer)

    def session_beenden(self):
        """Stoppt den Timer und geht zurück zum Home Menü."""
        if self.aktuelle_aktivitaet is not None:
            self.speichere_aktuelle_aktivitaet()
            
        self.timer_laeuft = False
        self.aktuelle_aktivitaet = None
        self.zeige_frame(self.home_frame)
        messagebox.showinfo("Session Beendet", "Deine Session wurde gespeichert. Gute Arbeit!")

    def beim_schliessen(self):
        if self.aktuelle_aktivitaet is not None:
            self.speichere_aktuelle_aktivitaet()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    # Damit die Combobox (Vorlagen) beim Klick auf "Session starten" aktuell ist:
    app = FlowTrackerApp(root)
    # Bevor wir die UI laden, sorgen wir dafür, dass die Vorlagen immer frisch geladen werden
    app.entry_kommentar.config(values=lese_textdatei(DATEI_VORLAGEN))
    root.mainloop()