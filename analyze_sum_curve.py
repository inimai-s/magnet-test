import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
from matplotlib.lines import Line2D
import collections
import addcopyfighandler
from haggis.math import full_width_half_max

df = pd.read_csv('test_CORRECT.csv')

ms = pd.read_csv('classified_CORRECT.csv')
ms = ms[ms['mode_shifters'] == 'y']
mode_shifters = list(ms['sxid'])

def find_pt_list(df,i):
    pt_list = []
    for col in df.columns:
        if 'degrees' in col:
            pt_list.append(df[col].iloc[i])
    return pt_list


# classify curve class based on shape
def classify_curve(pts):
    derivs=np.diff(pts)
    d2 = np.diff(derivs)
    extrema=0
    for j in range(1,len(derivs)-1):
        if (derivs[j] > derivs[j-1] and derivs[j] > derivs[j+1]) or (derivs[j] < derivs[j-1] and derivs[j] < derivs[j+1]):
            extrema+=1

    if abs(np.max(derivs)) > 4:
        if abs(np.max(d2)) > 3.7 and extrema > 5:
            return 'multiple'
        else:
            return 'one_hump'
    elif abs(np.max(derivs)) <= 4 and abs(np.max(derivs)) >= 1.2:
        if abs(np.max(d2)) > 3 and extrema > 5:
            return 'multiple'
        else:
            return 'one_hump'
    else:
        if abs(np.max(d2)) > 1:
            return 'one_hump'
        else:
            if np.max(pts) - np.min(pts) < 5:
                return 'flat'
            else:
                return 'one_hump'



# output information for predicted axial curve
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

    
    # calculate stats
    sum_avg = np.mean(min_list)
    comb_avg = np.mean(combined_pt_list)
    sum_std = np.std(min_list)
    comb_std = np.std(combined_pt_list)
    corr = np.correlate(min_list,combined_pt_list)
    sum_pp = np.ptp(min_list)
    comb_pp = np.ptp(combined_pt_list)
    sum_deriv = np.max(abs(np.gradient(min_list)))
    comb_deriv = np.max(abs(np.gradient(combined_pt_list)))
    sum_irr = (np.max(min_list) - np.min(min_list)) / sum_avg * 100
    comb_irr = (np.max(combined_pt_list) - np.min(combined_pt_list)) / comb_avg * 100
    sum_fwhm = 0#full_width_half_max(deg_list,min_list,factor=0.8)
    comb_fwhm = 0#full_width_half_max(deg_list,combined_pt_list,factor=0.8)
    sum_fft = np.fft.fft(min_list,n=1)
    comb_fft = np.fft.fft(combined_pt_list,n=1)
    sum_min = np.min(min_list)

    # classify curve families
    sum_type = classify_curve(min_list)
    comb_type = classify_curve(combined_pt_list)

    if sat in mode_shifters:
        ms = 'y'
    else:
        ms = 'n'

    return {'sxid':sat,'mode_shifter':ms,'sum_avg':sum_avg,'comb_avg':comb_avg,'sum_std':sum_std,'comb_std':comb_std, 'sum_pp':sum_pp, 'comb_pp':comb_pp, 'corr':corr, 'sum_type':sum_type, 'comb_type': comb_type, 'sum_deriv':sum_deriv, 'comb_deriv':comb_deriv, 'sum_irr':sum_irr, 'comb_irr':comb_irr, 'sum_fwhm': sum_fwhm, 'comb_fwhm':comb_fwhm, 'sum_fft':sum_fft, 'comb_fft':comb_fft,'sum_min':sum_min}





#-------------output metrics for predicted axial curves----------------------
dicts = []

for sat in set(df['sxid']):
    d = find_closest_sum_curve(df,sat)
    if d is not None:
        dicts.append(find_closest_sum_curve(df,sat))

final = pd.DataFrame(dicts)
final.to_csv('sum_curve_compare.csv')


#-----------plot predicted axial superimposed traces------------------------------
# deg_list = range(0,361,12)
# plt.figure(figsize=(10, 6))
# non_ms = 0
# msc = 0
# for i in range(0,len(df['sxid'])):
#     pt_list = find_closest_sum_curve(df,df['sxid'].iloc[i])
    
#     if pt_list is None:
#         continue

#     if df['sxid'].iloc[i] in mode_shifters:# and msc<20:
#         plt.plot(deg_list, pt_list,color='orange')
#         msc+=1
#     # elif non_ms < 100:
#     else:
#         plt.plot(deg_list, pt_list,color='blue')
#         non_ms+=1

# plt.xlabel('Azimuth Position (deg)')
# plt.ylabel('Magnetic Flux Density (Gauss)')
# plt.title(f'Predicted Axial Sum Measurements Superimposed'.title())
# plt.grid(True)
# line5 = Line2D([0], [0], label='Non-mode shifters', color='blue')
# line6 = Line2D([0], [0], label='Mode shifters', color='orange')
# plt.legend(handles=[line5,line6])
# plt.show()
