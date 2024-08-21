# MAGNET_TEST_PULL.PY
# pull all magnet test data for a specific list of satellites

import pandas as pd
import build_tree as bt
import output_tables as ot
import SQL_queries as sq

# list of all SXIDs (as strings) that magnet test data needs to be pulled for - change as necessary
v2_sats_list = ['11072','11075']


# connect to server
engine,db = sq.connect_to_sql_server()
sq.pn_to_wo_mapping(engine) # create PN to WorkOrderID mapping file


# add all magnet test data to output.csv for each sat in the list
for sat in v2_sats_list:
    try:
        magnets_tree = sq.get_full_magnets_tree(engine,str(sat)) # pull full magnets tree for sat
        cleaned_tree = ot.create_one_status(magnets_tree) # for components with multiple status with at least 1 Removed, keep only Removed status
        G = bt.add_to_table(sat, cleaned_tree) # format the tree into a networkx graph and take out all Removed status nodes
        rough_table = ot.graph_to_info_output(G) # list information for each node in the tree
        ot.full_table_to_tests(rough_table,sat) # output all magnet test data into output.csv
    except:
        continue
