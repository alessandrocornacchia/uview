import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# LOCAL_PATH="/home/cornaca/uview/results/IPU-22042025/"

LOCAL_PATH = os.getenv("LOCAL_PATH", "./") 
FIGURES_DIR = LOCAL_PATH + "/figures"

# ----------- plot utilities -----------------

def process_and_plot_dataset(df, plot_type, output_dir, algorithms=None, ax=None):
    """Process a dataset and create both time series and bar plots"""
    # Get all scrape rate columns NOTE the _ at the end !!!
    scrape_rate_cols = [col for col in df.columns if col.startswith('scrape_rate_')]
    
    # Determine the count column based on plot type
    if plot_type == 'metrics':
        x_variable = 'num_metrics'
    else:
        x_variable = 'num_pods'
    
    # Get unique algorithms and counts
    if algorithms is None:
        algorithms = sorted(df['algorithm'].unique())
    else:
        df["algorithm"] = df["algorithm"].map(algorithms)
        algorithms = list(algorithms.values())
    print("Detected algorithms:", algorithms)
    counts = sorted(df[x_variable].unique())

    
    # Create bar plots
    create_barplots(df, scrape_rate_cols, algorithms, x_variable, plot_type, output_dir, ax=ax)



def create_barplots(df, scrape_rate_cols, algorithms, x_variable, plot_type, output_dir, transitory_seconds=60, ax=None):
    """Create bar plots showing average scrape rates with confidence intervals"""
    # Calculate aggregated data for bar plots
    aggregated_data = []
    all_x = sorted(df[x_variable].unique())

    transitory = int(transitory_seconds / df['delta_t_seconds'].iloc[0])  # Convert to number of samples
    
    colors = ['#1B9E77', '#D95F02', '#7570B3']
    colors = ['#3C5488', '#E64B35', '#4DBBD5']
    # colors = ['#AAD8D3', '#00ADB5', '#393E46']  # Charcoal, Teal, Pale cyan
    hatches = ['+', '', '']  # Different hatch patterns for each algorithm

    for i,algorithm in enumerate(algorithms):
        
        for count in all_x:
            # Filter data for this algorithm and count
            filtered_df = df[(df['algorithm'] == algorithm) & (df[x_variable] == count)]
            
            if len(filtered_df) == 0:
                continue
                
            # Collect all rates across all LMAPs and time points
            all_rates = []
            for _, row in filtered_df.iterrows():
                # filtered df here contains only all LMAPs for this number of x value (e..g, num metrics)
                # and this algorithm.
                
                # append all time samples
                # TODO discard the first 10 samples (100 seconds) transient
                rates = [row[col] for col in scrape_rate_cols if pd.notna(row[col]) and int(col.split("_")[-1]) >= transitory]
                # append to all LMAPs
                all_rates.extend(rates)
            
            # Calculate average and standard error
            if all_rates:
                avg_rate = np.mean(all_rates)
                std_error = np.std(all_rates) / np.sqrt(len(all_rates))
                
                aggregated_data.append({
                    'algorithm': algorithm,
                    x_variable: count,
                    'avg_scrape_rate': avg_rate,
                    'std_error': std_error
                })
    
    # Convert to DataFrame
    agg_df = pd.DataFrame(aggregated_data)
    
    # Check if we have data
    if len(agg_df) == 0:
        print(f"No data available for {plot_type} bar plot")
        return
    
    # Create bar plot
    # plot parameter 
    ylabel = 'Throughput\n[scrapes/s]'
    
     
    # Use provided axis or create a new figure
    if ax is None:
        plt.figure(figsize=(3,1.5), dpi=300)
        ax = plt.gca()
    else:
        ax = ax
        
    
    # Define bar width and positions
    bar_width = 0.2

    x = np.arange(len(all_x))
    
    # Plot bars for each algorithm
    for i, algorithm in enumerate(algorithms):
        data = agg_df[agg_df['algorithm'] == algorithm]
        
        # Skip if no data for this algorithm
        if len(data) == 0:
            continue
        
        # Prepare data for plotting
        y_values = []
        y_errors = []
        x_positions = []
        
        for j, count in enumerate(all_x):
            count_data = data[data[x_variable] == count]
            if len(count_data) > 0:
                y_values.append(count_data['avg_scrape_rate'].values[0])
                y_errors.append(count_data['std_error'].values[0])
                x_positions.append(j)
        
        # Calculate positions with offset based on algorithm index
        offset = (i - (len(algorithms) - 1) / 2) * bar_width
        positions = np.array(x_positions) + offset
        
        bars = ax.bar(positions, 
               y_values, 
               bar_width, 
            #    yerr=y_errors,
               label=algorithm, 
               alpha=0.7,
               color=colors[i],
               hatch=hatches[i],
               lw=0.5,)
    
    # Set plot labels and title
    ax.set_xlabel(f'Number of {x_variable.split("_")[1]}')
    if YLABEL == '':
        # remove ylabel
        ax.set_ylabel(YLABEL)
    else:
        ax.set_ylabel(ylabel)
    # ax.set_title(f'Local processing only - no Prometheus')
    ax.set_xticks(x)
    ax.set_xticklabels(all_x)
    ax.grid(True, linestyle='--', alpha=0.7, axis='y')
    if LEGEND:
        # Add legend on top of the plot outside tge axis
        ax.legend()
    
    # Remove spines for cleaner look
    ax.spines["left"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    
    # plt.tight_layout()
    
    # # Save the plot
    # save_path = f"{output_dir}/avg_scrape_rate_{plot_type}"
    # plt.savefig(f"{save_path}.png", dpi=300, bbox_inches='tight', pad_inches=0.)
    # plt.savefig(f"{save_path}.pdf", dpi=300, bbox_inches='tight', pad_inches=0.)
    # plt.show()
    # plt.close()
    return ax

# ----------- plot utilities -----------------






"""Main function to plot RDMA benchmark results"""
try:
    # Load CSV files
    metrics_df = pd.read_csv(f"{LOCAL_PATH}/read_loop_vs_metrics.csv")
    pods_df = pd.read_csv(f"{LOCAL_PATH}/read_loop_vs_pods.csv")
except FileNotFoundError as e:
    print(f"Error: {e}. Please ensure the CSV files are in the specified LOCAL_PATH: {LOCAL_PATH}")
    exit(1)

import os
# Create output directory
output_dir = f'{FIGURES_DIR}'
os.makedirs(output_dir, exist_ok=True)

plot_algos = {
    "TH": "Threshold",
    "FD": "FDSketch",
    "VAE": "AutoEncoder"
}

import matplotlib as mpl
mpl.rcParams['hatch.linewidth'] = 0.1


# Create a single figure with two subplots for metrics and pods data
fig, (ax_metrics, ax_pods) = plt.subplots(1, 2, figsize=(6, 1.5), dpi=300)

LEGEND=False

# YLABEL='Tput\n[scrapes/s]'
YLABEL='Tput\n[scrape/s]'
# Process metrics data
process_and_plot_dataset(metrics_df, "metrics", output_dir, algorithms=plot_algos, ax=ax_metrics)

LEGEND=True
YLABEL=''
# Process pods data
process_and_plot_dataset(pods_df, "pods", output_dir, algorithms=plot_algos, ax=ax_pods)

plt.tight_layout()
    
# Save the plot
save_path = f"{output_dir}/avg_scrape_rate"
plt.savefig(f"{save_path}.png", dpi=300, bbox_inches='tight', pad_inches=0.)
plt.savefig(f"{save_path}.pdf", dpi=300, bbox_inches='tight', pad_inches=0.)
plt.show()
plt.close()

print(f"All plots saved to {output_dir}/")