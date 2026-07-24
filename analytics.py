import os
import csv
from datetime import datetime, timedelta
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure

def _datum_im_zeitraum(datum_str, start_date, end_date):
    if not datum_str:
        return False
    try:
        if start_date and datum_str < start_date:
            return False
        if end_date and datum_str > end_date:
            return False
        return True
    except:
        return True

def analysiere_daten(datei_kommentare, datei_aktivitaeten, score_max=5, start_date="", end_date=""):
    kommentare = {}
    if os.path.exists(datei_kommentare):
        with open(datei_kommentare, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    s_id, date_str, comment = row[0], row[1], row[2]
                    if _datum_im_zeitraum(date_str, start_date, end_date):
                        kommentare[s_id] = {"date": date_str, "comment": comment}
                    
    sessions = {}
    if os.path.exists(datei_aktivitaeten):
        with open(datei_aktivitaeten, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 6:
                    s_id, act, start, dur, score, subj = row[0], row[1], row[2], row[3], row[4], row[5]
                    if s_id in kommentare:
                        if s_id not in sessions:
                            sessions[s_id] = {"activities": [], "total_dur": 0}
                        try: d_val = float(dur)
                        except: d_val = 0.0
                        sessions[s_id]["activities"].append({"activity": act, "duration": d_val, "score": score, "subject": subj})
                        sessions[s_id]["total_dur"] += d_val

    total_prod_time = 0
    total_break_time = 0
    break_count = 0
    total_lunch_time = 0
    lunch_count = 0
    
    subject_durations = {}
    subject_scores = {}
    all_scores = []
    
    for s_id, data in sessions.items():
        for act_obj in data["activities"]:
            act_lower = act_obj["activity"].lower()
            dur_val = act_obj["duration"]
            
            if "productivity" in act_lower:
                total_prod_time += dur_val
                subj_name = act_obj["subject"].strip() if act_obj["subject"].strip() else "Unspecified Subject"
                
                subject_durations[subj_name] = subject_durations.get(subj_name, 0.0) + dur_val
                
                if act_obj["score"]:
                    try: 
                        sc = float(act_obj["score"])
                        all_scores.append(sc)
                        if subj_name not in subject_scores:
                            subject_scores[subj_name] = []
                        subject_scores[subj_name].append(sc)
                    except: pass
            elif "break" in act_lower:
                total_break_time += dur_val
                break_count += 1
            elif "lunch" in act_lower:
                total_lunch_time += dur_val
                lunch_count += 1

    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
    avg_break_time = total_break_time / break_count if break_count > 0 else 0.0
    avg_lunch_time = total_lunch_time / lunch_count if lunch_count > 0 else 0.0

    subject_details = {}
    for subj, dur in subject_durations.items():
        pct = (dur / total_prod_time * 100) if total_prod_time > 0 else 0.0
        subj_scs = subject_scores.get(subj, [])
        subj_avg_score = sum(subj_scs) / len(subj_scs) if subj_scs else 0.0
        subject_details[subj] = {
            "total_mins": dur,
            "pct": pct,
            "avg_score": subj_avg_score
        }
    
    lines = []
    lines.append("=== DETAILED SESSION HISTORY ===")
    
    if not kommentare:
        lines.append("\nNo sessions recorded for this timeframe.")
        return total_prod_time, total_break_time, avg_break_time, avg_lunch_time, subject_details, avg_score, "\n".join(lines)
        
    for s_id, info in sorted(kommentare.items(), reverse=True):
        date = info["date"]
        comment = info["comment"]
        lines.append(f"\n[ID: {s_id}] Date: {date}")
        lines.append(f"Comment: {comment}")
        if s_id in sessions:
            lines.append("Activities performed:")
            for act in sessions[s_id]["activities"]:
                sc_str = f" | Score: {act['score']}" if act['score'] else ""
                subj_str = f" | Subject: {act['subject']}" if act['subject'] else ""
                lines.append(f"  • {act['activity']}: {act['duration']} min{sc_str}{subj_str}")
        else:
            lines.append("  • No activity data logged for this session.")
        lines.append("-" * 45)
        
    return total_prod_time, total_break_time, avg_break_time, avg_lunch_time, subject_details, avg_score, "\n".join(lines)


def get_plotting_data(datei_kommentare, datei_aktivitaeten, start_date="", end_date="", plot1_filter="All Days"):
    session_dates = {}
    if os.path.exists(datei_kommentare):
        with open(datei_kommentare, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    s_id, date_str = row[0], row[1]
                    if _datum_im_zeitraum(date_str, start_date, end_date):
                        session_dates[s_id] = date_str

    sessions_acts = {}
    if os.path.exists(datei_aktivitaeten):
        with open(datei_aktivitaeten, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 6:
                    s_id, act, end_time_str, dur_str, score_str, subj = row[0], row[1], row[2], row[3], row[4], row[5]
                    if s_id in session_dates:
                        if s_id not in sessions_acts:
                            sessions_acts[s_id] = []
                        
                        try: dur = float(dur_str)
                        except: dur = 0.0
                        
                        try: score = float(score_str) if score_str else None
                        except: score = None

                        sessions_acts[s_id].append({
                            "activity": act,
                            "end_time_str": end_time_str,
                            "duration": dur,
                            "score": score,
                            "subject": subj
                        })

    plot1_raw = []
    plot2_raw = []
    plot3_raw = []
    
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for s_id, acts in sessions_acts.items():
        date_str = session_dates.get(s_id, None)
        day_of_week = None
        if date_str:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                day_of_week = dt.strftime("%A")
            except:
                pass

        cumulative_time = 0.0
        for act in acts:
            hour_val = None
            end_str = act["end_time_str"]
            dur = act["duration"]
            
            if end_str:
                try:
                    t_obj = datetime.strptime(end_str, "%H:%M:%S")
                    middle_dt = t_obj - timedelta(minutes=dur / 2.0)
                    hour_val = middle_dt.hour
                except:
                    pass

            if "productivity" in act["activity"].lower() and act["score"] is not None:
                sc = act["score"]
                w = dur if dur > 0 else 1.0
                
                if hour_val is not None and 0 <= hour_val <= 23:
                    plot1_raw.append({"hour": hour_val, "score": sc, "weight": w, "day": day_of_week})

                elapsed_h = int(cumulative_time / 60.0)
                plot2_raw.append({"elapsed_hour": elapsed_h, "score": sc, "weight": w, "day": day_of_week})

                if day_of_week is not None:
                    plot3_raw.append({"day": day_of_week, "score": sc, "weight": w})

            cumulative_time += dur

    hour_scores = {h: {"sum_score_weight": 0.0, "sum_weight": 0.0} for h in range(24)}
    for item in plot1_raw:
        if plot1_filter == "All Days" or item["day"] == plot1_filter:
            h = item["hour"]
            hour_scores[h]["sum_score_weight"] += item["score"] * item["weight"]
            hour_scores[h]["sum_weight"] += item["weight"]
            
    p1_hours, p1_avgs = [], []
    for h in range(24):
        if hour_scores[h]["sum_weight"] > 0:
            p1_hours.append(h)
            p1_avgs.append(hour_scores[h]["sum_score_weight"] / hour_scores[h]["sum_weight"])

    elapsed_scores = {}
    for item in plot2_raw:
        if plot1_filter == "All Days" or item["day"] == plot1_filter:
            eh = item["elapsed_hour"]
            if eh not in elapsed_scores:
                elapsed_scores[eh] = {"sum_score_weight": 0.0, "sum_weight": 0.0}
            elapsed_scores[eh]["sum_score_weight"] += item["score"] * item["weight"]
            elapsed_scores[eh]["sum_weight"] += item["weight"]

    p2_hours, p2_avgs = [], []
    for eh in sorted(elapsed_scores.keys()):
        if elapsed_scores[eh]["sum_weight"] > 0:
            p2_hours.append(eh)
            p2_avgs.append(elapsed_scores[eh]["sum_score_weight"] / elapsed_scores[eh]["sum_weight"])

    day_scores = {day: {"sum_score_weight": 0.0, "sum_weight": 0.0} for day in days_order}
    for item in plot3_raw:
        d = item["day"]
        if d in day_scores:
            day_scores[d]["sum_score_weight"] += item["score"] * item["weight"]
            day_scores[d]["sum_weight"] += item["weight"]

    p3_x_nums, p3_y_avgs = [], []
    for i, day in enumerate(days_order):
        if day_scores[day]["sum_weight"] > 0:
            p3_x_nums.append(i)
            p3_y_avgs.append(day_scores[day]["sum_score_weight"] / day_scores[day]["sum_weight"])

    return {
        "plot1": (p1_hours, p1_avgs),
        "plot2": (p2_hours, p2_avgs),
        "plot3": (p3_x_nums, p3_y_avgs),
        "days_order": days_order
    }


def generate_charts(datei_kommentare, datei_aktivitaeten, start_date="", end_date="", plot1_filter="All Days"):
    data = get_plotting_data(datei_kommentare, datei_aktivitaeten, start_date, end_date, plot1_filter)
    
    fig = Figure(figsize=(5, 14), dpi=100)
    fig.subplots_adjust(hspace=0.55)
    
    ax1 = fig.add_subplot(311)
    x1, y1 = data["plot1"]
    if x1:
        ax1.plot(x1, y1, marker='o', linestyle='-', color='tab:blue', linewidth=2, markersize=6)
        ax1.set_title(f"Avg Score by Hour ({plot1_filter}) [Weighted]", fontsize=10, pad=10)
        ax1.set_xlabel("Hour of Day (0-23)", fontsize=8)
        ax1.set_ylabel("Weighted Average Score", fontsize=8)
        ax1.set_xlim(-0.5, 23.5)
        ax1.set_ylim(0.5, 5.5)
        ax1.set_xticks(range(0, 24, 2))
        ax1.grid(True, linestyle='--', alpha=0.5)
    else:
        ax1.text(0.5, 0.5, "No data available for this filter", horizontalalignment='center', verticalalignment='center', transform=ax1.transAxes)
        ax1.set_title(f"Avg Score by Hour ({plot1_filter}) [Weighted]", fontsize=10, pad=10)

    ax2 = fig.add_subplot(312)
    x2, y2 = data["plot2"]
    if x2:
        ax2.plot(x2, y2, marker='o', linestyle='-', color='tab:orange', linewidth=2, markersize=6)
        ax2.set_title(f"Avg Score by Session Hour ({plot1_filter}) [Weighted]", fontsize=10, pad=10)
        ax2.set_xlabel("Hours into Session (0h, 1h, 2h...)", fontsize=8)
        ax2.set_ylabel("Weighted Average Score", fontsize=8)
        ax2.set_ylim(0.5, 5.5)
        ax2.grid(True, linestyle='--', alpha=0.5)
    else:
        ax2.text(0.5, 0.5, "No data available for this filter", horizontalalignment='center', verticalalignment='center', transform=ax2.transAxes)
        ax2.set_title(f"Avg Score by Session Hour ({plot1_filter}) [Weighted]", fontsize=10, pad=10)

    ax3 = fig.add_subplot(313)
    x3, y3 = data["plot3"]
    days_order = data["days_order"]
    if x3 and y3:
        ax3.plot(x3, y3, marker='o', linestyle='-', color='tab:green', linewidth=2, markersize=6)
        ax3.set_xticks(range(len(days_order)))
        ax3.set_xticklabels([d[:3] for d in days_order], fontsize=8)
        ax3.set_title("Avg Score by Day of Week [Weighted]", fontsize=10, pad=10)
        ax3.set_xlabel("Day of Week", fontsize=8)
        ax3.set_ylabel("Weighted Average Score", fontsize=8)
        ax3.set_xlim(-0.5, len(days_order) - 0.5)
        ax3.set_ylim(0.5, 5.5)
        ax3.grid(True, linestyle='--', alpha=0.5)
    else:
        ax3.text(0.5, 0.5, "No data available", horizontalalignment='center', verticalalignment='center', transform=ax3.transAxes)
        ax3.set_xticks(range(len(days_order)))
        ax3.set_xticklabels([d[:3] for d in days_order], fontsize=8)
        ax3.set_title("Avg Score by Day of Week [Weighted]", fontsize=10, pad=10)

    return fig