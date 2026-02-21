import pandas as pd
import numpy as np
import glob
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.collections import LineCollection
import matplotlib.colors as mcolors


# --- CONFIG ---
G = 9.81
SUMMARY_DIR = os.path.join(os.path.dirname(__file__), 'test_data', 'summaries')
RESULTANT_PLOTS_DIR = os.path.join(os.path.dirname(__file__), 'test_data', 'resultant_plots')

if not os.path.exists(SUMMARY_DIR):
    os.makedirs(SUMMARY_DIR, exist_ok=True)
if not os.path.exists(RESULTANT_PLOTS_DIR):
    os.makedirs(RESULTANT_PLOTS_DIR, exist_ok=True)

ACCELERATION_ALERT_LEVELS = [
    {"label": "> 10g",  "value": 10 * G, "color": "#e63946", "alpha": 0.25, "linestyle": "--"},
    {"label": "> 6g",   "value":  6 * G, "color": "#f4a261", "alpha": 0.25, "linestyle": "-."},
    {"label": "> 4g",  "value":  4 * G, "color": "#aa3b9d", "alpha": 0.25, "linestyle": "--"},
    {"label": "> 3g",  "value":  3 * G, "color": "#3b62aa", "alpha": 0.25, "linestyle": "--"}
]

GYRO_ALERT_LEVELS = [
    {"label": "> 800 deg/s", "value": np.deg2rad(800), "color": "#1F945F", "alpha": 0.25, "linestyle": "--"},
    {"label": "> 500 deg/s", "value": np.deg2rad(500), "color": "#e63946", "alpha": 0.25, "linestyle": "--"},
    {"label": "> 300 deg/s", "value": np.deg2rad(300), "color": "#f4a261", "alpha": 0.25, "linestyle": "-."},
    {"label": "> 200 deg/s", "value": np.deg2rad(200), "color": "#aa3b9d", "alpha": 0.25, "linestyle": "--"},
    {"label": "> 100 deg/s", "value": np.deg2rad(100), "color": "#3b62aa", "alpha": 0.25, "linestyle": "--"}
]

# --- HELPERS ---
def calculate_resultant(csv_file):
    """
    Calculate resultant acceleration and gyroscope values from IMU CSV data.
    Resultant = sqrt(x^2 + y^2 + z^2)
    """
    # Read CSV file
    df = pd.read_csv(csv_file)
    
    # Calculate resultant acceleration
    df['acc_resultant'] = np.sqrt(df['ax']**2 + df['ay']**2 + df['az']**2)
    
    # Calculate resultant gyroscope
    df['gyro_resultant'] = np.sqrt(df['gx']**2 + df['gy']**2 + df['gz']**2)
    
    return df

def plot_with_alerts_thresholds(df, plot_basename): 
    """Plot resultant acc and gyro, highlight regions exceeding alert threshold. Saves PNG to RESULTANT_PLOTS_DIR"""
    ts  = df['ts'].values
    acc = df['acc_resultant'].values
    gyro = df['gyro_resultant'].values

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))
    fig.suptitle('Resultant Acceleration and Gyroscope with Alert Thresholds', fontsize=16)

    # --- acceleration plot --- 
    ax1.plot(ts, acc, linewidth=1, label='Acc Resultant')
    for thr in ACCELERATION_ALERT_LEVELS:
        ax1.axhline(thr['value'], color=thr['color'], linestyle=thr['linestyle'],
                    linewidth=1.2, label=thr['label'])
        ax1.fill_between(ts, thr['value'], acc,
                         where=(acc > thr['value']),
                         color=thr['color'], alpha=thr['alpha'])
    ax1.set_ylabel('Acceleration (m/s²)')
    ax1.set_title('Resultant Acceleration')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)

    # --- gyroscope plot ---
    ax2.plot(ts, gyro, linewidth=1, label='Gyro Resultant')
    for thr in GYRO_ALERT_LEVELS:
        ax2.axhline(thr['value'], color=thr['color'], linestyle=thr['linestyle'],
                    linewidth=1.2, label=thr['label'])
        ax2.fill_between(ts, thr['value'], gyro,
                         where=(gyro > thr['value']),
                         color=thr['color'], alpha=thr['alpha'])
    ax2.set_xlabel('Timestamp (ms)')
    ax2.set_ylabel('Angular Velocity (rad/s)')
    ax2.set_title('Resultant Gyroscope')
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    out_path = os.path.join(RESULTANT_PLOTS_DIR, f"{plot_basename.replace('.csv', '_resultant.png')}")
    plt.savefig(out_path, dpi=300)
    plt.close(fig)


def print_alert_summary(df, file_basename): 
    """Write to plain text file in SUMMARY_DIR of number of alerts"""
    acc = df['acc_resultant'].values
    gyro = df['gyro_resultant'].values
    ts  = df['ts'].values
    lines = []

    lines.append(f"Alert Summary")
    lines.append("=" * 60)

    for thr in ACCELERATION_ALERT_LEVELS:
        acc_alerts = np.sum(acc > thr['value'])
        lines.append(f"  {thr['label']}: {acc_alerts} samples")

    lines.append("\nGyroscope:")
    for thr in GYRO_ALERT_LEVELS:
        gyro_alerts = np.sum(gyro > thr['value'])
        lines.append(f"  {thr['label']}: {gyro_alerts} samples")

    out_path = os.path.join(SUMMARY_DIR,
                            file_basename.replace('.csv', '_summary.txt')) 
    with open(out_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')


# --- MAIN ---

def main(): 
    test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data', 'raw')
    csv_files = glob.glob(os.path.join(test_data_dir, '*.csv'))

    if not csv_files:
        return 
    
    for csv in csv_files: 
        basename = os.path.basename(csv)
        df = calculate_resultant(csv)
        print_alert_summary(df, basename)
        plot_with_alerts_thresholds(df, basename)

if __name__ == "__main__":
    main()