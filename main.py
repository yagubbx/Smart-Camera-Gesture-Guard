import os
import csv
import time
import threading
from datetime import datetime

import cv2
import mediapipe as mp
import pyttsx3
from dotenv import load_dotenv


# --------------------------------------------------
# Configuration
# --------------------------------------------------

load_dotenv()

camera_url = os.getenv("CAMERA_URL")

if not camera_url:
    raise ValueError("CAMERA_URL was not found in the .env file!")


EVIDENCE_DIR = "evidence"
EVENTS_FILE = "events.csv"

COUNTDOWN_SECONDS = 5
GESTURE_HOLD_SECONDS = 2

os.makedirs(EVIDENCE_DIR, exist_ok=True)


# --------------------------------------------------
# Create CSV event log
# --------------------------------------------------

if not os.path.exists(EVENTS_FILE):
    with open(EVENTS_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow(
            [
                "timestamp",
                "event",
                "duration_seconds",
                "evidence_file",
            ]
        )


# --------------------------------------------------
# Camera
# --------------------------------------------------

cap = cv2.VideoCapture(camera_url)

if not cap.isOpened():
    raise RuntimeError("Could not open the camera stream!")


# --------------------------------------------------
# MediaPipe Hands
# --------------------------------------------------

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6,
)


# --------------------------------------------------
# Application state
# --------------------------------------------------

protected_area = None

intrusion_start_time = None
last_spoken_number = None

alarm_triggered = False
evidence_saved = False

gesture_start_time = None
access_granted_time = None

system_armed = True

speech_lock = threading.Lock()

window_name = "AI Object Guard"


# --------------------------------------------------
# Session statistics
# --------------------------------------------------

session_intrusions = 0
evidence_count = 0
longest_intrusion = 0.0
successful_disarms = 0


# --------------------------------------------------
# Speech
# --------------------------------------------------

def speak(text):
    """Speak without blocking the video loop."""

    def worker():

        with speech_lock:

            engine = pyttsx3.init()

            engine.setProperty(
                "rate",
                170,
            )

            engine.say(text)
            engine.runAndWait()

            engine.stop()

    threading.Thread(
        target=worker,
        daemon=True,
    ).start()


# --------------------------------------------------
# Alarm
# --------------------------------------------------

def trigger_alarm():
    """Play an alarm sound in the background."""

    def worker():

        try:
            import winsound

            for _ in range(5):

                winsound.Beep(
                    1200,
                    200,
                )

                winsound.Beep(
                    800,
                    200,
                )

        except Exception:
            print("ALARM!")

    threading.Thread(
        target=worker,
        daemon=True,
    ).start()


# --------------------------------------------------
# Victory gesture detection
# --------------------------------------------------

def is_victory_gesture(hand_landmarks):
    """
    Detect a simple victory sign.

    Index finger  = UP
    Middle finger = UP
    Ring finger   = DOWN
    Pinky finger  = DOWN
    """

    landmarks = hand_landmarks.landmark

    # Finger tip and PIP joint IDs
    index_tip = landmarks[8]
    index_pip = landmarks[6]

    middle_tip = landmarks[12]
    middle_pip = landmarks[10]

    ring_tip = landmarks[16]
    ring_pip = landmarks[14]

    pinky_tip = landmarks[20]
    pinky_pip = landmarks[18]


    # In image coordinates:
    # smaller Y means the point is higher
    index_up = (
        index_tip.y < index_pip.y
    )

    middle_up = (
        middle_tip.y < middle_pip.y
    )

    ring_down = (
        ring_tip.y > ring_pip.y
    )

    pinky_down = (
        pinky_tip.y > pinky_pip.y
    )


    return (
        index_up
        and middle_up
        and ring_down
        and pinky_down
    )


# --------------------------------------------------
# Save evidence
# --------------------------------------------------

def save_evidence(frame, duration):

    global session_intrusions
    global evidence_count
    global longest_intrusion

    now = datetime.now()

    timestamp_display = now.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    timestamp_filename = now.strftime(
        "%Y-%m-%d_%H-%M-%S"
    )


    filename = (
        f"intrusion_"
        f"{timestamp_filename}.jpg"
    )

    filepath = os.path.join(
        EVIDENCE_DIR,
        filename,
    )


    evidence_frame = frame.copy()


    cv2.putText(
        evidence_frame,
        "INTRUSION DETECTED",
        (30, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 0, 255),
        3,
    )


    cv2.putText(
        evidence_frame,
        timestamp_display,
        (30, 90),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 255),
        2,
    )


    cv2.putText(
        evidence_frame,
        f"Duration: {duration:.1f} sec",
        (30, 125),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 255),
        2,
    )


    cv2.imwrite(
        filepath,
        evidence_frame,
    )


    with open(
        EVENTS_FILE,
        "a",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                timestamp_display,
                "INTRUSION",
                f"{duration:.2f}",
                filename,
            ]
        )


    session_intrusions += 1
    evidence_count += 1

    if duration > longest_intrusion:
        longest_intrusion = duration


    print()
    print("INTRUSION DETECTED")
    print(f"Time: {timestamp_display}")
    print(
        f"Evidence saved: {filepath}"
    )
    print()


