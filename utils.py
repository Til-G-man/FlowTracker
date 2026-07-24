import os
import ctypes

def lese_textdatei(dateiname):
    if not os.path.exists(dateiname): return []
    with open(dateiname, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def schreibe_textdatei(dateiname, liste):
    with open(dateiname, "w", encoding="utf-8") as f:
        for item in liste: f.write(f"{item}\n")

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
    except:
        return "Fehler", "Fehler beim Lesen"