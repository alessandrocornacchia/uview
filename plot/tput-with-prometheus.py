import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# LOCAL_PATH="/home/cornaca/uview/results/IPU-22042025/"

LOCAL_PATH = os.getenv("LOCAL_PATH", "./") 
FIGURES_DIR = LOCAL_PATH + "/figures"


ylabel = 'Tput\n[scrape/s]'
figsize=(2, 1.5)
subplots = True

# Load the CSV data
metrics_df = pd.read_csv(LOCAL_PATH + '/prometheus_scrape_vs_metrics.csv')
pods_df = pd.read_csv(LOCAL_PATH + '/prometheus_scrape_vs_pods.csv')

# sort by num_metrics and num_pods
metrics_df.sort_values(by='num_metrics', inplace=True)
pods_df.sort_values(by='num_pods', inplace=True)

# change algorithm FD into FDSketch
metrics_df['algorithm'] = metrics_df['algorithm'].replace({'FD': 'FDSketch'})
pods_df['algorithm'] = pods_df['algorithm'].replace({'FD': 'FDSketch'})

# Filter to only include FDSketch algorithm
metrics_df = metrics_df[metrics_df['algorithm'] == 'FDSketch']
pods_df = pods_df[pods_df['algorithm'] == 'FDSketch']

# Set publication style with light axis frame
plt.rcParams['axes.facecolor'] = 'white'
plt.rcParams['axes.edgecolor'] = 'black'
plt.rcParams['axes.linewidth'] = 0.5
plt.rcParams['grid.color'] = 'gray'
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['grid.linewidth'] = 0.5
plt.rcParams['grid.alpha'] = 0.7
plt.rcParams['font.size'] = 8
plt.rcParams['legend.fontsize'] = 8
plt.rcParams['xtick.labelsize'] = 8
plt.rcParams['ytick.labelsize'] = 8

# FIGURE 1: Metrics plot

if not subplots:
    plt.figure(figsize=figsize, dpi=300)
else:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(3.7, 1.5))

# ax1 = plt.gca()

# Generate color gradient (different transparency levels of green)
num_metrics = len(metrics_df['num_metrics'].unique())
greens = plt.cm.Greens(np.linspace(0.4, 0.9, num_metrics))

# Plot metrics with custom bar style
x_pos = np.arange(num_metrics)
values = []

for i, (metric_val, group) in enumerate(metrics_df.groupby('num_metrics')):
    value = group['requests_per_sec'].values[0]
    values.append(value)
    bar = ax1.bar(i, value, color=greens[i], width=0.6)
    
    # Add value label on top of bar
    ax1.text(i, value + 0.05*max(values) if values else value, 
             f"{value:.1f}", ha='center', va='bottom', fontsize=8)

# Configure the metrics plot
ax1.set_xlabel('Number of Metrics', fontsize=9)
ax1.set_ylabel(ylabel, fontsize=9)
ax1.set_xticks(x_pos)
ax1.set_xticklabels(sorted(metrics_df['num_metrics'].unique()))
ax1.grid(axis='y', linestyle='--', alpha=0.7)
ax1.spines["left"].set_visible(False)
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)
ax1.spines["bottom"].set_visible(False)

# Set y-axis to start from 0
ax1.set_ylim(bottom=0)

# # Save the metrics figure
if not subplots:
    plt.tight_layout()
    plt.savefig(f'{FIGURES_DIR}/prom_tput_metrics.png', dpi=300, bbox_inches='tight', pad_inches=0.)
    plt.savefig(f'{FIGURES_DIR}/prom_tput_metrics.pdf', dpi=300, bbox_inches='tight', pad_inches=0.)
    plt.show()

# FIGURE 2: Pods plot 
    plt.figure(figsize=figsize, dpi=300)
    ax2 = plt.gca()

# Generate color gradient (different transparency levels of green)
num_pods = len(pods_df['num_pods'].unique())
greens = plt.cm.Greens(np.linspace(0.4, 0.9, num_pods))

# Plot pods with custom bar style
x_pos = np.arange(num_pods)
values = []

for i, (pod_val, group) in enumerate(pods_df.groupby('num_pods')):
    value = group['requests_per_sec'].values[0]
    values.append(value)
    bar = ax2.bar(i, value, color=greens[i], width=0.6)
    
    # Add value label on top of bar
    ax2.text(i, value + 0.05*max(values) if values else value, 
             f"{value:.1f}", ha='center', va='bottom', fontsize=8)

# Configure the pods plot
ax2.set_xlabel('Number of Pods', fontsize=9)
# ax2.set_ylabel(ylabel, fontsize=9)
ax2.set_xticks(x_pos)
ax2.set_xticklabels(sorted(pods_df['num_pods'].unique()))
ax2.grid(axis='y', linestyle='--', alpha=0.7)
ax2.spines["left"].set_visible(False)
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)
ax2.spines["bottom"].set_visible(False)

# Set y-axis to start from 0
ax2.set_ylim(bottom=0)

# Save the pods figure
if not subplots:
    name = 'prom_tput_pods'
else:
    name = 'prom_tput_both'
plt.tight_layout()

if os.path.exists(FIGURES_DIR) is False:
    os.makedirs(FIGURES_DIR)

plt.savefig(f'{FIGURES_DIR}/{name}.png', dpi=300, bbox_inches='tight', pad_inches=0.)
plt.savefig(f'{FIGURES_DIR}/{name}.pdf', dpi=300, bbox_inches='tight', pad_inches=0.)
plt.show()

print(f"Figures {name}.png saved in {FIGURES_DIR} directory")