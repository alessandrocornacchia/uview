#%%
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns

# Load the data
df_sock = pd.read_csv('./sockshop.csv')
df_dsb = pd.read_csv('./dsb_hotel.csv')

df_sock['workload'] = 'sockshop'
df_dsb['workload'] = 'dsb_hotel'

df = pd.concat([df_sock, df_dsb])
df['workload'] = df['workload'].map({'sockshop': 'Sockshop', 'dsb_hotel': 'DSB Hotel'})

#%%
res = df[df['algorithm'] == '$\mu$View']

coverage_color =  'white'#b8860b'
overhead_color = '#008080'
fig, ax = plt.subplots(dpi=300, figsize=(3, 1.5))

# add horizontal line at 25% (backward the bars)
ax.axhline(y=20, color='black', linewidth=1.5, linestyle=':')
ax.axhline(y=5, color='black', linewidth=1.5, linestyle=':')
ax.text(0.47, 22, 'head 20%', color='black', fontsize=6, ha='center', va='bottom')
ax.text(0.47, 7, 'head 5%', color='black', fontsize=6, ha='center', va='bottom')

res[['coverage_norm', 'overhead_norm', 'workload']].set_index('workload').plot.bar(
    ax=ax, 
    color=[coverage_color, overhead_color], 
    width=0.5, 
    edgecolor='black', 
    linewidth=0.5, zorder=2)

mpl.rcParams['hatch.linewidth'] = 0.1
# add hatches every two bars
for i, bar in enumerate(ax.patches):
    print(i)
    if i < 2:
        bar.set_hatch('//')
        

# Rotating X-axis labels
plt.xticks(rotation = 0)

ax.set_ylim(0, 105)

# # remove legend and add secondary y-axis
ax2 = ax.twinx()

# set ax2 y-axis scale to align with overhead_norm plotted before. Do not replot bars.
ax2.set_ylim(ax.get_ylim())
ax2.set_ylabel('Overhead [%]', fontsize=8)

ax.legend().remove()

# set color of secondary axis ticks and labels
ax2.yaxis.label.set_color('#008080')
#ax2.tick_params(axis='y', colors='#008080')
# set color only on numbers not on ticks
for t in ax2.get_yticklabels():
    t.set_color('#008080')

# remove x-axis labels
ax.set_xlabel('')
ax.set_ylabel('Coverage [%]', fontsize=8)

# Draw the grid behind the bars
ax.set_axisbelow(True)
ax.grid(axis='y', ls=':', color='black', alpha=0.5)

# reduce axis font size 
ax.tick_params(axis='both', which='major', labelsize=8)
ax2.tick_params(axis='both', which='major', labelsize=8)

# set tick style internal to the plot
ax.tick_params(axis='y', direction='in')
ax2.tick_params(axis='y', direction='in')

# reduce thickness of the axis
for axis in ['top','bottom','left','right']:
    ax.spines[axis].set_linewidth(0.5)
    ax2.spines[axis].set_linewidth(0.5)

# reduce thickness of the ticks
ax.xaxis.set_tick_params(width=0.7)
ax.yaxis.set_tick_params(width=0.7)
ax2.yaxis.set_tick_params(width=0.7)
ax2.xaxis.set_tick_params(width=0.7)

# set bold font on x-axis
for t in ax.get_xticklabels():
    t.set_fontweight('bold')

# draw a line at y=100 with text tail sampling
ax.axhline(y=100, color='orchid', linewidth=1, linestyle='-')
ax.text(0.4, 90, 'tail sampling', color='orchid', fontsize=6, ha='center', va='bottom')
plt.savefig('nsdi-uview-vs-workload.pdf', bbox_inches='tight', pad_inches=0)

plt.show()


#%%
# plot barplot where color is associated to workload column, x-axis has no labels and no ticks
# and y-axis corresponds to column coverage_norm 