# --------------------------------------------------
# Instructions
# --------------------------------------------------

print("Camera connected!")
print("AI Object Guard started!")
print()
print("S = Select protected area")
print("R = Reset protected area")
print("A = Arm system")
print("Q = Quit")
print()
print(
    "Victory gesture for 2 seconds "
    "= Disarm"
)


# --------------------------------------------------
# Main loop
# --------------------------------------------------

while True:

    ret, frame = cap.read()

    if not ret:
        print(
            "Could not read a frame "
            "from the camera stream."
        )
        break


    # Mirror view
    frame = cv2.flip(
        frame,
        1,
    )

    height, width, _ = frame.shape


    rgb_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB,
    )

    results = hands.process(
        rgb_frame
    )


    hand_inside = False
    victory_detected = False


    # --------------------------------------------------
    # Hand processing
    # --------------------------------------------------

    if results.multi_hand_landmarks:

        for hand_landmarks in (
            results.multi_hand_landmarks
        ):

            # Draw 21 hand landmarks
            mp_drawing.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
            )


            # Check Victory gesture
            if is_victory_gesture(
                hand_landmarks
            ):
                victory_detected = True


            # Check protected area
            if (
                protected_area
                and system_armed
            ):

                x1, y1, x2, y2 = (
                    protected_area
                )

                for landmark in (
                    hand_landmarks.landmark
                ):

                    landmark_x = int(
                        landmark.x * width
                    )

                    landmark_y = int(
                        landmark.y * height
                    )


                    if (
                        x1
                        <= landmark_x
                        <= x2
                        and
                        y1
                        <= landmark_y
                        <= y2
                    ):

                        hand_inside = True
                        break


    # --------------------------------------------------
    # Intrusion countdown
    # --------------------------------------------------

    countdown_number = None


    if (
        protected_area
        and hand_inside
        and system_armed
    ):

        if intrusion_start_time is None:

            intrusion_start_time = (
                time.time()
            )

            last_spoken_number = None
            alarm_triggered = False
            evidence_saved = False


        elapsed = (
            time.time()
            - intrusion_start_time
        )


        countdown_number = (
            COUNTDOWN_SECONDS
            - int(elapsed)
        )


        if countdown_number >= 1:

            if (
                countdown_number
                != last_spoken_number
            ):

                words = {
                    5: "Five",
                    4: "Four",
                    3: "Three",
                    2: "Two",
                    1: "One",
                }


                speak(
                    words[
                        countdown_number
                    ]
                )

                last_spoken_number = (
                    countdown_number
                )


        else:

            countdown_number = None


            if not alarm_triggered:

                speak(
                    "Warning! "
                    "Do not touch!"
                )

                trigger_alarm()

                alarm_triggered = True


            if not evidence_saved:

                duration = (
                    time.time()
                    - intrusion_start_time
                )

                save_evidence(
                    frame,
                    duration,
                )

                evidence_saved = True


    elif not hand_inside:

        intrusion_start_time = None
        last_spoken_number = None

        if not alarm_triggered:
            evidence_saved = False


    # --------------------------------------------------
    # Victory gesture / Disarm
    # --------------------------------------------------

    if (
        alarm_triggered
        and system_armed
        and victory_detected
    ):

        if gesture_start_time is None:

            gesture_start_time = (
                time.time()
            )


        gesture_duration = (
            time.time()
            - gesture_start_time
        )


        if (
            gesture_duration
            >= GESTURE_HOLD_SECONDS
        ):

            system_armed = False
            alarm_triggered = False

            intrusion_start_time = None
            last_spoken_number = None

            gesture_start_time = None

            access_granted_time = (
                time.time()
            )

            successful_disarms += 1

            speak(
                "Access granted. "
                "System disarmed."
            )

            print()
            print("ACCESS GRANTED")
            print("SYSTEM DISARMED")
            print()


    else:

        if not victory_detected:
            gesture_start_time = None


    # --------------------------------------------------
    # Protected area display
    # --------------------------------------------------

    if protected_area:

        x1, y1, x2, y2 = (
            protected_area
        )


        if not system_armed:

            color = (
                150,
                150,
                150,
            )

            area_text = (
                "SYSTEM DISARMED"
            )


        elif hand_inside:

            color = (
                0,
                0,
                255,
            )

            area_text = (
                "HAND DETECTED!"
            )


        else:

            color = (
                0,
                255,
                0,
            )

            area_text = (
                "PROTECTED AREA"
            )


        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            color,
            3,
        )


        cv2.putText(
            frame,
            area_text,
            (
                x1,
                max(
                    y1 - 10,
                    30,
                ),
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            color,
            2,
        )


    # --------------------------------------------------
    # Countdown display
    # --------------------------------------------------

    if countdown_number is not None:

        countdown_text = str(
            countdown_number
        )


        text_size = cv2.getTextSize(
            countdown_text,
            cv2.FONT_HERSHEY_SIMPLEX,
            4,
            8,
        )[0]


        text_x = (
            width
            - text_size[0]
        ) // 2

        text_y = (
            height
            + text_size[1]
        ) // 2


        cv2.putText(
            frame,
            countdown_text,
            (
                text_x,
                text_y,
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            4,
            (0, 0, 255),
            8,
        )


    # --------------------------------------------------
    # Alarm display
    # --------------------------------------------------

    if (
        alarm_triggered
        and system_armed
    ):

        cv2.putText(
            frame,
            "DO NOT TOUCH!",
            (40, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            (0, 0, 255),
            4,
        )


        cv2.putText(
            frame,
            "Show V sign for 2 sec",
            (40, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
        )


    # --------------------------------------------------
    # Gesture progress
    # --------------------------------------------------

    if (
        gesture_start_time
        is not None
        and victory_detected
    ):

        gesture_duration = (
            time.time()
            - gesture_start_time
        )


        remaining = max(
            0,
            GESTURE_HOLD_SECONDS
            - gesture_duration,
        )


        cv2.putText(
            frame,
            f"V SIGN: {remaining:.1f}s",
            (
                40,
                height - 60,
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
        )


    # --------------------------------------------------
    # Access granted message
    # --------------------------------------------------

    if access_granted_time:

        if (
            time.time()
            - access_granted_time
            < 3
        ):

            message = (
                "ACCESS GRANTED"
            )


            size = cv2.getTextSize(
                message,
                cv2.FONT_HERSHEY_SIMPLEX,
                1.5,
                4,
            )[0]


            cv2.putText(
                frame,
                message,
                (
                    (
                        width
                        - size[0]
                    ) // 2,
                    height // 2,
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.5,
                (0, 255, 0),
                4,
            )

        else:

            access_granted_time = None


    # --------------------------------------------------
    # System status
    # --------------------------------------------------

    if system_armed:

        status = "ARMED"
        status_color = (
            0,
            255,
            0,
        )

    else:

        status = "DISARMED"
        status_color = (
            150,
            150,
            150,
        )


    cv2.putText(
        frame,
        f"SYSTEM: {status}",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        status_color,
        2,
    )


    # --------------------------------------------------
    # Date and time
    # --------------------------------------------------

    current_time = (
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )


    cv2.putText(
        frame,
        current_time,
        (
            20,
            height - 20,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2,
    )


    # --------------------------------------------------
    # Display
    # --------------------------------------------------

    cv2.imshow(
        window_name,
        frame,
    )


    key = (
        cv2.waitKey(1)
        & 0xFF
    )


    # --------------------------------------------------
    # Select protected area
    # --------------------------------------------------

    if key == ord("s"):

        print(
            "Select the protected area "
            "and press ENTER."
        )


        roi = cv2.selectROI(
            "Select Protected Area",
            frame,
            showCrosshair=True,
            fromCenter=False,
        )


        cv2.destroyWindow(
            "Select Protected Area"
        )


        x, y, w, h = map(
            int,
            roi,
        )


        if w > 0 and h > 0:

            protected_area = (
                x,
                y,
                x + w,
                y + h,
            )

            system_armed = True

            intrusion_start_time = None
            last_spoken_number = None

            alarm_triggered = False
            evidence_saved = False
            gesture_start_time = None

            print(
                "Protected area selected!"
            )


    # --------------------------------------------------
    # Reset
    # --------------------------------------------------

    elif key == ord("r"):

        protected_area = None

        intrusion_start_time = None
        last_spoken_number = None

        alarm_triggered = False
        evidence_saved = False

        gesture_start_time = None

        print(
            "Protected area reset."
        )


    # --------------------------------------------------
    # Re-arm system
    # --------------------------------------------------

    elif key == ord("a"):

        system_armed = True

        intrusion_start_time = None
        last_spoken_number = None

        alarm_triggered = False
        evidence_saved = False

        gesture_start_time = None

        speak(
            "System armed."
        )

        print("SYSTEM ARMED")


    # --------------------------------------------------
    # Quit
    # --------------------------------------------------

    elif key == ord("q"):
        break


# --------------------------------------------------
# Cleanup
# --------------------------------------------------

hands.close()
cap.release()
cv2.destroyAllWindows()


# --------------------------------------------------
# Session summary
# --------------------------------------------------

print()
print("=" * 38)
print("SESSION SUMMARY")
print("=" * 38)

print(
    f"Intrusions: "
    f"{session_intrusions}"
)

print(
    f"Evidence captured: "
    f"{evidence_count}"
)

print(
    f"Successful disarms: "
    f"{successful_disarms}"
)

print(
    f"Longest intrusion: "
    f"{longest_intrusion:.1f} seconds"
)

print("=" * 38)