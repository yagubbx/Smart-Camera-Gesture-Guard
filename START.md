# Getting Started

Follow these steps to run AI Object Guard on Windows.

## Requirements

- Python 3.11
- Git
- Android phone with IP Webcam
- Phone and computer on the same Wi-Fi network

## 1. Clone the Project

```powershell
git clone https://github.com/USERNAME/AI-Object-Guard.git
cd AI-Object-Guard
```

## 2. Create the Environment

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

Install the required packages:

```powershell
pip install -r requirements.txt
```

## 3. Start the Phone Camera

Open **IP Webcam** on the Android phone and select **Start server**.

The app will show an address similar to:

```text
http://192.168.1.65:8080
```

Keep the app running while using the project.

## 4. Configure the Camera

Create `.env` from the example:

```powershell
Copy-Item .env.example .env
```

Open `.env` and add your phone's IP address:

```env
CAMERA_URL=http://YOUR_PHONE_IP:8080/video
```

Example:

```env
CAMERA_URL=http://192.168.1.65:8080/video
```

## 5. Run

```powershell
python main.py
```

Press `S` and select the area you want to protect. Press **Enter** to confirm.

## Controls

| Key | Action |
|---|---|
| `S` | Select protected area |
| `R` | Reset protected area |
| `A` | Arm the system |
| `Q` | Quit |

When an alarm starts, hold a **V / Victory sign** in front of the camera for about 2 seconds to disarm the system.

Press `A` to arm it again.

## Next Time

For future runs:

```powershell
.venv\Scripts\Activate.ps1
python main.py
```

Make sure IP Webcam is running and the phone IP in `.env` is correct.