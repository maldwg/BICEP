import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, HourLocator, MinuteLocator, AutoDateLocator

# Consistent colors for Slips and Suricata
color_slips = 'red'
color_suricata = 'blue'

def plot_cpu_usage(csv_file, output_file, slips_name, suricata_name):
    # Load CSV into DataFrame
    df = pd.read_csv(csv_file, parse_dates=['Time'])

    # Plot CPU usage
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(df['Time'], df[slips_name], label='Slips CPU usage', color=color_slips)
    ax.plot(df['Time'], df[suricata_name], label='Suricata CPU usage', color=color_suricata)

    # Set dynamic ticks for the x-axis based on the time range
    time_range = df['Time'].max() - df['Time'].min()

    if time_range.total_seconds() < 3600:  # Less than 1 hour
        locator = MinuteLocator(interval=5)  # Show ticks every 5 minutes
        formatter = DateFormatter('%H:%M')
    elif time_range.total_seconds() < 10800:  # Less than 3 hours
        locator = MinuteLocator(interval=10)  # Show ticks every 10 minutes
        formatter = DateFormatter('%H:%M')
    elif time_range.total_seconds() < 86400:  # Less than 24 hours
        locator = HourLocator(interval=1)  # Show ticks every 1 hour
        formatter = DateFormatter('%H:%M')
    else:  # More than 24 hours
        locator = AutoDateLocator()  # Automatically decide the ticks
        formatter = DateFormatter('%Y-%m-%d')

    # Set the locator and formatter for the x-axis
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    # Add labels and title
    ax.set_xlabel('Elapsed Time')
    ax.set_ylabel('CPU usage (%)')
    ax.set_title('CPU usage over time')
    plt.xticks(rotation=45)
    plt.legend()

    # Save the plot as an SVG file
    plt.tight_layout()
    plt.savefig(output_file, format='svg')
    plt.close()

def plot_ram_usage(csv_file, output_file, slips_name, suricata_name):
    # Load CSV into DataFrame
    df = pd.read_csv(csv_file, parse_dates=['Time'])

    # Plot RAM usage
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(df['Time'], df[slips_name], label='Slips RAM usage', color=color_slips)
    ax.plot(df['Time'], df[suricata_name], label='Suricata RAM usage', color=color_suricata)

    # Set dynamic ticks for the x-axis based on the time range
    time_range = df['Time'].max() - df['Time'].min()

    if time_range.total_seconds() < 3600:  # Less than 1 hour
        locator = MinuteLocator(interval=5)  # Show ticks every 5 minutes
        formatter = DateFormatter('%H:%M')
    elif time_range.total_seconds() < 10800:  # Less than 3 hours
        locator = MinuteLocator(interval=10)  # Show ticks every 10 minutes
        formatter = DateFormatter('%H:%M')
    elif time_range.total_seconds() < 86400:  # Less than 24 hours
        locator = HourLocator(interval=1)  # Show ticks every 1 hour
        formatter = DateFormatter('%H:%M')
    else:  # More than 24 hours
        locator = AutoDateLocator()  # Automatically decide the ticks
        formatter = DateFormatter('%Y-%m-%d')

    # Set the locator and formatter for the x-axis
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    # Add labels and title
    ax.set_xlabel('Elapsed Time')
    ax.set_ylabel('RAM usage (MB)')
    ax.set_title('RAM usage over time')
    plt.xticks(rotation=45)
    plt.legend()

    # Save the plot as an SVG file
    plt.tight_layout()
    plt.savefig(output_file, format='svg')
    plt.close()

cpu_csv_file = '/mnt/d/master/cpu-tmnids.csv'
ram_csv_file = '/mnt/d/master/memory-tmnids.csv'

plot_cpu_usage(cpu_csv_file, '/mnt/c/Users/Max/Desktop/cpu-tmnids.svg', 'Slips-41015', 'Suricata-32921')
plot_ram_usage(ram_csv_file, '/mnt/c/Users/Max/Desktop/memory-tmnids.svg', 'Slips-41015', 'Suricata-32921')

# cpu_csv_file = '/mnt/d/master/ensemble-cpu.csv'
# ram_csv_file = '/mnt/d/master/ensemble-memory.csv'

# plot_cpu_usage(cpu_csv_file, '/mnt/c/Users/Max/Desktop/cpu-ensemble.svg', 'Slips-52377', 'Suricata-36335')
# plot_ram_usage(ram_csv_file, '/mnt/c/Users/Max/Desktop/memory-ensemble.svg', 'Slips-52377', 'Suricata-36335')
