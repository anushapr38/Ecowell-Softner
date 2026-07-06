"""
Ecowell - Firebase Fault Monitor & Email Alert System
Reads sensor data from Firebase Realtime Database, detects fault states,
and sends email notifications to admin when regeneration is required.

Requirements:
    pip install firebase-admin requests
"""

import firebase_admin
from firebase_admin import credentials, db
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import json
import os
from datetime import datetime
import logging
import sys
import requests

# ========== FIX WINDOWS CONSOLE ENCODING ==========
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ========== CONFIGURATION ==========
# Firebase configuration (using your existing config)
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyAUmszBpqnVaftWt_807NDGOXQJSY6ErvA",
    "authDomain": "ecowell-iot-project.firebaseapp.com",
    "databaseURL": "https://ecowell-iot-project-default-rtdb.asia-southeast1.firebasedatabase.app",
    "projectId": "ecowell-iot-project",
    "storageBucket": "ecowell-iot-project.firebasestorage.app",
    "messagingSenderId": "14292512544",
    "appId": "1:14292512544:web:d2279da621b8e5ec6ef145"
}

# Database reference
DEVICE_ID = "softener-01"
DATABASE_URL = FIREBASE_CONFIG["databaseURL"]

# Email configuration (Gmail example - use App Password)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "ecowellorganisation2026@gmail.com"  # Replace with your email
EMAIL_PASSWORD = "zxnm luse qcpb cqtm"   # Replace with your Gmail App Password
EMAIL_RECIPIENT = "anushapr39@gmail.com"  # Replace with admin email
# Thresholds (same as in the simulator)
THRESHOLDS = {
    "salt": {"low": 25, "critical": 15},
    "tds": {"elevated": 350, "critical": 600},
    "pressure": {"low": 1.5, "critical": 0.5},
    "flow": {"low": 3, "critical": 0.1}
}

# Check interval in seconds
CHECK_INTERVAL = 10

# Track sent notifications to avoid spamming
NOTIFICATION_COOLDOWN = 300  # 5 minutes cooldown between notifications
last_notification_time = 0

# ========== LOGGING SETUP ==========
# Remove emojis from log messages to avoid encoding issues
def clean_message(msg):
    """Remove emoji characters from log messages for Windows console."""
    # Simple approach: replace common emojis with text equivalents
    replacements = {
        '🚀': '[START] ',
        '📡': '[DEVICE] ',
        '⏱️': '[TIME] ',
        '📧': '[EMAIL] ',
        '✅': '[OK] ',
        '⚠️': '[WARNING] ',
        '❌': '[ERROR] ',
        '🔹': '[INFO] ',
        '📊': '[DATA] ',
        '🔧': '[ACTION] ',
        '🛑': '[STOP] ',
        '🌊': '[ECOWELL] ',
        '📋': '[CONFIG] ',
        '📧': '[EMAIL] ',
    }
    for emoji, text in replacements.items():
        msg = msg.replace(emoji, text)
    return msg

