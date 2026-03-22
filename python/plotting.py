FILE_DIRECTORY = r'C:\Users\teres\Projects\test_imu\python\test_data\raw\testing_2'

import pandas as pd 
import os 
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec

def get_all_csv_files(directory):
    csv_files = []
    for filename in os.listdir(directory):
        if filename.endswith('.csv'):
            csv_files.append(os.path.join(directory, filename))
    return csv_files

# want to plot the following: 
# - acceleration resultant (overlay on top of raw x,y,z values)
# - gyroscope resultant (overlay on top of raw x,y,z values)
# - jerk resultant 
# - for time segments where event != 0, highlight the contiguous segment in time until event !=0 
# - for time segments where state != 0, highlight the contiguous segment in time until state !=0
# - colour code the event and state segments differently (e.g., yellow if = 1, blue if = 2 , and so on)

# Sample data: 
# ts,ax,ay,az,gx,gy,gz,r_acc,r_gyro,event,state,jerk,freefall,horizontal,motionless
# 353402,0.364,0.04,1.064,-6.3,-15.0,3.0,1.125,16.6,0,0,0.3,0,0,1
# timestamp, acceleration in x,y,z, gyroscope in x,y,z, resultant acceleration, resultant gyroscope, event, state, jerk, freefall, horizontal, motionless
# all accelerations are in g, all gyroscope values are in degrees/s
# jerk is in g/s

def highlight_segments(ax, df, column, colors):
    """
    Highlight contiguous segments where column != 0 with different colors.
    
    Args:
        ax: matplotlib axis object
        df: DataFrame with data
        column: column name to check for non-zero segments ('event' or 'state')
        colors: dict mapping values to colors (e.g., {1: 'yellow', 2: 'blue'})
    """
    mask = df[column] != 0
    if not mask.any():
        return
    
    # Find contiguous segments
    segments = []
    start_idx = None
    current_value = None
    
    for idx in range(len(df)):
        if mask.iloc[idx]:
            value = df[column].iloc[idx]
            if start_idx is None:
                start_idx = idx
                current_value = value
            elif value != current_value:
                # Value changed, save previous segment
                segments.append((start_idx, idx - 1, current_value))
                start_idx = idx
                current_value = value
        else:
            if start_idx is not None:
                # End of segment
                segments.append((start_idx, idx - 1, current_value))
                start_idx = None
                current_value = None
    
    # Handle case where segment extends to end
    if start_idx is not None:
        segments.append((start_idx, len(df) - 1, current_value))
    
    # Draw highlighted regions
    for start, end, value in segments:
        color = colors.get(value, 'gray')
        ax.axvspan(df['ts'].iloc[start], df['ts'].iloc[end], 
                   alpha=0.3, color=color, label=f'{column}={value}')


