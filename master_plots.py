import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
from matplotlib.lines import Line2D
import collections
import addcopyfighandler

df = pd.read_csv('test_CORRECT.csv')

ms = pd.read_csv('classified_CORRECT.csv')
ms = ms[ms['mode_shifters'] == 'y']
mode_shifters = list(ms['sxid'])

inner = df[df['magnet_type'] == 'inner']
outer = df[df['magnet_type'] == 'outer']
combined = df[df['magnet_type'] == 'combined']

inner['pp'] = inner['Maximum Magnetic Flux Density'] - inner['Minimum Magnetic Flux Density']
outer['pp'] = outer['Maximum Magnetic Flux Density'] - outer['Minimum Magnetic Flux Density']
combined['pp'] = combined['Maximum Magnetic Flux Density'] - combined['Minimum Magnetic Flux Density']

deg_list = range(0,361,12)

# generate plots of superimposed traces
def superimposed_traces(df):
    plt.figure(figsize=(10, 6))
    non_ms = 0
    msc = 0
    for i in range(0,len(df['sxid'])):
        pt_list = []
        for col in df.columns:
            if 'degrees' in col:
                pt_list.append(df[col].iloc[i])

        if df['sxid'].iloc[i] in mode_shifters:# and msc<20:
            plt.plot(deg_list, pt_list,color='orange')
            msc+=1
        # elif non_ms < 100:
        else:
            plt.plot(deg_list, pt_list,color='blue')
            non_ms+=1

    plt.xlabel('Azimuth Position (deg)')
    plt.ylabel('Magnetic Flux Density (Gauss)')
    plt.title(f'{df['magnet_type'].iloc[0]} Magnet Measurements Superimposed'.title())
    plt.grid(True)
    line5 = Line2D([0], [0], label='Non-mode shifters', color='blue')
    line6 = Line2D([0], [0], label='Mode shifters', color='orange')
    plt.legend(handles=[line5,line6])
    plt.show()

# generate histograms for inner axial, outer axial, and radial scans based on deviation metrics
def output_histo(df,metric):
    df_ms = df[df['sxid'].isin(mode_shifters)]
    df_nonms = df[~df['sxid'].isin(mode_shifters)]

    plt.figure(figsize=(10, 6))
    plt.hist(df_nonms[metric], bins=20,range=(int(min(df_nonms[metric])), math.ceil(max(df_nonms[metric])) + 1), color='blue', edgecolor='black',label='Non-mode shifters')
    plt.hist(df_ms[metric], bins=20,range=(int(min(df_ms[metric])), math.ceil(max(df_ms[metric])) + 1), color = 'orange', edgecolor='black',label='Mode shifters')
    plt.xlabel(f'{df['magnet_type'].iloc[0]} Magnet {metric} (Gauss)'.title())
    plt.ylabel('Count of Satellites')
    plt.title(f'Histogram of {df['magnet_type'].iloc[0]} Magnet {metric}'.title())
    plt.legend()
    plt.show()

def find_pt_list(df,i):
    pt_list = []
    for col in df.columns:
        if 'degrees' in col:
            pt_list.append(df[col].iloc[i])
    return pt_list

def output_difference_superimposed_combined(df,sat):
    df = df[df['sxid'] == sat]
    deg_list = range(0,361,12)
    if len(df['sxid']) != 3:
        return
    
    for i in range(len(df['sxid'])):
        if df['magnet_type'].iloc[i] == 'inner':
            inner_pt_list = find_pt_list(df,i)
        elif df['magnet_type'].iloc[i] == 'outer':
            outer_pt_list = find_pt_list(df,i)
        else:
            combined_pt_list = find_pt_list(df,i)

    difflist = [inner_pt_list[i] - outer_pt_list[i] for i in range(len(inner_pt_list))]

    fig,ax1 = plt.subplots()
    ax1.set_xlabel('Azimuth Position (deg)')
    ax1.set_ylabel('Magnetic Flux Density (Gauss)', color='blue')
    ax1.set_ylim((280,350))
    ax1.plot(deg_list, combined_pt_list, color='blue', label='Measured Combined Curve')
    ax1.tick_params(axis='y', labelcolor='blue')

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

    ax2.set_ylabel('Magnetic Flux Density (Gauss)', color='orange')
    ax2.set_ylim((20,90))
    ax2.plot(deg_list, difflist, color='orange', label = 'Difference between Inner and Outer Magnet Curves')
    ax2.tick_params(axis='y', labelcolor='orange')

    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    plt.grid(True)
    plt.title(f'Difference Curve vs Combined Curve for Sat {sat}')
    fig.legend()
    plt.show()
    