class SafeLogger:
    """Wrapper for logger that cleans messages before logging."""
    def __init__(self, logger):
        self.logger = logger
    
    def info(self, msg, *args, **kwargs):
        self.logger.info(clean_message(msg), *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        self.logger.warning(clean_message(msg), *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        self.logger.error(clean_message(msg), *args, **kwargs)
    
    def debug(self, msg, *args, **kwargs):
        self.logger.debug(clean_message(msg), *args, **kwargs)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ecowell_monitor.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = SafeLogger(logging.getLogger(__name__))

# ========== FIREBASE REST API HELPERS ==========
def get_firebase_data(path):
    """Fetch data from Firebase Realtime Database using REST API."""
    try:
        url = f"{DATABASE_URL}{path}.json"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to fetch data: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return None

# ========== FAULT DETECTION ==========
def check_fault_conditions(sensors):
    """
    Check sensor data against thresholds and return list of fault reasons.
    
    Args:
        sensors: Dictionary containing sensor readings
        
    Returns:
        List of fault reason strings, empty if no faults
    """
    faults = []
    
    if not sensors:
        return ["No sensor data available"]
    
    # Check pressure
    pressure = sensors.get('pressure', 0)
    if pressure < THRESHOLDS['pressure']['critical']:
        faults.append(f"Pressure critically low: {pressure:.2f} bar (threshold: {THRESHOLDS['pressure']['critical']} bar)")
    elif pressure < THRESHOLDS['pressure']['low']:
        faults.append(f"Pressure low: {pressure:.2f} bar (threshold: {THRESHOLDS['pressure']['low']} bar)")
    
    # Check TDS
    tds = sensors.get('tds', 0)
    if tds > THRESHOLDS['tds']['critical']:
        faults.append(f"TDS critically high: {tds:.0f} ppm (threshold: {THRESHOLDS['tds']['critical']} ppm)")
    elif tds > THRESHOLDS['tds']['elevated']:
        faults.append(f"TDS elevated: {tds:.0f} ppm (threshold: {THRESHOLDS['tds']['elevated']} ppm)")
    
    # Check salt
    salt = sensors.get('salt', 0)
    if salt < THRESHOLDS['salt']['critical']:
        faults.append(f"Salt level critically low: {salt:.0f}% (threshold: {THRESHOLDS['salt']['critical']}%)")
    elif salt < THRESHOLDS['salt']['low']:
        faults.append(f"Salt level low: {salt:.0f}% (threshold: {THRESHOLDS['salt']['low']}%)")
    
    # Check flow
    flow = sensors.get('flow', 0)
    if flow < THRESHOLDS['flow']['critical']:
        faults.append(f"Flow rate critically low: {flow:.1f} L/min (threshold: {THRESHOLDS['flow']['critical']} L/min)")
    elif flow < THRESHOLDS['flow']['low']:
        faults.append(f"Flow rate low: {flow:.1f} L/min (threshold: {THRESHOLDS['flow']['low']} L/min)")
    
    return faults

# ========== EMAIL NOTIFICATION ==========
def send_notification(sensor_data, fault_reasons, device_id=DEVICE_ID):
    """
    Send email notification to admin about fault state.
    
    Args:
        sensor_data: Dictionary containing sensor readings
        fault_reasons: List of fault reasons
        device_id: Device identifier
    """
    global last_notification_time
    
    # Check cooldown
    current_time = time.time()
    if current_time - last_notification_time < NOTIFICATION_COOLDOWN:
        logger.info(f"Notification cooldown active. Last sent {int((current_time - last_notification_time))}s ago")
        return False
    
    try:
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = f"URGENT: Regeneration Required - {device_id}"

        # Build sensor status table rows
        sensor_rows = []
        sensor_labels = [
            ('Pressure', 'pressure', 'bar', '{:.2f}'),
            ('TDS', 'tds', 'ppm', '{:.0f}'),
            ('Salt Level', 'salt', '%', '{:.0f}'),
            ('Flow Rate', 'flow', 'L/min', '{:.1f}')
        ]
        
        for label, key, unit, fmt in sensor_labels:
            value = sensor_data.get(key, 0)
            # Determine status
            if key == 'pressure':
                if value < THRESHOLDS['pressure']['critical']:
                    status, color = 'CRITICAL', '#cc4444'
                elif value < THRESHOLDS['pressure']['low']:
                    status, color = 'LOW', '#856404'
                else:
                    status, color = 'NORMAL', '#1a7a4a'
            elif key == 'tds':
                if value > THRESHOLDS['tds']['critical']:
                    status, color = 'CRITICAL', '#cc4444'
                elif value > THRESHOLDS['tds']['elevated']:
                    status, color = 'ELEVATED', '#856404'
                else:
                    status, color = 'NORMAL', '#1a7a4a'
            elif key == 'salt':
                if value < THRESHOLDS['salt']['critical']:
                    status, color = 'CRITICAL', '#cc4444'
                elif value < THRESHOLDS['salt']['low']:
                    status, color = 'LOW', '#856404'
                else:
                    status, color = 'NORMAL', '#1a7a4a'
            elif key == 'flow':
                if value < THRESHOLDS['flow']['critical']:
                    status, color = 'CRITICAL', '#cc4444'
                elif value < THRESHOLDS['flow']['low']:
                    status, color = 'LOW', '#856404'
                else:
                    status, color = 'NORMAL', '#1a7a4a'
            else:
                status, color = 'UNKNOWN', '#888888'
            
            sensor_rows.append(
                f'<tr><td style="padding: 6px;">{label}</td>'
                f'<td style="padding: 6px; text-align: right;">{fmt.format(value)} {unit}</td>'
                f'<td style="padding: 6px; text-align: right; color: {color}; font-weight: bold;">{status}</td></tr>'
            )

        # Build email body
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #cc4444;">REGENERATION REQUIRED</h2>
            <p style="font-size: 16px; color: #cc4444; font-weight: bold;">
                The water softener system has detected critical conditions requiring immediate regeneration.
            </p>
            
            <div style="background: #f8f8f8; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <h3 style="margin-top: 0;">Device Information</h3>
                <p><strong>Device ID:</strong> {device_id}</p>
                <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>

            <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #ffc107;">
                <h3 style="margin-top: 0; color: #856404;">Fault Reasons</h3>
                <ul>
                    {''.join(f'<li style="padding: 4px 0;">{reason}</li>' for reason in fault_reasons)}
                </ul>
            </div>

            <div style="background: #e8f4fd; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <h3 style="margin-top: 0;">Current Sensor Readings</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="background: #d1e7f5;">
                        <th style="padding: 8px; text-align: left;">Sensor</th>
                        <th style="padding: 8px; text-align: right;">Value</th>
                        <th style="padding: 8px; text-align: right;">Status</th>
                    </tr>
                    {''.join(sensor_rows)}
                </table>
            </div>

            <div style="background: #f8f8f8; padding: 12px; border-radius: 8px; margin: 15px 0;">
                <h4 style="margin: 0;">Recommended Action</h4>
                <p style="margin: 8px 0 0 0; color: #555;">
                    Please <strong>initiate regeneration</strong> immediately using the simulator panel 
                    or the remote command interface.
                </p>
            </div>

            <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;" />
            <p style="font-size: 12px; color: #888;">
                This is an automated notification from the Ecowell IoT Monitoring System.
                <br />Device: {device_id} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, 'html'))

        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

        last_notification_time = current_time
        logger.info(f"Notification email sent to {EMAIL_RECIPIENT}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

# ========== MAIN MONITORING LOOP ==========
def monitor_device():
    """Main monitoring loop that checks Firebase and sends alerts."""
    logger.info("[START] Starting Ecowell Fault Monitor...")
    logger.info(f"[DEVICE] Monitoring device: {DEVICE_ID}")
    logger.info(f"[TIME] Check interval: {CHECK_INTERVAL}s")
    logger.info(f"[EMAIL] Alerts will be sent to: {EMAIL_RECIPIENT}")
    logger.info("-" * 50)

    consecutive_faults = 0
    last_fault_state = False

    while True:
        try:
            # Fetch device data from Firebase
            device_data = get_firebase_data(f"/devices/{DEVICE_ID}")
            
            if not device_data:
                logger.warning("No data received from Firebase")
                time.sleep(CHECK_INTERVAL)
                continue

            # Extract sensors
            sensors = device_data.get('sensors', {})
            fault_state = device_data.get('fault', False)
            state = device_data.get('state', 'UNKNOWN')

            # Check for fault conditions based on thresholds
            fault_reasons = check_fault_conditions(sensors)

            # Also check if Firebase explicitly reports fault
            if fault_state or state == 'FAULT':
                if not fault_reasons:
                    fault_reasons = ["Device reported FAULT state"]

            # Log current state
            if fault_reasons:
                logger.warning(f"[WARNING] Fault detected: {', '.join(fault_reasons)}")
                consecutive_faults += 1
                
                # Send notification if this is a new fault or sustained fault
                if not last_fault_state or consecutive_faults % 3 == 0:
                    send_notification(sensors, fault_reasons, DEVICE_ID)
                
                last_fault_state = True
            else:
                if last_fault_state:
                    logger.info("[OK] System back to normal state")
                    consecutive_faults = 0
                    last_fault_state = False
                else:
                    logger.info(f"[OK] All sensors normal | Flow: {sensors.get('flow', 0):.1f} L/min | TDS: {sensors.get('tds', 0):.0f} ppm | Salt: {sensors.get('salt', 0):.0f}% | Pressure: {sensors.get('pressure', 0):.2f} bar")

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            logger.info("[STOP] Monitoring stopped by user")
            break
        except Exception as e:
            logger.error(f"[ERROR] Error in monitoring loop: {e}")
            time.sleep(CHECK_INTERVAL)

# ========== ENTRY POINT ==========
if __name__ == "__main__":
    print("=" * 60)
    print("  Ecowell - Firebase Fault Monitor & Alert System")
    print("=" * 60)
    print()
    print("Configuration:")
    print(f"  Database: {DATABASE_URL}")
    print(f"  Device ID: {DEVICE_ID}")
    print(f"  Check Interval: {CHECK_INTERVAL}s")
    print(f"  Email Recipient: {EMAIL_RECIPIENT}")
    print(f"  Cooldown: {NOTIFICATION_COOLDOWN}s between emails")
    print()
    print("To enable email notifications, update these variables:")
    print("  - EMAIL_SENDER = 'your-email@gmail.com'")
    print("  - EMAIL_PASSWORD = 'your-app-password'")
    print()
    print("For Gmail, you need to:")
    print("  1. Enable 2-Factor Authentication")
    print("  2. Generate an App Password (Settings > Security > App Passwords)")
    print()
    print("Press Ctrl+C to stop")
    print("-" * 60)
    
    # Start monitoring
    monitor_device()
