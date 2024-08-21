# OUTPUT_TABLES.PY
# functions that format all part tables and magnet tests

import pandas as pd
import numpy as np
import networkx as nx
import otto_tests as otto

# output list of data information for each part in a graph
def graph_to_info_output(G):
    table = pd.DataFrame(columns=['PartNumber','SerialNumber','Description','WorkOrderID','TestSerialNumber'])
    for n in G.nodes:
        new = pd.Series({'PartNumber':G.nodes[n]['part_number'],'SerialNumber':G.nodes[n]['serial_number'],'Description':G.nodes[n]['desc'], 'WorkOrderID':G.nodes[n]['work_order'], 'TestSerialNumber':G.nodes[n]['test_sn']})
        table = table._append(new, ignore_index=True)
    droppedtable = table.drop_duplicates()
    return droppedtable


# remove all nodes in the tree that are not a thruster assembly or magnet
def remove_non_magnets(df):
    return df[(df['ChildDesc'].str.contains('THRUSTER ASSEMBLY')) | (df['ChildDesc'].str.contains('PERMANENT MAGNET'))]


# if a part has more than 1 status and at least 1 of them is 'Removed', only retain the 'Removed' status in the tree
def create_one_status(df):
    grouped = df.groupby(['ChildTraceID', 'ParentTraceID']) # Group by 'ChildTraceId' and 'ParentTraceId'
    # Filter rows
    filtered_rows = grouped.apply(lambda x: x[x['Status'] == 'Removed'] if any(x['Status'] == 'Removed') else x)
    # Reset index to clean up resulting DataFrame
    filtered_df = filtered_rows.droplevel(0).reset_index(drop=True)
    return filtered_df


# outputs all magnet test data for a given list of magnets
def full_table_to_tests(df,sat):
    pn_wo_map = pd.read_pickle('pn_wo_map.pkl')
    df = df[df['Description'].str.contains('PERMANENT MAGNET')] # work with only magnet parts

    test_sns_str = set(df['TestSerialNumber']) # all test serial numbers of the magnets
    snpndict={}

    for item in test_sns_str:
        temp = df[df['TestSerialNumber'] == item]
        wo_list = set(temp['WorkOrderID'])
        map = pn_wo_map[pn_wo_map['WorkOrderID'].isin(wo_list)]
        snpndict[int(item)] = set(map['PartNumber']) # all part numbers associated with the tests of a test serial number

    test_dicts = []
    tests = otto.find_latest_magnet_tests(snpndict) # find all magnet tests
    for test in tests:
        test_dicts.append(otto.generate_magnet_test_entry(test,sat)) # format each test into csv row

    test_table = pd.DataFrame(test_dicts)
    test_table.to_csv('output.csv',mode='a',index=False,header=False) # add to output.csv
