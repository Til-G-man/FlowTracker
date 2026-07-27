import time
import cv2
import os
import csv
from datetime import datetime

class EyeTrackerManager:
    def __init__(self, session_id, activity, energy_saver=False, output_dir=None):
        self.session_id = session_id
        self.activity = activity
        self.energy_saver = energy_saver
        self.output_dir = output_dir or os.path.expanduser("~")
        self.running = False
        self.thread = None
        self.blink_count = 0
        self.frames_analyzed = 0
        self.start_time = 0
        self.gaze_events = []  # Speichert die Ereignisse (Weggeschaut / Zurückgeschaut)

    def start(self):
        if self.running:
            return
        self.running = True
        self.start_time = time.time()
        self.blink_count = 0
        self.frames_analyzed = 0
        self.gaze_events = []
        
        import threading
        self.thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        self._save_stats()

    def _tracking_loop(self):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                self.running = False
                return

        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

        target_interval = 0.5 if self.energy_saver else 0.1

        eyes_previously_seen = True
        blink_cooldown = 0
        
        # Status-Variablen für Blickrichtung (Bildschirm vs. Weggeschaut)
        is_looking_at_screen = True
        missing_face_count = 0
        present_face_count = 0
        # Schwellenwert: Nach wie vielen konsekutiven Frames ohne Gesicht gilt man als "weggeschaut"
        missing_threshold = 3 if not self.energy_saver else 2

        try:
            while self.running:
                loop_start = time.time()
                ret, frame = cap.read()
                
                if not ret or frame is None:
                    time.sleep(1.0)
                    continue

                self.frames_analyzed += 1
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
                face_detected = len(faces) > 0

                # --- Blick-Status-Logik (Weggeschaut / Am Bildschirm) ---
                if face_detected:
                    missing_face_count = 0
                    present_face_count += 1
                    if not is_looking_at_screen and present_face_count >= 2:
                        is_looking_at_screen = True
                        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.gaze_events.append([self.session_id, self.activity, "Looked back at screen", timestamp_str])
                else:
                    present_face_count = 0
                    missing_face_count += 1
                    if is_looking_at_screen and missing_face_count >= missing_threshold:
                        is_looking_at_screen = False
                        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.gaze_events.append([self.session_id, self.activity, "Looked away from screen", timestamp_str])

                # --- Blinzel-Erkennung (nur im Normalmodus) ---
                if not self.energy_saver and face_detected:
                    eyes_found = False
                    for (x, y, w, h) in faces:
                        roi_gray = gray[y:y+h, x:x+w]
                        eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=3)
                        if len(eyes) >= 1:
                            eyes_found = True
                        break
                    
                    if blink_cooldown > 0:
                        blink_cooldown -= 1
                    else:
                        if eyes_previously_seen and not eyes_found:
                            self.blink_count += 1
                            blink_cooldown = 5
                            
                    eyes_previously_seen = eyes_found

                elapsed = time.time() - loop_start
                sleep_time = target_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except Exception as e:
            print(f"[EyeTracker Fehler]: {e}")
        finally:
            cap.release()

    def _save_stats(self):
        if self.frames_analyzed == 0:
            return
        
        # 1. Allgemeine Statistiken speichern
        filename_stats = os.path.join(self.output_dir, "eye_stats.csv")
        mode_used = "EnergySaver (2 FPS, No Blinks)" if self.energy_saver else "Normal (OpenCV Tracking & Blinks)"
        duration_mins = round((time.time() - self.start_time) / 60, 2)

        file_exists = os.path.exists(filename_stats)
        with open(filename_stats, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["session_id", "activity", "mode", "blink_count", "frames_analyzed", "duration_mins", "timestamp"])
            writer.writerow([
                self.session_id,
                self.activity,
                mode_used,
                self.blink_count if not self.energy_saver else "N/A (Energy Saver)",
                self.frames_analyzed,
                duration_mins,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])

        # 2. Gaze-Events (Weggeschaut / Zurückgeschaut) in separater Datei speichern
        if self.gaze_events:
            filename_events = os.path.join(self.output_dir, "eye_gaze_events.csv")
            events_exist = os.path.exists(filename_events)
            with open(filename_events, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not events_exist:
                    writer.writerow(["session_id", "activity", "event_type", "timestamp"])
                writer.writerows(self.gaze_events)