import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import time, csv, os
from datetime import datetime, timedelta
import config_manager as cm
import utils
import analytics
import eye_tracker

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

try:
    from plyer import notification
    PLYER_INSTALLIERT = True
except: 
    PLYER_INSTALLIERT = False

try:
    from pynput import keyboard, mouse
    PYNPUT_INSTALLIERT = True
except: 
    PYNPUT_INSTALLIERT = False

SCORE_MIN = 1
SCORE_MAX = 5
GESCHUETZTE_AKTIVITAETEN = ["Productivity", "Break", "Lunch"]
AKTUELLE_VERSION = "v1.0.0"
GITHUB_REPO = "DEIN_GITHUB_USER/DEIN_REPO_NAME"

class FlowTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Flow Tracker")
        
        window_width, window_height = 550, 840
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (window_width // 2)
        self.root.geometry(f"{window_width}x{window_height}+{x}+20")
        
        cm.init_projekt()
        self.einstellungen = cm.lade_einstellungen()
        
        if "pausenbenachrichtigung" not in self.einstellungen:
            self.einstellungen["pausenbenachrichtigung"] = True
        if "aktivitaetentracker" not in self.einstellungen:
            self.einstellungen["aktivitaetentracker"] = True
        if "tastatur_tracker" not in self.einstellungen:
            self.einstellungen["tastatur_tracker"] = False
        if "mousetracker" not in self.einstellungen:
            self.einstellungen["mousetracker"] = False
        if "eyetracker" not in self.einstellungen:
            self.einstellungen["eyetracker"] = False
        if "eyetracker_energysparmodus" not in self.einstellungen:
            self.einstellungen["eyetracker_energysparmodus"] = False
        
        self.session_id = ""
        self.aktuelle_aktivitaet = None
        self.aktivitaet_startzeit = 0
        self.timer_laeuft = False
        self.erinnerung_gesendet = False
        self.fenster_zeiten = {}
        self.letztes_fach = ""  # <--- NEU: Speichert das zuletzt gewählte Fach
        
        self.kb_listener = None
        self.last_key_time = 0
        self.keystroke_count = 0
        self.typing_pauses = 0
        self.kb_intervals = []

        self.mouse_listener = None
        self.click_count = 0
        self.scroll_count = 0
        self.mouse_move_count = 0

        self.eye_manager = None
        
        self.home_frame = tk.Frame(self.root)
        self.settings_frame = tk.Frame(self.root)
        self.kommentar_frame = tk.Frame(self.root)
        self.haupt_frame = tk.Frame(self.root)
        self.analysis_frame = tk.Frame(self.root)
        
        self.current_subject_details = {}
        
        self.erstelle_home_ui()
        self.erstelle_settings_ui()
        self.erstelle_kommentar_ui()
        self.erstelle_analysis_ui()
        
        self.zeige_frame(self.home_frame)
        self.root.protocol("WM_DELETE_WINDOW", self.beim_schliessen)

    def zeige_frame(self, frame_anzeigen):
        for frame in [self.home_frame, self.settings_frame, self.kommentar_frame, self.haupt_frame, self.analysis_frame]:
            frame.pack_forget()
        frame_anzeigen.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
        if frame_anzeigen == self.kommentar_frame:
            self.entry_kommentar['values'] = utils.lese_textdatei(cm.DATEI_VORLAGEN)
        elif frame_anzeigen == self.analysis_frame:
            self.aktualisiere_analysen_anzeige()

    def starte_update_pruefung(self):
        import threading
        threading.Thread(target=self._check_github_for_updates, daemon=True).start()

    def _check_github_for_updates(self):
        try:
            import urllib.request
            import json
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(url, headers={'User-Agent': 'FlowTracker-App'})
            with urllib.request.urlopen(req, timeout=4) as response:
                data = json.loads(response.read().decode())
                latest_tag = data.get("tag_name", "")
                self.latest_release_url = data.get("html_url", "")
                if latest_tag and latest_tag != AKTUELLE_VERSION:
                    self.root.after(0, lambda: self.zeige_update_button(latest_tag))
        except Exception:
            pass

    def zeige_update_button(self, new_version):
        if hasattr(self, 'btn_update') and self.btn_update.winfo_exists():
            self.btn_update.config(text=f"🚀 Update verfügbar ({new_version})!")
            self.btn_update.pack(before=self.home_buttons_frame, pady=5)

    def erstelle_home_ui(self):
        tk.Label(self.home_frame, text="🧠 Flow Tracker", font=("Helvetica", 28, "bold")).pack(pady=20)
        
        self.home_buttons_frame = tk.Frame(self.home_frame)
        self.home_buttons_frame.pack(pady=10)
        
        tk.Button(self.home_buttons_frame, text="▶ Start Session", font=("Helvetica", 14), bg="lightgreen", width=20, height=2,
                  command=lambda: self.zeige_frame(self.kommentar_frame)).pack(pady=10)
        
        tk.Button(self.home_buttons_frame, text="📊 Data Analysis", font=("Helvetica", 14), bg="lightblue", width=20, height=2,
                  command=lambda: self.zeige_frame(self.analysis_frame)).pack(pady=10)
                  
        tk.Button(self.home_buttons_frame, text="⚙️ Settings", font=("Helvetica", 14), bg="lightgray", width=20, height=2,
                  command=lambda: self.zeige_frame(self.settings_frame)).pack(pady=10)

        import webbrowser
        self.btn_update = tk.Button(
            self.home_frame, 
            text="", 
            font=("Helvetica", 12, "bold"), 
            bg="#ffcc00", 
            fg="#333", 
            width=25, 
            height=2,
            command=lambda: webbrowser.open(getattr(self, 'latest_release_url', 'https://github.com/' + GITHUB_REPO + '/releases'))
        )
        self.starte_update_pruefung()

    def erstelle_settings_ui(self):
        for w in self.settings_frame.winfo_children(): w.destroy()
        
        top_header = tk.Frame(self.settings_frame)
        top_header.pack(fill=tk.X, pady=(0, 5))
        
        tk.Button(top_header, text="⬅ Back", command=lambda: self.zeige_frame(self.home_frame), width=8, font=("Helvetica", 9), bg="lightgray").pack(side=tk.LEFT)
        tk.Label(top_header, text="Settings", font=("Helvetica", 14, "bold")).pack(side=tk.LEFT, padx=10)
        
        settings_canvas_wrapper = tk.Frame(self.settings_frame)
        settings_canvas_wrapper.pack(expand=True, fill=tk.BOTH, pady=5)
        
        canvas = tk.Canvas(settings_canvas_wrapper, highlightthickness=0)
        scrollbar = tk.Scrollbar(settings_canvas_wrapper, orient="vertical", command=canvas.yview)
        
        container = tk.Frame(canvas)
        container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._bind_mousewheel(settings_canvas_wrapper, canvas)
        
        def create_accordion_section(title, builder_func):
            section_frame = tk.Frame(container, bd=1, relief=tk.SOLID, bg="#f0f0f0")
            section_frame.pack(fill=tk.X, padx=5, pady=5)
            
            header_btn = tk.Button(
                section_frame, 
                text=f"▶  {title}", 
                font=("Helvetica", 10, "bold"), 
                anchor="w", 
                bg="#e0e0e0", 
                relief=tk.FLAT,
                padx=10, pady=8
            )
            header_btn.pack(fill=tk.X)
            
            content_frame = tk.Frame(section_frame, padx=10, pady=10, bg="white")
            is_open = [False]
            
            def toggle():
                if is_open[0]:
                    content_frame.pack_forget()
                    header_btn.config(text=f"▶  {title}")
                    is_open[0] = False
                else:
                    content_frame.pack(fill=tk.BOTH, expand=True)
                    header_btn.config(text=f"▼  {title}")
                    is_open[0] = True
                canvas.configure(scrollregion=canvas.bbox("all"))
                
            header_btn.config(command=toggle)
            builder_func(content_frame)

        def build_general(parent):
            self.setting_widgets = {}
            setting_labels = {
                "lern_erinnerung_minuten": "Break Reminder Minutes",
                "pausenbenachrichtigung": "Break Notification",
                "aktivitaetentracker": "Window Activity",
                "tastatur_tracker": "Keyboard Activity Tracker",
                "mousetracker": "Mouse Activity Tracker",
                "eyetracker": "Webcam Eye Tracker",
                "eyetracker_energysparmodus": "Eye Tracker Energy Saving Mode"
            }
            for i, (k, v) in enumerate(self.einstellungen.items()):
                display_name = setting_labels.get(k, k.replace("_", " ").title())
                tk.Label(parent, text=display_name+":", bg="white", font=("Helvetica", 9)).grid(row=i, column=0, sticky="nw", padx=5, pady=5)
                
                right_frame = tk.Frame(parent, bg="white")
                right_frame.grid(row=i, column=1, sticky="w", padx=5, pady=5)
                
                if isinstance(v, bool):
                    cb = ttk.Combobox(right_frame, values=["True", "False"], state="readonly", width=12)
                    cb.set(str(v))
                    cb.pack(side=tk.TOP, anchor="w")
                    self.setting_widgets[k] = cb
                    if k == "aktivitaetentracker":
                        tk.Label(right_frame, text="Tracks active windows & application titles", font=("Helvetica", 8), fg="gray", bg="white").pack(side=tk.TOP, anchor="w", pady=(2, 0))
                    elif k == "tastatur_tracker":
                        tk.Label(right_frame, text="Measures typing speed & pauses (No keylogging)", font=("Helvetica", 8), fg="gray", bg="white").pack(side=tk.TOP, anchor="w", pady=(2, 0))
                    elif k == "mousetracker":
                        tk.Label(right_frame, text="Measures clicks, scrolls & filtered movement", font=("Helvetica", 8), fg="gray", bg="white").pack(side=tk.TOP, anchor="w", pady=(2, 0))
                    elif k == "eyetracker":
                        tk.Label(right_frame, text="Local webcam gaze & blink estimation (Offline)", font=("Helvetica", 8), fg="gray", bg="white").pack(side=tk.TOP, anchor="w", pady=(2, 0))
                    elif k == "eyetracker_energysparmodus":
                        tk.Label(right_frame, text="Reduces to 2 FPS, skips blink tracking", font=("Helvetica", 8), fg="gray", bg="white").pack(side=tk.TOP, anchor="w", pady=(2, 0))
                else:
                    ent = tk.Entry(right_frame)
                    ent.insert(0, str(v))
                    ent.pack(side=tk.TOP, anchor="w")
                    self.setting_widgets[k] = ent
                    
            tk.Button(parent, text="💾 Save", command=self.speichere_vars, bg="lightgreen", font=("Helvetica", 9)).grid(row=len(self.einstellungen), columnspan=2, pady=10)

        create_accordion_section("General Settings", build_general)
        
        def build_activities(parent):
            self.baue_listen_manager(parent, cm.DATEI_AKT_LISTE, is_activities=True)
        create_accordion_section("Activities Manager", build_activities)
        
        def build_templates(parent):
            self.baue_listen_manager(parent, cm.DATEI_VORLAGEN)
        create_accordion_section("Templates Manager", build_templates)
        
        def build_subjects(parent):
            self.baue_listen_manager(parent, cm.DATEI_FAECHER)
        create_accordion_section("Subjects Manager", build_subjects)
        
        def build_events(parent):
            self.baue_listen_manager(parent, cm.DATEI_EVENTS)
        create_accordion_section("Events Manager", build_events)

    def speichere_vars(self):
        neue_einstellungen = {}
        for k, widget in self.setting_widgets.items():
            val = widget.get()
            try:
                old_val = self.einstellungen[k]
                if isinstance(old_val, bool):
                    neue_einstellungen[k] = (val.lower() == 'true')
                else:
                    neue_einstellungen[k] = type(old_val)(val)
            except:
                messagebox.showerror("Error", f"Error at {k}. Please enter a valid value.")
                return
        self.einstellungen = neue_einstellungen
        cm.speichere_einstellungen(self.einstellungen)
        messagebox.showinfo("Success", "Settings saved successfully!")

    def baue_listen_manager(self, tab, dateiname, is_activities=False):
        lb = tk.Listbox(tab, height=6, selectmode=tk.EXTENDED); lb.pack(fill=tk.BOTH, expand=True, pady=5)
        for w in utils.lese_textdatei(dateiname): lb.insert(tk.END, w)
        ent = tk.Entry(tab); ent.pack(fill=tk.X, pady=2)
        
        def add(): 
            val = ent.get().strip()
            if val: 
                lb.insert(tk.END, val)
                utils.schreibe_textdatei(dateiname, lb.get(0, tk.END))
                ent.delete(0, tk.END)
                
        def delete_items():
            selection = lb.curselection()
            for i in reversed(selection):
                item_text = lb.get(i)
                if is_activities and item_text in GESCHUETZTE_AKTIVITAETEN:
                    messagebox.showwarning("Warning", f"'{item_text}' is a core category and cannot be deleted.")
                    continue
                lb.delete(i)
            utils.schreibe_textdatei(dateiname, lb.get(0, tk.END))
            
        btn_frame = tk.Frame(tab, bg="white")
        btn_frame.pack(fill=tk.X, pady=5)
        tk.Button(btn_frame, text="Add", command=add, width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Delete", fg="red", command=delete_items, width=10).pack(side=tk.LEFT, padx=2)

    def _bind_mousewheel(self, widget, canvas):
        def _on_mousewheel(event):
            if hasattr(event, 'delta') and event.delta:
                amount = int(-1 * (event.delta / 120)) if abs(event.delta) >= 120 else (-1 if event.delta > 0 else 1)
                canvas.yview_scroll(amount, "units")
            elif hasattr(event, 'num'):
                if event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")
        
        widget.bind("<MouseWheel>", _on_mousewheel, add="+")
        widget.bind("<Button-4>", _on_mousewheel, add="+")
        widget.bind("<Button-5>", _on_mousewheel, add="+")
        
        for child in widget.winfo_children():
            self._bind_mousewheel(child, canvas)

    def erstelle_analysis_ui(self):
        top_header = tk.Frame(self.analysis_frame)
        top_header.pack(fill=tk.X, pady=(0, 2))
        
        tk.Button(top_header, text="⬅ Back", command=lambda: self.zeige_frame(self.home_frame), width=8, font=("Helvetica", 9), bg="lightgray").pack(side=tk.LEFT)
        tk.Label(top_header, text="Session Analytics & History", font=("Helvetica", 14, "bold")).pack(side=tk.LEFT, padx=10)
        
        filter_frame = tk.LabelFrame(self.analysis_frame, text=" Date Range Filter ", font=("Helvetica", 9, "bold"), padx=5, pady=5)
        filter_frame.pack(fill=tk.X, pady=5)
        
        row1 = tk.Frame(filter_frame)
        row1.pack(fill=tk.X, pady=2)
        
        tk.Label(row1, text="From (YYYY-MM-DD):", font=("Helvetica", 9)).pack(side=tk.LEFT, padx=2)
        self.ent_start_date = tk.Entry(row1, width=11, font=("Helvetica", 9))
        self.ent_start_date.pack(side=tk.LEFT, padx=2)
        
        tk.Label(row1, text="To:", font=("Helvetica", 9)).pack(side=tk.LEFT, padx=2)
        self.ent_end_date = tk.Entry(row1, width=11, font=("Helvetica", 9))
        self.ent_end_date.pack(side=tk.LEFT, padx=2)
        
        tk.Button(row1, text="Filter", command=self.aktualisiere_analysen_anzeige, width=7, font=("Helvetica", 9), bg="lightblue").pack(side=tk.LEFT, padx=5)
        tk.Button(row1, text="Reset", command=self.reset_date_filter, width=7, font=("Helvetica", 9)).pack(side=tk.LEFT, padx=2)
        
        row2 = tk.Frame(filter_frame)
        row2.pack(fill=tk.X, pady=(4, 2))
        
        tk.Label(row2, text="Presets:", font=("Helvetica", 9, "italic")).pack(side=tk.LEFT, padx=2)
        tk.Button(row2, text="Today", command=self.set_preset_today, font=("Helvetica", 8), width=8).pack(side=tk.LEFT, padx=2)
        tk.Button(row2, text="Last Week", command=self.set_preset_last_week, font=("Helvetica", 8), width=9).pack(side=tk.LEFT, padx=2)
        tk.Button(row2, text="Last Month", command=self.set_preset_last_month, font=("Helvetica", 8), width=9).pack(side=tk.LEFT, padx=2)

        analysis_nb = ttk.Notebook(self.analysis_frame)
        analysis_nb.pack(expand=True, fill=tk.BOTH, pady=5)
        
        tab_history = tk.Frame(analysis_nb)
        tab_charts_outer = tk.Frame(analysis_nb)
        
        analysis_nb.add(tab_history, text="Summary & History")
        analysis_nb.add(tab_charts_outer, text="Performance Charts")
        
        stats_frame = tk.LabelFrame(tab_history, text=" Productivity Overview ", font=("Helvetica", 10, "bold"), padx=10, pady=10)
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.lbl_total_time = tk.Label(stats_frame, text="Total Productive Time: 0.0 mins (0.0 hrs) | Avg Score: 0.0", font=("Helvetica", 9))
        self.lbl_total_time.pack(anchor="w", pady=1)
        
        self.lbl_break_lunch = tk.Label(stats_frame, text="Total Break: 0.0 mins | Avg Break: 0.0 mins | Avg Lunch: 0.0 mins", font=("Helvetica", 9))
        self.lbl_break_lunch.pack(anchor="w", pady=1)
        
        subject_row = tk.Frame(stats_frame)
        subject_row.pack(fill=tk.X, pady=5)
        tk.Label(subject_row, text="Subject:", font=("Helvetica", 9)).pack(side=tk.LEFT, padx=(0, 5))
        
        self.cbox_subject_stats = ttk.Combobox(subject_row, state="readonly", width=18, font=("Helvetica", 9))
        self.cbox_subject_stats.pack(side=tk.LEFT, padx=(0, 10))
        self.cbox_subject_stats.bind("<<ComboboxSelected>>", self.on_subject_selected)
        
        self.lbl_subject_pct = tk.Label(subject_row, text="Share: 0.0%", font=("Helvetica", 9))
        self.lbl_subject_pct.pack(side=tk.LEFT, padx=5)
        
        self.lbl_subject_time = tk.Label(stats_frame, text="Subject Time: 0.0 mins (0.00 hrs) | Subject Avg Score: 0.0", font=("Helvetica", 9))
        self.lbl_subject_time.pack(anchor="w", pady=(2, 0))
        
        text_container = tk.Frame(tab_history)
        text_container.pack(expand=True, fill=tk.BOTH, pady=5)
        scrollbar = tk.Scrollbar(text_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_analysis = tk.Text(text_container, wrap=tk.WORD, yscrollcommand=scrollbar.set, font=("Courier", 9), bg="#f9f9f9")
        self.txt_analysis.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scrollbar.config(command=self.txt_analysis.yview)
        
        chart_controls_frame = tk.Frame(tab_charts_outer, bg="#eef2f5", padx=8, pady=6)
        chart_controls_frame.pack(side=tk.TOP, fill=tk.X)
        
        tk.Label(chart_controls_frame, text="Weekday Filter (Plots 1 & 2):", font=("Helvetica", 9, "bold"), bg="#eef2f5").pack(side=tk.LEFT, padx=5)
        self.cbox_plot1_filter = ttk.Combobox(
            chart_controls_frame, 
            values=["All Days", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            state="readonly",
            width=15,
            font=("Helvetica", 9)
        )
        self.cbox_plot1_filter.pack(side=tk.LEFT, padx=5)
        self.cbox_plot1_filter.current(0)
        self.cbox_plot1_filter.bind("<<ComboboxSelected>>", lambda e: self.aktualisiere_analysen_anzeige())

        canvas_charts_wrapper = tk.Frame(tab_charts_outer)
        canvas_charts_wrapper.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.canvas_charts = tk.Canvas(canvas_charts_wrapper, highlightthickness=0)
        scrollbar_charts = tk.Scrollbar(canvas_charts_wrapper, orient="vertical", command=self.canvas_charts.yview)
        
        self.chart_container = tk.Frame(self.canvas_charts)
        self.chart_container.bind(
            "<Configure>",
            lambda e: self.canvas_charts.configure(scrollregion=self.canvas_charts.bbox("all"))
        )
        
        self.canvas_charts.create_window((0, 0), window=self.chart_container, anchor="nw")
        self.canvas_charts.configure(yscrollcommand=scrollbar_charts.set)
        
        self.canvas_charts.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_charts.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._bind_mousewheel(tab_charts_outer, self.canvas_charts)
        
        btn_frame = tk.Frame(self.analysis_frame)
        btn_frame.pack(pady=2)
        tk.Button(btn_frame, text="🔄 Refresh", command=self.aktualisiere_analysen_anzeige, width=15, bg="lightyellow").pack()

    def set_preset_today(self):
        today_str = datetime.now().strftime("%Y-%m-%d")
        self.ent_start_date.delete(0, tk.END)
        self.ent_start_date.insert(0, today_str)
        self.ent_end_date.delete(0, tk.END)
        self.ent_end_date.insert(0, today_str)
        self.aktualisiere_analysen_anzeige()

    def set_preset_last_week(self):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        self.ent_start_date.delete(0, tk.END)
        self.ent_start_date.insert(0, start_date.strftime("%Y-%m-%d"))
        self.ent_end_date.delete(0, tk.END)
        self.ent_end_date.insert(0, end_date.strftime("%Y-%m-%d"))
        self.aktualisiere_analysen_anzeige()

    def set_preset_last_month(self):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        self.ent_start_date.delete(0, tk.END)
        self.ent_start_date.insert(0, start_date.strftime("%Y-%m-%d"))
        self.ent_end_date.delete(0, tk.END)
        self.ent_end_date.insert(0, end_date.strftime("%Y-%m-%d"))
        self.aktualisiere_analysen_anzeige()

    def reset_date_filter(self):
        self.ent_start_date.delete(0, tk.END)
        self.ent_end_date.delete(0, tk.END)
        self.aktualisiere_analysen_anzeige()

    def on_subject_selected(self, event=None):
        selected_subj = self.cbox_subject_stats.get()
        if selected_subj and selected_subj in self.current_subject_details:
            details = self.current_subject_details[selected_subj]
            mins = details["total_mins"]
            hrs = mins / 60
            pct = details["pct"]
            avg_sc = details["avg_score"]
            
            self.lbl_subject_pct.config(text=f"Share: {pct:.1f}%")
            self.lbl_subject_time.config(text=f"Subject Time: {mins:.1f} mins ({hrs:.2f} hrs) | Subject Avg Score: {avg_sc:.1f}")
        else:
            self.lbl_subject_pct.config(text="Share: 0.0%")
            self.lbl_subject_time.config(text="Subject Time: 0.0 mins (0.00 hrs) | Subject Avg Score: 0.0")

    def aktualisiere_analysen_anzeige(self):
        start_d = self.ent_start_date.get().strip()
        end_d = self.ent_end_date.get().strip()
        plot1_f = self.cbox_plot1_filter.get().strip() or "All Days"
        
        total_prod, total_break, avg_break, avg_lunch, subject_details, avg_score, report_text = analytics.analysiere_daten(
            cm.DATEI_KOMMENTARE, cm.DATEI_AKTIVITAETEN, SCORE_MAX, start_d, end_d
        )
        
        self.current_subject_details = subject_details
        
        hours = total_prod / 60
        self.lbl_total_time.config(text=f"Total Productive Time: {total_prod:.1f} mins ({hours:.2f} hrs) | Avg Score: {avg_score:.1f}")
        self.lbl_break_lunch.config(text=f"Total Break: {total_break:.1f} mins | Avg Break: {avg_break:.1f} mins | Avg Lunch: {avg_lunch:.1f} mins")
        
        subject_names = list(subject_details.keys())
        self.cbox_subject_stats['values'] = subject_names
        
        if subject_names:
            current_selection = self.cbox_subject_stats.get()
            if current_selection not in subject_names:
                self.cbox_subject_stats.current(0)
        else:
            self.cbox_subject_stats.set('')
            
        self.on_subject_selected()
            
        self.txt_analysis.config(state=tk.NORMAL)
        self.txt_analysis.delete("1.0", tk.END)
        self.txt_analysis.insert(tk.END, report_text)
        self.txt_analysis.config(state=tk.DISABLED)

        for widget in self.chart_container.winfo_children():
            widget.destroy()
            
        fig = analytics.generate_charts(cm.DATEI_KOMMENTARE, cm.DATEI_AKTIVITAETEN, start_d, end_d, plot1_f)
        canvas_fig = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas_fig.draw()
        canvas_fig_widget = canvas_fig.get_tk_widget()
        canvas_fig_widget.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        self._bind_mousewheel(self.chart_container, self.canvas_charts)

    def erstelle_kommentar_ui(self):
        for w in self.kommentar_frame.winfo_children(): w.destroy()
        
        top_header = tk.Frame(self.kommentar_frame)
        top_header.pack(fill=tk.X, pady=(0, 20))
        
        tk.Button(top_header, text="⬅ Back", command=lambda: self.zeige_frame(self.home_frame), width=8, font=("Helvetica", 9), bg="lightgray").pack(side=tk.LEFT)
        tk.Label(top_header, text="New Session", font=("Helvetica", 14, "bold")).pack(side=tk.LEFT, padx=10)
        
        tk.Label(self.kommentar_frame, text="Choose or enter session comment:", font=("Helvetica", 10)).pack(pady=5)
        self.entry_kommentar = ttk.Combobox(self.kommentar_frame, font=("Helvetica", 12), width=30)
        self.entry_kommentar.pack(pady=10)
        tk.Button(self.kommentar_frame, text="🚀 Start", font=("Helvetica", 12), bg="lightgreen", width=15, height=2, command=self.starte_session).pack(pady=20)

    def starte_session(self):
        kommentar = self.entry_kommentar.get().strip() or "No comment"
        if kommentar and kommentar != "No comment":
            vorhandene_vorlagen = utils.lese_textdatei(cm.DATEI_VORLAGEN)
            if kommentar not in vorhandene_vorlagen:
                vorhandene_vorlagen.append(kommentar)
                utils.schreibe_textdatei(cm.DATEI_VORLAGEN, vorhandene_vorlagen)

        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(cm.DATEI_KOMMENTARE, "a", newline="", encoding="utf-8") as f: csv.writer(f).writerow([self.session_id, datetime.now().strftime("%Y-%m-%d"), kommentar])
        self.erstelle_haupt_ui()
        self.zeige_frame(self.haupt_frame)

    def erstelle_haupt_ui(self):
        for w in self.haupt_frame.winfo_children(): w.destroy()
        
        top_header = tk.Frame(self.haupt_frame)
        top_header.pack(fill=tk.X, pady=(0, 10))
        
        tk.Button(top_header, text="⬅ Back", command=self.session_beenden, width=8, font=("Helvetica", 9), bg="lightgray").pack(side=tk.LEFT)
        tk.Label(top_header, text="Active Session", font=("Helvetica", 14, "bold")).pack(side=tk.LEFT, padx=10)
        
        self.lbl_status = tk.Label(self.haupt_frame, text="...", font=("Helvetica", 12)); self.lbl_status.pack(pady=5)
        self.lbl_timer = tk.Label(self.haupt_frame, text="00:00", font=("Helvetica", 48, "bold")); self.lbl_timer.pack(pady=5)
        self.lbl_msg = tk.Label(self.haupt_frame, text="", fg="red"); self.lbl_msg.pack(pady=2)
        
        bf = tk.Frame(self.haupt_frame); bf.pack(pady=10)
        self.buttons = {}
        for i, akt in enumerate(utils.lese_textdatei(cm.DATEI_AKT_LISTE)):
            btn = tk.Button(bf, text=akt, width=12, height=2, command=lambda a=akt: self.wechsle_akt(a))
            btn.grid(row=i//2, column=i%2, padx=5, pady=5); self.buttons[akt] = btn

        event_frame = tk.Frame(self.haupt_frame, bd=1, relief=tk.SOLID, padx=10, pady=10)
        event_frame.pack(pady=10, fill=tk.X)
        
        tk.Label(event_frame, text="Log Event:", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        sub_event_frame = tk.Frame(event_frame)
        sub_event_frame.pack(fill=tk.X)
        
        self.cbox_events = ttk.Combobox(sub_event_frame, values=utils.lese_textdatei(cm.DATEI_EVENTS), width=18, font=("Helvetica", 10))
        self.cbox_events.pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
        if self.cbox_events['values']:
            self.cbox_events.current(0)
            
        tk.Button(sub_event_frame, text="Log Event 📌", command=self.logge_event, font=("Helvetica", 10), bg="lightyellow").pack(side=tk.LEFT)

    def logge_event(self):
        event_name = self.cbox_events.get().strip()
        if not event_name:
            messagebox.showwarning("Notice", "Please select an event.")
            return
            
        vorhandene_events = utils.lese_textdatei(cm.DATEI_EVENTS)
        if event_name not in vorhandene_events:
            vorhandene_events.append(event_name)
            utils.schreibe_textdatei(cm.DATEI_EVENTS, vorhandene_events)
            self.cbox_events['values'] = vorhandene_events

        zeitstempel = datetime.now().strftime("%H:%M:%S")
        datum = datetime.now().strftime("%Y-%m-%d")
        aktuelle_akt = self.aktuelle_aktivitaet if self.aktuelle_aktivitaet else "No activity"
        
        with open(cm.DATEI_EVENT_LOGS, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([self.session_id, aktuelle_akt, event_name, f"{datum} {zeitstempel}"])
            
        self.lbl_msg.config(text=f"✅ '{event_name}' logged ({zeitstempel})", fg="green")
        self.root.after(3000, lambda: self.lbl_msg.config(text="") if self.lbl_msg.cget("text").startswith("✅") else None)

    def starte_keyboard_listener(self):
        if not self.einstellungen.get("tastatur_tracker", False) or not PYNPUT_INSTALLIERT:
            return
        
        self.keystroke_count = 0
        self.typing_pauses = 0
        self.kb_intervals = []
        self.last_key_time = time.time()
        
        def on_press(key):
            now = time.time()
            diff = now - self.last_key_time
            self.keystroke_count += 1
            if diff > 2.5:
                self.typing_pauses += 1
            else:
                self.kb_intervals.append(diff)
            self.last_key_time = now

        try:
            self.kb_listener = keyboard.Listener(on_press=on_press)
            self.kb_listener.start()
        except Exception:
            pass

    def stoppe_keyboard_listener(self):
        if self.kb_listener:
            try:
                self.kb_listener.stop()
            except Exception:
                pass
            self.kb_listener = None

    def starte_mouse_listener(self):
        if not self.einstellungen.get("mousetracker", False) or not PYNPUT_INSTALLIERT:
            return
        
        self.click_count = 0
        self.scroll_count = 0
        self.mouse_move_count = 0
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        
        def on_click(x, y, button, pressed):
            if pressed:
                self.click_count += 1
                
        def on_scroll(x, y, dx, dy):
            self.scroll_count += 1
            
        def on_move(x, y):
            distanz = abs(x - self.last_mouse_x) + abs(y - self.last_mouse_y)
            if distanz > 50:
                self.mouse_move_count += 1
                self.last_mouse_x = x
                self.last_mouse_y = y

        try:
            self.mouse_listener = mouse.Listener(on_click=on_click, on_scroll=on_scroll, on_move=on_move)
            self.mouse_listener.start()
        except Exception:
            pass

    def stoppe_mouse_listener(self):
        if self.mouse_listener:
            try:
                self.mouse_listener.stop()
            except Exception:
                pass
            self.mouse_listener = None

    def starte_eye_tracker(self):
        if not self.einstellungen.get("eyetracker", False):
            return
        energy_mode = self.einstellungen.get("eyetracker_energysparmodus", False)
        self.eye_manager = eye_tracker.EyeTrackerManager(
            self.session_id, 
            self.aktuelle_aktivitaet or "No activity", 
            energy_saver=energy_mode, 
            output_dir=cm.BASE_DIR
        )
        self.eye_manager.start()

    def stoppe_eye_tracker(self):
        if self.eye_manager:
            self.eye_manager.stop()
            self.eye_manager = None

    def wechsle_akt(self, neue_akt):
        if neue_akt == self.aktuelle_aktivitaet: return
        if self.aktuelle_aktivitaet: self.speichere_aktuelle_akt()
        
        self.stoppe_keyboard_listener()
        self.stoppe_mouse_listener()
        self.stoppe_eye_tracker()
        
        self.lbl_msg.config(text="") 
        self.erinnerung_gesendet = False
        self.aktuelle_aktivitaet = neue_akt
        self.aktivitaet_startzeit = time.time()
        self.fenster_zeiten = {}
        self.lbl_status.config(text=f"Current: {neue_akt}")
        
        if not self.timer_laeuft: 
            self.timer_laeuft = True
            self.aktualisiere_timer()
            
        self.starte_keyboard_listener()
        self.starte_mouse_listener()
        self.starte_eye_tracker()

    def abfrage_lern_details(self):
        top = tk.Toplevel(self.root)
        top.title("Session Summary")
        top.geometry("320x250")
        
        tk.Label(top, text=f"Score (optional, from {SCORE_MIN} to {SCORE_MAX}):").pack(pady=5)
        ent_score = tk.Entry(top)
        ent_score.pack()
        
        tk.Label(top, text="Subject (optional):").pack(pady=5)
        
        # Frame für Combobox und Clear-Button nebeneinander
        fach_frame = tk.Frame(top)
        fach_frame.pack(pady=2)
        
        faecher_liste = utils.lese_textdatei(cm.DATEI_FAECHER)
        cbox_fach = ttk.Combobox(fach_frame, values=faecher_liste, width=20)
        cbox_fach.pack(side=tk.LEFT, padx=(0, 5))
        
        # Zuletzt gewähltes Fach automatisch vorauswählen, falls vorhanden
        if self.letztes_fach:
            cbox_fach.set(self.letztes_fach)
            
        def clear_fach():
            cbox_fach.set("")
            
        tk.Button(fach_frame, text="❌ Clear", command=clear_fach, font=("Helvetica", 8), width=6).pack(side=tk.LEFT)
        
        result = {"score": "", "fach": ""}
        def save():
            sc = ent_score.get()
            if sc:
                try:
                    s_val = int(sc)
                    if not (SCORE_MIN <= s_val <= SCORE_MAX): raise ValueError
                    result["score"] = s_val
                except: 
                    messagebox.showerror("Error", f"Score must be an integer from {SCORE_MIN} to {SCORE_MAX}.")
                    return
            
            fach_eingabe = cbox_fach.get().strip()
            result["fach"] = fach_eingabe
            
            # Fach für das nächste Mal merken
            self.letztes_fach = fach_eingabe
            
            if fach_eingabe:
                vorhandene_faecher = utils.lese_textdatei(cm.DATEI_FAECHER)
                if fach_eingabe not in vorhandene_faecher:
                    vorhandene_faecher.append(fach_eingabe)
                    utils.schreibe_textdatei(cm.DATEI_FAECHER, vorhandene_faecher)
                    
            top.destroy()
            
        tk.Button(top, text="Save", command=save, width=15).pack(pady=20)
        self.root.wait_window(top)
        return result

    def speichere_aktuelle_akt(self):
        self.stoppe_keyboard_listener()
        self.stoppe_mouse_listener()
        self.stoppe_eye_tracker()
        
        dur = round((time.time() - self.aktivitaet_startzeit) / 60, 2)
        score, fach = "", ""
        if self.timer_laeuft and self.aktuelle_aktivitaet and "productivity" in self.aktuelle_aktivitaet.lower():
            details = self.abfrage_lern_details(); score, fach = details["score"], details["fach"]
        
        with open(cm.DATEI_AKTIVITAETEN, "a", newline="", encoding="utf-8") as f: 
            csv.writer(f).writerow([self.session_id, self.aktuelle_aktivitaet, datetime.now().strftime("%H:%M:%S"), dur, score, fach])
        
        if self.einstellungen.get("aktivitaetentracker", True):
            with open(cm.DATEI_FENSTER, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for (p, t), s in self.fenster_zeiten.items(): writer.writerow([self.session_id, self.aktuelle_aktivitaet, p, t, s])
                
        if self.einstellungen.get("tastatur_tracker", False) and self.keystroke_count > 0:
            avg_interval = sum(self.kb_intervals) / len(self.kb_intervals) if self.kb_intervals else 0
            tastatur_datei = os.path.join(cm.BASE_DIR, "tastatur_stats.csv")
            with open(tastatur_datei, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([self.session_id, self.aktuelle_aktivitaet, self.keystroke_count, self.typing_pauses, round(avg_interval, 3), datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

        if self.einstellungen.get("mousetracker", False) and (self.click_count > 0 or self.scroll_count > 0 or self.mouse_move_count > 0):
            maus_datei = os.path.join(cm.BASE_DIR, "maus_stats.csv")
            with open(maus_datei, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([self.session_id, self.aktuelle_aktivitaet, self.click_count, self.scroll_count, self.mouse_move_count, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

    def aktualisiere_timer(self):
        if not self.timer_laeuft: return
        try:
            gesamt_sek = int(time.time() - self.aktivitaet_startzeit)
            mins = gesamt_sek // 60
            secs = gesamt_sek % 60
            self.lbl_timer.config(text=f"{mins:02d}:{secs:02d}")
            
            if self.aktuelle_aktivitaet and "productivity" in self.aktuelle_aktivitaet.lower() and mins >= self.einstellungen["lern_erinnerung_minuten"] and not self.erinnerung_gesendet:
                if self.einstellungen.get("pausenbenachrichtigung", True):
                    self.lbl_msg.config(text="⏰ Time for a break!")
                    if PLYER_INSTALLIERT:
                        try:
                            notification.notify(title="Flow Tracker", message="Time for a break!", timeout=10)
                        except Exception:
                            pass
                self.erinnerung_gesendet = True
                
            if self.einstellungen.get("aktivitaetentracker", True):
                p, t = utils.hole_aktives_fenster_info()
                self.fenster_zeiten[(p, t)] = self.fenster_zeiten.get((p, t), 0) + 1
        except Exception:
            pass
            
        self.root.after(1000, self.aktualisiere_timer)

    def session_beenden(self):
        if self.aktuelle_aktivitaet: self.speichere_aktuelle_akt()
        self.stoppe_keyboard_listener()
        self.stoppe_mouse_listener()
        self.stoppe_eye_tracker()
        self.timer_laeuft = False
        self.lbl_msg.config(text="")
        self.zeige_frame(self.home_frame)

    def beim_schliessen(self):
        if self.aktuelle_aktivitaet: self.speichere_aktuelle_akt()
        self.stoppe_keyboard_listener()
        self.stoppe_mouse_listener()
        self.stoppe_eye_tracker()
        self.root.destroy()