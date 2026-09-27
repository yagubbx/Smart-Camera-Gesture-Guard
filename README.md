# AI Object Guard

AI Object Guard is a small real-time computer vision project that uses a smartphone camera to protect a selected area.

The system tracks hands, detects when a hand enters the protected area, starts a voice countdown, and triggers an alarm if the hand stays there.

## Features

- Live smartphone camera stream
- Real-time hand tracking with 21 landmarks
- Custom protected area
- Voice countdown from 5 to 1
- Intrusion alarm
- Automatic evidence capture
- CSV event logging
- Victory sign (V) to disarm the system
- Armed and disarmed modes

## How It Works

```text
Smartphone Camera
        ↓
      OpenCV
        ↓
  MediaPipe Hands
        ↓
  Protected Area
        ↓
  Hand Detected
        ↓
   5 → 4 → 3 → 2 → 1
        ↓
 Alarm + Evidence
        ↓
 V Sign → Disarm
```

## Controls

| Key | Action |
|---|---|
| `S` | Select protected area |
| `R` | Reset protected area |
| `A` | Arm the system |
| `Q` | Quit |

## Gesture Disarm

After the alarm starts, show a **V / Victory sign** to the camera and hold it for about 2 seconds.

```text
V Sign → Access Granted → System Disarmed
```

Press `A` to arm the system again.

## Technologies

Python, OpenCV, MediaPipe, pyttsx3

## Setup

Full installation and usage instructions are available in [START.md](START.md).

## Note

Camera settings are stored in `.env`. Evidence images and event logs are created locally and are not included in the repository.