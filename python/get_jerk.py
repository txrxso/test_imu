import pandas as pd 
import numpy as np
import os 
import matplotlib.pyplot as plt

# CSV format: ts,ax,ay,az,gx,gy,gz
FILEPATH = r'C:\Users\teres\Projects\test_imu\python\test_data\raw\tracy_fall_1.csv'

def calculate_jerk(df): 
    """
    Calculate jerk (rate of change of acceleration) from IMU acceleration data.
    Jerk = dA/dt for each axis (x, y, z)
    
    Args:
        df: DataFrame with columns ts, ax, ay, az
    
    Returns:
        DataFrame with columns ts, jerk_x, jerk_y, jerk_z, jerk_resultant
    """
    # Calculate time differences in seconds (ts is in milliseconds)
    dt = df['ts'].diff() / 1000.0  # Convert ms to seconds
    
    # Calculate acceleration differences
    dax = df['ax'].diff()
    day = df['ay'].diff()
    daz = df['az'].diff()
    
    # Calculate jerk for each axis (m/s³)
    jerk_x = dax / dt
    jerk_y = day / dt
    jerk_z = daz / dt
    
    # Calculate resultant jerk magnitude
    jerk_resultant = np.sqrt(jerk_x**2 + jerk_y**2 + jerk_z**2)
    
    # Create result dataframe
    jerk_df = pd.DataFrame({
        'ts': df['ts'],
        'jerk_x': jerk_x,
        'jerk_y': jerk_y,
        'jerk_z': jerk_z,
        'jerk_resultant': jerk_resultant
    })
    
    # Drop first row (NaN due to diff operation)
    jerk_df = jerk_df.dropna()
    
    return jerk_df

def plot_jerk(jerk_df, save_path=None):
    """
    Plot jerk data for all three axes and resultant.
    
    Args:
        jerk_df: DataFrame with jerk data
        save_path: Optional path to save the plot
    """
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))
    fig.suptitle('Jerk Analysis', fontsize=16)
    
    # Plot individual axes
    axes[0].plot(jerk_df['ts'], jerk_df['jerk_x'], label='Jerk X', alpha=0.7)
    axes[0].plot(jerk_df['ts'], jerk_df['jerk_y'], label='Jerk Y', alpha=0.7)
    axes[0].plot(jerk_df['ts'], jerk_df['jerk_z'], label='Jerk Z', alpha=0.7)
    axes[0].set_xlabel('Time (ms)')
    axes[0].set_ylabel('Jerk (m/s³)')
    axes[0].set_title('Jerk Components (X, Y, Z)')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Plot resultant
    axes[1].plot(jerk_df['ts'], jerk_df['jerk_resultant'], label='Resultant Jerk', color='purple', linewidth=1.5)
    axes[1].set_xlabel('Time (ms)')
    axes[1].set_ylabel('Jerk (m/s³)')
    axes[1].set_title('Resultant Jerk Magnitude')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300)
        print(f"Plot saved to: {save_path}")
    else:
        plt.show()
    
    plt.close(fig)

def plot_jerk_with_acceleration(jerk_df, acc_df, save_path=None):
    """
    Plot jerk and acceleration data side by side for comparison.
    
    Args:
        jerk_df: DataFrame with jerk data
        acc_df: DataFrame with acceleration data (ax, ay, az)
        save_path: Optional path to save the plot
    """
    # Calculate resultant acceleration
    acc_resultant = np.sqrt(acc_df['ax']**2 + acc_df['ay']**2 + acc_df['az']**2)
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle('Acceleration and Jerk Analysis', fontsize=16)
    
    # Plot acceleration
    axes[0].plot(acc_df['ts'], acc_df['ax'], label='Acc X', alpha=0.6)
    axes[0].plot(acc_df['ts'], acc_df['ay'], label='Acc Y', alpha=0.6)
    axes[0].plot(acc_df['ts'], acc_df['az'], label='Acc Z', alpha=0.6)
    axes[0].plot(acc_df['ts'], acc_resultant, label='Resultant', color='black', linewidth=2, alpha=0.8)
    axes[0].set_xlabel('Time (ms)')
    axes[0].set_ylabel('Acceleration (m/s²)')
    axes[0].set_title('Acceleration Data')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Plot jerk
    axes[1].plot(jerk_df['ts'], jerk_df['jerk_x'], label='Jerk X', alpha=0.6)
    axes[1].plot(jerk_df['ts'], jerk_df['jerk_y'], label='Jerk Y', alpha=0.6)
    axes[1].plot(jerk_df['ts'], jerk_df['jerk_z'], label='Jerk Z', alpha=0.6)
    axes[1].plot(jerk_df['ts'], jerk_df['jerk_resultant'], label='Resultant', color='purple', linewidth=2, alpha=0.8)
    axes[1].set_xlabel('Time (ms)')
    axes[1].set_ylabel('Jerk (m/s³)')
    axes[1].set_title('Jerk Data')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300)
        print(f"Plot saved to: {save_path}")
    else:
        plt.show()
    
    plt.close(fig)

def print_jerk_stats(jerk_df):
    """Print statistical summary of jerk data."""
    print("\n=== Jerk Statistics ===")
    print(f"Max Resultant Jerk: {jerk_df['jerk_resultant'].max():.2f} m/s³")
    print(f"Mean Resultant Jerk: {jerk_df['jerk_resultant'].mean():.2f} m/s³")
    print(f"Std Dev Resultant Jerk: {jerk_df['jerk_resultant'].std():.2f} m/s³")
    print(f"\nMax Jerk X: {jerk_df['jerk_x'].abs().max():.2f} m/s³")
    print(f"Max Jerk Y: {jerk_df['jerk_y'].abs().max():.2f} m/s³")
    print(f"Max Jerk Z: {jerk_df['jerk_z'].abs().max():.2f} m/s³")


if __name__ == "__main__":
    # Example: Set FILEPATH to a test file
    if not FILEPATH:
        # Use the currently open file as an example
        FILEPATH = os.path.join(os.path.dirname(__file__), 'test_data', 'raw', 'tracy_fall_5.csv')
        print(f"Using example file: {FILEPATH}")
    
    # Load the data 
    df = pd.read_csv(FILEPATH)
    print(f"Loaded {len(df)} data points from {os.path.basename(FILEPATH)}")
    
    # Calculate jerk 
    jerk_df = calculate_jerk(df)
    
    # Print statistics
    print_jerk_stats(jerk_df)
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(__file__), 'test_data', 'jerk_output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output filename
    base_filename = os.path.splitext(os.path.basename(FILEPATH))[0]
    jerk_csv_path = os.path.join(output_dir, f"{base_filename}_jerk.csv")
    jerk_plot_path = os.path.join(output_dir, f"{base_filename}_jerk_plot.png")
    combined_plot_path = os.path.join(output_dir, f"{base_filename}_acc_jerk_plot.png")
    
    # Save the jerk data 
    jerk_df.to_csv(jerk_csv_path, index=False)
    print(f"Jerk data saved to: {jerk_csv_path}")
    
    # Generate plots
    plot_jerk(jerk_df, save_path=jerk_plot_path)
    plot_jerk_with_acceleration(jerk_df, df, save_path=combined_plot_path)
    