def plot_all_data(df: pd.DataFrame, filename: str):
    """Create a 2-column grid: left has acceleration, gyroscope, jerk; right has state and event segments."""
    fig = plt.figure(figsize=(18, 12))
    gs = GridSpec(3, 2, figure=fig, hspace=0.3, wspace=0.3)
    
    event_colors = {1: 'yellow', 2: 'orange', 3: 'red'}
    state_colors = {1: 'lightblue', 2: 'blue', 3: 'darkblue'}
    
    # Left Column - Plot 1: Acceleration
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(df['ts'], df['ax'], label='ax', alpha=0.7, linewidth=1)
    ax1.plot(df['ts'], df['ay'], label='ay', alpha=0.7, linewidth=1)
    ax1.plot(df['ts'], df['az'], label='az', alpha=0.7, linewidth=1)
    ax1.plot(df['ts'], df['r_acc'], label='resultant', color='black', linewidth=2)
    # ax1.set_xlabel('Timestamp (ms)')
    ax1.set_ylabel('Acceleration (g)')
    ax1.set_title('Acceleration')
    ax1.legend(loc='upper right', fontsize=9)
    ax1.grid(True, alpha=0.3)
    
    # Left Column - Plot 2: Gyroscope
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.plot(df['ts'], df['gx'], label='gx', alpha=0.7, linewidth=1)
    ax2.plot(df['ts'], df['gy'], label='gy', alpha=0.7, linewidth=1)
    ax2.plot(df['ts'], df['gz'], label='gz', alpha=0.7, linewidth=1)
    ax2.plot(df['ts'], df['r_gyro'], label='resultant', color='black', linewidth=2)
    # ax2.set_xlabel('Timestamp (ms)')
    ax2.set_ylabel('Gyroscope (deg/s)')
    ax2.set_title('Gyroscope')
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3)
    
    # Left Column - Plot 3: Jerk
    ax3 = fig.add_subplot(gs[2, 0])
    ax3.plot(df['ts'], df['jerk'], label='jerk', color='purple', linewidth=1.5)
    ax3.set_xlabel('Timestamp (ms)')
    ax3.set_ylabel('Jerk (g/s)')
    ax3.set_title('Jerk Resultant')
    ax3.legend(loc='upper right', fontsize=9)
    ax3.grid(True, alpha=0.3)
    
    # Right Column - Plot 4: State Segments (spans row 0-1)
    ax4 = fig.add_subplot(gs[0:2, 1])
    # Create secondary y-axis for jerk
    ax4_twin = ax4.twinx()
    ax4.plot(df['ts'], df['r_acc'], label='resultant acc', color='blue', linewidth=1.5)
    ax4_twin.plot(df['ts'], df['jerk'], label='resultant jerk', color='purple', linewidth=1.5)
    highlight_segments(ax4, df, 'state', state_colors)
    # ax4.set_xlabel('Timestamp (ms)')
    ax4.set_ylabel('Resultant Acc (g)', color='blue')
    ax4_twin.set_ylabel('Resultant Jerk (g/s)', color='purple')
    ax4.set_title('State Segments')
    ax4.legend(loc='upper left', fontsize=9)
    ax4_twin.legend(loc='upper right', fontsize=9)
    ax4.grid(True, alpha=0.3)
    ax4.tick_params(axis='y', labelcolor='blue')
    ax4_twin.tick_params(axis='y', labelcolor='purple')
    
    # Right Column - Plot 5: Event Segments (row 2)
    ax5 = fig.add_subplot(gs[2, 1])
    # Create secondary y-axis for jerk
    ax5_twin = ax5.twinx()
    ax5.plot(df['ts'], df['r_acc'], label='resultant acc', color='blue', linewidth=1.5)
    ax5_twin.plot(df['ts'], df['jerk'], label='resultant jerk', color='purple', linewidth=1.5)
    highlight_segments(ax5, df, 'event', event_colors)
    ax5.set_xlabel('Timestamp (ms)')
    ax5.set_ylabel('Resultant Acc (g)', color='blue')
    ax5_twin.set_ylabel('Resultant Jerk (g/s)', color='purple')
    ax5.set_title('Event Segments')
    ax5.legend(loc='upper left', fontsize=9)
    ax5_twin.legend(loc='upper right', fontsize=9)
    ax5.grid(True, alpha=0.3)
    ax5.tick_params(axis='y', labelcolor='blue')
    ax5_twin.tick_params(axis='y', labelcolor='purple')
    
    # Overall title
    fig.suptitle(f'{os.path.basename(filename)}', fontsize=14)
    
    return fig


if __name__ == "__main__":
    csv_files = get_all_csv_files(FILE_DIRECTORY)
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        
        # Create 1x5 grid plot for each file
        fig = plot_all_data(df, csv_file)
        
        # Save the figure BEFORE closing it
        output_path = os.path.join(FILE_DIRECTORY, f'{os.path.basename(csv_file).replace(".csv", ".png")}')
        plt.savefig(output_path, dpi=300)
        
        plt.show(block=False)  
        plt.pause(2)           
        plt.close()