def assembled_curve(df,sat):
    df = df[df['sxid'] == sat]
    deg_list = range(0,361,12)
    if len(df['sxid']) != 3:
        return
    
    for i in range(len(df['sxid'])):
        if df['magnet_type'].iloc[i] == 'inner':
            inner_pt_list = np.array(find_pt_list(df,i))
            inner_min = np.argmin(inner_pt_list)
            inner_pt_list = np.roll(inner_pt_list,-inner_min)
        elif df['magnet_type'].iloc[i] == 'outer':
            outer_pt_list = np.array(find_pt_list(df,i))
            outer_max = np.argmax(outer_pt_list)
            outer_pt_list = np.roll(outer_pt_list,-outer_max)
        else:
            combined_pt_list = find_pt_list(df,i)

    difflist = [inner_pt_list[i] + outer_pt_list[i] for i in range(len(inner_pt_list))]

    fig,ax1 = plt.subplots(figsize=(10,8))
    ax1.set_xlabel('Azimuth Position (deg)')
    ax1.set_ylabel('Magnetic Flux Density (Gauss)', color='blue')
    ax1.set_ylim((280,350))
    ax1.plot(deg_list, combined_pt_list, color='blue', label='Actual Combined Curve')
    ax1.tick_params(axis='y', labelcolor='blue')

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

    ax2.set_ylabel('Magnetic Flux Density (Gauss)', color='orange')
    ax2.set_ylim((1350,1420))
    ax2.plot(deg_list, difflist, color='orange', label = 'Predicted Axial Sum Curve')
    ax2.tick_params(axis='y', labelcolor='orange')

    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    plt.grid(True)
    plt.title(f'Sum Curve vs Combined Curve for Sat {sat}')
    fig.legend()
    plt.show()
    plt.close()


# generate the predicted axial curve and graph it
def find_closest_sum_curve(df,sat):
    df = df[df['sxid'] == sat]
    deg_list = range(0,361,12)
    if len(df['sxid']) != 3:
        return
    
    for i in range(len(df['sxid'])):
        if df['magnet_type'].iloc[i] == 'inner':
            inner_pt_list = np.array(find_pt_list(df,i))
            inner_min = np.argmin(inner_pt_list)
            inner_pt_list = np.roll(inner_pt_list,-inner_min)
        elif df['magnet_type'].iloc[i] == 'outer':
            outer_pt_list = np.array(find_pt_list(df,i))
            outer_max = np.argmax(outer_pt_list)
            outer_pt_list = np.roll(outer_pt_list,-outer_max)
        else:
            combined_pt_list = np.array(find_pt_list(df,i))

    difflist = np.array([inner_pt_list[i] + outer_pt_list[i] for i in range(len(inner_pt_list))])

    diff = difflist - combined_pt_list
    squared_residuals = diff ** 2
    min_diff = np.sum(squared_residuals)
    min_list = difflist

    for i in range(len(deg_list)-1):
        difflist = np.roll(difflist,1)
        diff = difflist - combined_pt_list
        squared_residuals = diff ** 2
        if np.sum(squared_residuals) < min_diff:
            min_diff = np.sum(squared_residuals)
            min_list = difflist


    fig,ax1 = plt.subplots(figsize=(10,8))
    ax1.set_xlabel('Azimuth Position (deg)')
    ax1.set_ylabel('Magnetic Flux Density (Gauss)', color='blue')
    ax1.set_ylim((280,350))
    ax1.plot(deg_list, combined_pt_list, color='blue', label='Actual Combined Curve')
    ax1.text(0.6,0.05,f'Sum of Squared Distance between Curves: {np.format_float_scientific(min_diff,precision=6)}', transform=plt.gca().transAxes)
    ax1.tick_params(axis='y', labelcolor='blue')

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

    ax2.set_ylabel('Magnetic Flux Density (Gauss)', color='orange')
    if np.mean(min_list) < 1400:
        ax2.set_ylim((1350,1420))
    else:
        ax2.set_ylim((1390,1460))
    ax2.plot(deg_list, min_list, color='orange', label = 'Predicted Axial Sum Curve')
    ax2.tick_params(axis='y', labelcolor='orange')

    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    plt.grid(True)
    plt.title(f'Sum Curve vs Combined Curve for Sat {sat}')
    fig.legend()
    if sat in mode_shifters:
        plt.savefig(f'sum_curves/mode_shifters/sat{sat}')
    else:
        plt.savefig(f'sum_curves/non_mode_shifters/sat{sat}')
    plt.close()

# superimposed_traces(inner)
# superimposed_traces(outer)
# superimposed_traces(combined)

output_histo(inner,'pp')
output_histo(outer,'pp')
output_histo(combined,'pp')

output_histo(inner,'Minimum Magnetic Flux Density')
output_histo(outer, 'Minimum Magnetic Flux Density')
output_histo(combined, 'Minimum Magnetic Flux Density')
