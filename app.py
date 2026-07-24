import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import time, csv, os
from datetime import datetime, timedelta
import config_manager as cm
import utils
import analytics

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

try:
    from plyer import notification
    PLYER_INSTALLIERT = True
except: PLYER_INSTALLIERT = False

SCORE_MIN = 1
SCORE_MAX = 5
GESCHUETZTE_AKTIVITAETEN = ["Productivity", "Break", "Lunch"]

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
        
        self.session_id = ""
        self.aktuelle_aktivitaet = None
        self.aktivitaet_startzeit = 0
        self.timer_laeuft = False
        self.erinnerung_gesendet = False
        self.fenster_zeiten = {}
        
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

    def erstelle_home_ui(self):
        tk.Label(self.home_frame, text="🧠 Flow Tracker", font=("Helvetica", 28, "bold")).pack(pady=40)
        
        tk.Button(self.home_frame, text="▶ Start Session", font=("Helvetica", 14), bg="lightgreen", width=20, height=2,
                  command=lambda: self.zeige_frame(self.kommentar_frame)).pack(pady=10)
        
        tk.Button(self.home_frame, text="📊 Data Analysis", font=("Helvetica", 14), bg="lightblue", width=20, height=2,
                  command=lambda: self.zeige_frame(self.analysis_frame)).pack(pady=10)
                  
        tk.Button(self.home_frame, text="⚙️ Settings", font=("Helvetica", 14), bg="lightgray", width=20, height=2,
                  command=lambda: self.zeige_frame(self.settings_frame)).pack(pady=10)

    def erstelle_settings_ui(self):
        tk.Label(self.settings_frame, text="Settings", font=("Helvetica", 20, "bold")).pack(pady=10)
        nb = ttk.Notebook(self.settings_frame)
        nb.pack(expand=True, fill=tk.BOTH, pady=10)
        
        t1, t2, t3, t4, t5 = tk.Frame(nb), tk.Frame(nb), tk.Frame(nb), tk.Frame(nb), tk.Frame(nb)
        nb.add(t1, text="General")
        nb.add(t2, text="Activities")
        nb.add(t3, text="Templates")
        nb.add(t4, text="Subjects")
        nb.add(t5, text="Events")
        
        self.setting_widgets = {}
        
        # Mapping für englische Beschriftungen der Einstellungen
        setting_labels = {
            "lern_erinnerung_minuten": "Break Reminder Minutes",
            "pausenbenachrichtigung": "Break Notification",
            "aktivitaetentracker": "Activity Tracker"
        }
        
        for i, (k, v) in enumerate(self.einstellungen.items()):
            display_name = setting_labels.get(k, k.replace("_", " ").title())
            tk.Label(t1, text=display_name+":").grid(row=i, column=0, sticky="nw", padx=10, pady=5)
            
            right_frame = tk.Frame(t1)
            right_frame.grid(row=i, column=1, sticky="w", padx=10, pady=5)
            
            if isinstance(v, bool):
                cb = ttk.Combobox(right_frame, values=["True", "False"], state="readonly", width=12)
                cb.set(str(v))
                cb.pack(side=tk.TOP, anchor="w")
                self.setting_widgets[k] = cb
                
                # Klein dazuschreiben, was der Aktivitätentracker trackt
                if k == "aktivitaetentracker":
                    tk.Label(right_frame, text="Tracks active windows & application titles", font=("Helvetica", 8), fg="gray").pack(side=tk.TOP, anchor="w", pady=(2, 0))
            else:
                ent = tk.Entry(right_frame)
                ent.insert(0, str(v))
                ent.pack(side=tk.TOP, anchor="w")
                self.setting_widgets[k] = ent
                
        tk.Button(t1, text="💾 Save", command=self.speichere_vars).grid(row=len(self.einstellungen), columnspan=2, pady=20)
        
        self.baue_listen_manager(t2, cm.DATEI_AKT_LISTE, is_activities=True)
        self.baue_listen_manager(t3, cm.DATEI_VORLAGEN)
        self.baue_listen_manager(t4, cm.DATEI_FAECHER)
        self.baue_listen_manager(t5, cm.DATEI_EVENTS)
        
        tk.Button(self.settings_frame, text="⬅ Back", command=lambda: self.zeige_frame(self.home_frame)).pack()

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
        lb = tk.Listbox(tab, height=8, selectmode=tk.EXTENDED); lb.pack(fill=tk.BOTH, expand=True)
        for w in utils.lese_textdatei(dateiname): lb.insert(tk.END, w)
        ent = tk.Entry(tab); ent.pack(fill=tk.X)
        
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
            
        tk.Button(tab, text="Add", command=add).pack()
        tk.Button(tab, text="Delete", fg="red", command=delete_items).pack()

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
        
        # --- TAB 1: Summary & History ---
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
        
        # --- TAB 2: Performance Charts (Scrollable) ---
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
        tk.Label(self.kommentar_frame, text="New Session", font=("Helvetica", 14, "bold")).pack(pady=20)
        tk.Label(self.kommentar_frame, text="Choose or enter session comment:").pack()
        self.entry_kommentar = ttk.Combobox(self.kommentar_frame, font=("Helvetica", 12), width=30)
        self.entry_kommentar.pack(pady=10)
        tk.Button(self.kommentar_frame, text="🚀 Start", command=self.starte_session).pack(pady=20)
        tk.Button(self.kommentar_frame, text="Cancel", command=lambda: self.zeige_frame(self.home_frame)).pack()

    def starte_session(self):
        kommentar = self.entry_kommentar.get().strip() or "No comment"
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(cm.DATEI_KOMMENTARE, "a", newline="", encoding="utf-8") as f: csv.writer(f).writerow([self.session_id, datetime.now().strftime("%Y-%m-%d"), kommentar])
        self.erstelle_haupt_ui()
        self.zeige_frame(self.haupt_frame)

    def erstelle_haupt_ui(self):
        for w in self.haupt_frame.winfo_children(): w.destroy()
        
        self.lbl_status = tk.Label(self.haupt_frame, text="...", font=("Helvetica", 12)); self.lbl_status.pack()
        self.lbl_timer = tk.Label(self.haupt_frame, text="00:00", font=("Helvetica", 48, "bold")); self.lbl_timer.pack()
        self.lbl_msg = tk.Label(self.haupt_frame, text="", fg="red"); self.lbl_msg.pack()
        
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

        tk.Button(self.haupt_frame, text="⏹ End Session", fg="red", command=self.session_beenden).pack(pady=10)

    def logge_event(self):
        event_name = self.cbox_events.get().strip()
        if not event_name:
            messagebox.showwarning("Notice", "Please select an event.")
            return
            
        zeitstempel = datetime.now().strftime("%H:%M:%S")
        datum = datetime.now().strftime("%Y-%m-%d")
        aktuelle_akt = self.aktuelle_aktivitaet if self.aktuelle_aktivitaet else "No activity"
        
        with open(cm.DATEI_EVENT_LOGS, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([self.session_id, aktuelle_akt, event_name, f"{datum} {zeitstempel}"])
            
        self.lbl_msg.config(text=f"✅ '{event_name}' logged ({zeitstempel})", fg="green")
        self.root.after(3000, lambda: self.lbl_msg.config(text="") if self.lbl_msg.cget("text").startswith("✅") else None)

    def wechsle_akt(self, neue_akt):
        if neue_akt == self.aktuelle_aktivitaet: return
        if self.aktuelle_aktivitaet: self.speichere_aktuelle_akt()
        self.lbl_msg.config(text="") 
        self.erinnerung_gesendet = False
        self.aktuelle_aktivitaet = neue_akt
        self.aktivitaet_startzeit = time.time()
        self.fenster_zeiten = {}
        self.lbl_status.config(text=f"Current: {neue_akt}")
        if not self.timer_laeuft: self.timer_laeuft = True; self.aktualisiere_timer()

    def abfrage_lern_details(self):
        top = tk.Toplevel(self.root)
        top.title("Session Summary")
        top.geometry("300x250")
        
        tk.Label(top, text=f"Score (optional, from {SCORE_MIN} to {SCORE_MAX}):").pack(pady=5)
        ent_score = tk.Entry(top)
        ent_score.pack()
        
        tk.Label(top, text="Subject (optional):").pack(pady=5)
        cbox_fach = ttk.Combobox(top, values=utils.lese_textdatei(cm.DATEI_FAECHER))
        cbox_fach.pack()
        
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
            result["fach"] = cbox_fach.get()
            top.destroy()
            
        tk.Button(top, text="Save", command=save).pack(pady=20)
        self.root.wait_window(top)
        return result

    def speichere_aktuelle_akt(self):
        dur = round((time.time() - self.aktivitaet_startzeit) / 60, 2)
        score, fach = "", ""
        if self.timer_laeuft and self.aktuelle_aktivitaet and "productivity" in self.aktuelle_aktivitaet.lower():
            details = self.abfrage_lern_details(); score, fach = details["score"], details["fach"]
        with open(cm.DATEI_AKTIVITAETEN, "a", newline="", encoding="utf-8") as f: csv.writer(f).writerow([self.session_id, self.aktuelle_aktivitaet, datetime.now().strftime("%H:%M:%S"), dur, score, fach])
        
        if self.einstellungen.get("aktivitaetentracker", True):
            with open(cm.DATEI_FENSTER, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for (p, t), s in self.fenster_zeiten.items(): writer.writerow([self.session_id, self.aktuelle_aktivitaet, p, t, s])

    def aktualisiere_timer(self):
        if not self.timer_laeuft: return
        gesamt_sek = int(time.time() - self.aktivitaet_startzeit)
        mins = gesamt_sek // 60
        secs = gesamt_sek % 60
        self.lbl_timer.config(text=f"{mins:02d}:{secs:02d}")
        
        if self.aktuelle_aktivitaet and "productivity" in self.aktuelle_aktivitaet.lower() and mins >= self.einstellungen["lern_erinnerung_minuten"] and not self.erinnerung_gesendet:
            if self.einstellungen.get("pausenbenachrichtigung", True):
                self.lbl_msg.config(text="⏰ Time for a break!")
                if PLYER_INSTALLIERT: notification.notify(title="Flow Tracker", message="Time for a break!", timeout=10)
            self.erinnerung_gesendet = True
            
        if self.einstellungen.get("aktivitaetentracker", True):
            p, t = utils.hole_aktives_fenster_info()
            self.fenster_zeiten[(p, t)] = self.fenster_zeiten.get((p, t), 0) + 1
            
        self.root.after(1000, self.aktualisiere_timer)

    def session_beenden(self):
        if self.aktuelle_aktivitaet: self.speichere_aktuelle_akt()
        self.timer_laeuft = False
        self.lbl_msg.config(text="")
        self.zeige_frame(self.home_frame)

    def beim_schliessen(self):
        if self.aktuelle_aktivitaet: self.speichere_aktuelle_akt()
        self.root.destroy()