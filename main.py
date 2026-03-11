import cv2
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from deepface import DeepFace
import threading
import os
import queue
import time
from datetime import datetime

# --- CONFIGURATION & STYLING ---
COLOR_BG = "#1e1e2e"
COLOR_FG = "#cdd6f4"
COLOR_ACCENT = "#89b4fa"
COLOR_PANEL = "#313244"
COLOR_SUCCESS = "#a6e3a1"
COLOR_DANGER = "#f38ba8"
COLOR_WARNING = "#fab387"

EMOTIONS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
EMOTION_COLORS = {
    "angry": "#f38ba8",
    "disgust": "#94e2d5",
    "fear": "#cba6f7",
    "happy": "#a6e3a1",
    "sad": "#89b4fa",
    "surprise": "#fab387",
    "neutral": "#bac2de"
}

EMOTION_QUOTES = {
    "angry": "Stay calm and keep moving forward.",
    "disgust": "Focus on the positive aspects around you.",
    "fear": "Fear is temporary; courage is eternal.",
    "happy": "Happiness is a choice. Choose it.",
    "sad": "Every cloud has a silver lining.",
    "surprise": "Life is full of wonderful surprises.",
    "neutral": "Balance is the key to focus."
}

class EmotionAnalyzer(threading.Thread):
    """Background thread for performance-intensive emotion analysis."""
    def __init__(self, input_queue, result_queue):
        super().__init__(daemon=True)
        self.input_queue = input_queue
        self.result_queue = result_queue
        self.running = True

    def run(self):
        while self.running:
            try:
                frame = self.input_queue.get(timeout=1)
                if frame is None: continue
                # Perform analysis
                result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False, silent=True)
                self.result_queue.put(result[0])
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Analysis Thread Error: {e}")

class PremiumFERApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Face Emotion Recognition - Premium Edition")
        self.root.geometry("1100x700")
        self.root.configure(bg=COLOR_BG)

        # Ensure directory for snapshots
        if not os.path.exists("snapshots"):
            os.makedirs("snapshots")

        # State management
        self.cap = None
        self.is_capturing = False
        self.current_emotion = "neutral"
        self.emotion_scores = {e: 0 for e in EMOTIONS}
        self.analysis_input_q = queue.Queue(maxsize=1)
        self.analysis_result_q = queue.Queue()
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        # Start analysis thread
        self.analyzer = EmotionAnalyzer(self.analysis_input_q, self.analysis_result_q)
        self.analyzer.start()

        self._setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_ui(self):
        """Build the premium dark-themed UI."""
        # Main container with padding
        self.main_container = tk.Frame(self.root, bg=COLOR_BG, padx=20, pady=20)
        self.main_container.pack(expand=True, fill="both")

        # --- LEFT PANEL: VIDEO FEED ---
        self.left_panel = tk.Frame(self.main_container, bg=COLOR_BG)
        self.left_panel.pack(side="left", expand=True, fill="both")

        self.video_container = tk.Frame(self.left_panel, bg="black", bd=2, relief="flat")
        self.video_container.pack(expand=True, fill="both", pady=(0, 10))
        
        self.video_label = tk.Label(self.video_container, bg="black")
        self.video_label.pack(expand=True, fill="both")

        # Controls panel
        self.controls = tk.Frame(self.left_panel, bg=COLOR_BG)
        self.controls.pack(fill="x")

        self.btn_start = tk.Button(self.controls, text="Start Live Feed", command=self.toggle_capture, 
                                  bg=COLOR_SUCCESS, fg=COLOR_BG, font=("Helvetica", 12, "bold"), 
                                  padx=20, pady=10, relief="flat", activebackground="#94e2d5")
        self.btn_start.pack(side="left", padx=5)

        self.btn_snapshot = tk.Button(self.controls, text="Capture Snapshot", command=self.take_snapshot,
                                     bg=COLOR_ACCENT, fg=COLOR_BG, font=("Helvetica", 12, "bold"),
                                     padx=20, pady=10, relief="flat", state="disabled")
        self.btn_snapshot.pack(side="left", padx=5)

        # --- RIGHT PANEL: ANALYTICS ---
        self.right_panel = tk.Frame(self.main_container, bg=COLOR_PANEL, width=350, padx=20, pady=20)
        self.right_panel.pack(side="right", fill="y", padx=(20, 0))
        self.right_panel.pack_propagate(False)

        # Header
        tk.Label(self.right_panel, text="Emotion Analytics", bg=COLOR_PANEL, fg=COLOR_FG, 
                 font=("Helvetica", 18, "bold")).pack(pady=(0, 20))

        # Emotion Meters
        self.meters = {}
        for emotion in EMOTIONS:
            f = tk.Frame(self.right_panel, bg=COLOR_PANEL)
            f.pack(fill="x", pady=5)
            
            lbl = tk.Label(f, text=emotion.capitalize(), bg=COLOR_PANEL, fg=COLOR_FG, font=("Helvetica", 10))
            lbl.pack(side="left")
            
            canvas = tk.Canvas(f, height=15, bg=COLOR_BG, highlightthickness=0)
            canvas.pack(side="right", fill="x", expand=True, padx=(10, 0))
            self.meters[emotion] = canvas

        # Dominant Emotion & Quote
        self.dominant_lbl = tk.Label(self.right_panel, text="Analyzing...", bg=COLOR_PANEL, fg=COLOR_ACCENT,
                                     font=("Helvetica", 14, "bold"))
        self.dominant_lbl.pack(pady=(30, 5))
        
        self.quote_lbl = tk.Label(self.right_panel, text="Start the feed to begin.", bg=COLOR_PANEL, fg=COLOR_FG,
                                  font=("Helvetica", 11, "italic"), wraplength=280)
        self.quote_lbl.pack(pady=10)

        # Status Bar
        self.status_bar = tk.Label(self.root, text="System Ready", bg=COLOR_PANEL, fg="#bac2de", bd=1, relief="sunken", anchor="w")
        self.status_bar.pack(side="bottom", fill="x")

    def toggle_capture(self):
        if not self.is_capturing:
            self._start()
        else:
            self._stop()

    def _start(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Could not access webcam.")
            return
        
        self.is_capturing = True
        self.btn_start.config(text="Stop Live Feed", bg=COLOR_DANGER)
        self.btn_snapshot.config(state="normal")
        self.status_bar.config(text="Analyzing Live Stream...")
        self.update_frame()

    def _stop(self):
        self.is_capturing = False
        if self.cap:
            self.cap.release()
        self.btn_start.config(text="Start Live Feed", bg=COLOR_SUCCESS)
        self.btn_snapshot.config(state="disabled")
        self.video_label.config(image="")
        self.status_bar.config(text="Feed Stopped")

    def update_frame(self):
        if not self.is_capturing: return

        ret, frame = self.cap.read()
        if not ret: return

        # Process frame for UI
        display_frame = cv2.flip(frame, 1) # Mirror effect
        
        # Face detection for visual overlay
        gray = cv2.cvtColor(display_frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        for (x, y, w, h) in faces:
            # Custom corner-brackets for a high-tech look
            length = w // 4
            cv2.line(display_frame, (x, y), (x + length, y), (137, 180, 250), 2)
            cv2.line(display_frame, (x, y), (x, y + length), (137, 180, 250), 2)
            cv2.line(display_frame, (x + w, y), (x + w - length, y), (137, 180, 250), 2)
            cv2.line(display_frame, (x + w, y), (x + w, y + length), (137, 180, 250), 2)
            cv2.line(display_frame, (x, y + h), (x + length, y + h), (137, 180, 250), 2)
            cv2.line(display_frame, (x, y + h), (x, y + h - length), (137, 180, 250), 2)
            cv2.line(display_frame, (x + w, y + h), (x + w - length, y + h), (137, 180, 250), 2)
            cv2.line(display_frame, (x + w, y + h), (x + w, y + h - length), (137, 180, 250), 2)

        # Offload analysis to thread (only if queue is empty)
        if self.analysis_input_q.empty():
            # Use the original frame for DeepFace analysis (better accuracy)
            self.analysis_input_q.put(frame.copy())

        # Check for results
        try:
            while not self.analysis_result_q.empty():
                res = self.analysis_result_q.get_nowait()
                self.emotion_scores = res['emotion']
                self.current_emotion = res['dominant_emotion']
                self.update_analytics()
        except queue.Empty:
            pass

        # Convert to TK image
        img = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        # Resize to fit panel while maintaining aspect ratio
        img.thumbnail((700, 500), Image.Resampling.LANCZOS)
        self.imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.configure(image=self.imgtk)

        self.root.after(10, self.update_frame)

    def update_analytics(self):
        """Update the side panel with latest data."""
        self.dominant_lbl.config(text=f"Feeling {self.current_emotion.upper()}", 
                                 fg=EMOTION_COLORS.get(self.current_emotion, COLOR_ACCENT))
        self.quote_lbl.config(text=EMOTION_QUOTES.get(self.current_emotion, ""))

        for emotion, canvas in self.meters.items():
            score = self.emotion_scores.get(emotion, 0)
            width = canvas.winfo_width()
            fill_width = (score / 100.0) * width
            
            canvas.delete("bar")
            canvas.create_rectangle(0, 0, fill_width, 15, fill=EMOTION_COLORS[emotion], tags="bar")

    def take_snapshot(self):
        if not self.cap: return
        ret, frame = self.cap.read()
        if ret:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"snapshots/mood_{self.current_emotion}_{ts}.jpg"
            cv2.imwrite(filename, frame)
            self.status_bar.config(text=f"Snapshot saved: {filename}")

    def _on_close(self):
        self.analyzer.running = False
        self._stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = PremiumFERApp(root)
    root.mainloop()
