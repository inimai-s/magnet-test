import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math

df = pd.read_csv('sum_curve_compare.csv')
df['corr2'] = df['corr'].str.strip('[]').astype(float)
df['deriv_ratio'] = df['sum_deriv'] / df['comb_deriv']
df['avg_ratio'] = df['sum_avg'] / df['comb_avg']
df['std_ratio'] = df['sum_std'] / df['comb_std']
df['ptp_ratio'] = df['sum_pp'] / df['comb_pp']
df['sum_fft2'] = df['sum_fft'].str.strip('[+0.j]').astype(float)
df['comb_fft2'] = df['comb_fft'].str.strip('[+0.j]').astype(float)
df['irr_ratio'] = df['comb_irr'] / df['sum_irr']


# output histogram for predicted axial curve
def output_histo(metric):
    df_ms = df[df['mode_shifter'] == 'y']
    df_nonms = df[df['mode_shifter'] == 'n']

    plt.figure(figsize=(10, 6))
    plt.hist(df_nonms[metric], bins=20,range=(int(min(df_nonms[metric])), math.ceil(max(df_nonms[metric])) + 1), color='blue', edgecolor='black',label='Non-mode shifters')
    plt.hist(df_ms[metric], bins=20,range=(int(min(df_ms[metric])), math.ceil(max(df_ms[metric])) + 1), color = 'orange', edgecolor='black',label='Mode shifters')
    plt.xlabel(f'Sum Curve {metric} (Gauss)'.title())
    plt.ylabel('Count of Satellites')
    plt.title(f'Histogram of Sum Curve {metric}'.title())
    plt.legend()
    plt.show()

output_histo('sum_min')
