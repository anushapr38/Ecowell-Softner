# 🚰 Smart Water Softener Monitoring System

A modern IoT-based Smart Water Softener Monitoring Dashboard built using HTML, CSS, JavaScript, and Firebase Realtime Database.

The system simulates a real industrial water softener by monitoring:

- 💧 Flow Rate
- ⏲️ Pressure
- ⚗️ TDS (Total Dissolved Solids)
- 🧂 Salt Level

The dashboard automatically detects abnormal conditions, displays warnings, and stores live sensor data in Firebase.

---

# 📌 Features

## Power Control

- ON/OFF Machine
- Real-time status indication
- Idle mode when power is OFF

---

## Automatic Sensor Simulation

When power is ON,

- Flow Rate automatically varies
- Pressure automatically varies
- Salt Level automatically varies
- TDS automatically varies

This simulates real industrial sensor behavior.

---

## Monitoring Mode

Click **Start Monitoring**

This enables:

- Manual sensor control
- Live slider adjustment
- Instant Firebase updates

Stop Monitoring returns the system to automatic simulation mode.

---

## Sensor Monitoring

The dashboard monitors:

### 💧 Flow Rate
- Normal Flow
- Low Flow
- High Flow
- Stalled Flow Detection

### ⏲️ Pressure
- Normal
- Low
- Critical

### ⚗️ TDS
- Good
- Elevated
- Critical

### 🧂 Salt Level
- OK
- Low
- Critical

---

# 🚨 Fault Detection

The system automatically detects abnormal conditions.

Examples:

- Low Salt
- High TDS
- Low Pressure

When critical thresholds are crossed:

- Red warning appears
- Tank changes to Critical mode
- Regeneration Required alert is shown
- Firebase state changes to FAULT

---

# 🔄 Regeneration

Click

**Regenerate Now**

The system restores all sensor values back to normal.

Normal values:

| Sensor | Value |
|---------|------|
| Flow | 5 L/min |
| Pressure | 2.5 bar |
| TDS | 150 ppm |
| Salt | 75 % |

---

# ☁ Firebase Integration

The project stores live data inside Firebase Realtime Database.

Data uploaded includes:

- Device ID
- Sensor readings
- Monitoring state
- Fault status
- Timestamp
- Power status

Database Structure:

```
devices/
    softener-01/
        sensors/
            flow
            pressure
            tds
            salt

        history/
            timestamp
            readings
```

---

# 🛠 Technologies Used

- HTML5
- CSS3
- JavaScript (ES6)
- Firebase Realtime Database
- Firebase SDK

---

# 📂 Project Structure

```
project/

│── index.html
│── README.md
```

---

# ▶ How to Run

1. Clone the repository

```
git clone https://github.com/yourusername/water-softener-monitor.git
```

2. Open

```
index.html
```

in any modern browser.

---

# Firebase Setup

Create a Firebase project.

Enable:

- Realtime Database

Replace the configuration inside:

```javascript
const firebaseConfig = {
    apiKey: "...",
    authDomain: "...",
    databaseURL: "...",
    projectId: "...",
    storageBucket: "...",
    messagingSenderId: "...",
    appId: "..."
};
```

---

# Sensor Thresholds

## Salt

| Condition | Value |
|------------|-------|
| Normal | >25% |
| Warning | <25% |
| Critical | <15% |

---

## TDS

| Condition | Value |
|------------|-------|
| Good | <350 ppm |
| Warning | >350 ppm |
| Critical | >600 ppm |

---

## Pressure

| Condition | Value |
|------------|-------|
| Normal | >1.5 bar |
| Warning | <1.5 bar |
| Critical | <0.5 bar |

---

# User Interface

The dashboard includes:

- Industrial machine design
- Animated water tank
- Live sensor cards
- Interactive sliders
- Monitoring controls
- Regeneration alert
- Firebase status indicator
- Responsive layout

---

# Future Improvements

- Arduino integration
- ESP32 support
- Real sensor inputs
- MQTT communication
- Email/SMS alerts
- Predictive maintenance
- Historical graphs
- User authentication
- Mobile application

---

# Author

**Ashwath Bheemappa Sankannavar**

IoT | Embedded Systems | Full Stack Development | Industrial Automation

---

# License

This project is released under the MIT License.
