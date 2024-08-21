# BUILD_TREE.PY
# given a tree table output, builds a tree with nodes for each part that stores relevant information

import pandas as pd
import numpy as np
import networkx as nx


# tree node class that stores relevant information for each part
class TreeNode:
    def __init__(self, description, pn, id, wo, traceid, test_sn, status, sn = None):
        self.description = description
        self.pn = pn
        self.sn = sn
        self.children = []
        self.parent = []
        self.id = id
        self.wo = wo
        self.traceid = traceid
        self.test_sn = test_sn
        self.status = status

    def add_child(self, child_node):
        self.children.append(child_node)
        child_node.parent.append(self)

    def __repr__(self):
        return f'TreeNode({self.description}, PN: {self.pn}, SN: {self.sn})'
    

# return the part information for the total thruster assembly
def find_thruster_root_info(df,sxid):

    for i in range(len(df['ChildTraceID'])):
        if 'STARLINK SATELLITE' in df['ParentDesc'].iloc[i] and 'THRUSTER ASSEMBLY' in df['ChildDesc'].iloc[i] and sxid == df['ParentSN'].iloc[i]:
            return df['ParentTraceID'].iloc[i],df['ParentDesc'].iloc[i], df['ParentPN'].iloc[i], df['ChildTraceID'].iloc[i], df['ChildDesc'].iloc[i], df['ChildPN'].iloc[i], df['ChildSN'].iloc[i], df['WoID'].iloc[i], df['TestSerialNumber'].iloc[i], df['Status'].iloc[i]


# return list of part nodes including the parent satellite and all thruster assemblies (issued and removed)
def find_beginning_nodes(df,sxid):

    nodelist = []
    df = df[(df['ChildDesc'].str.contains('THRUSTER ASSEMBLY')) & (df['ParentDesc'].str.contains('STARLINK SATELLITE'))]

    root = TreeNode(df['ParentDesc'].iloc[0], df['ParentPN'].iloc[0], 0, None, df['ParentTraceID'].iloc[0], None, None, sxid)
    nodelist.append(root)

    for i in range(len(df['ChildDesc'])):
        new = TreeNode(df['ChildDesc'].iloc[i], df['ChildPN'].iloc[i], i+1, df['WoID'].iloc[i], df['ChildTraceID'].iloc[i], df['TestSerialNumber'].iloc[i], df['Status'].iloc[i], df['ChildSN'].iloc[i])
        nodelist.append(new)

    return nodelist,len(df['ChildDesc'])+1


# return the part information for the primary struct integration kit and regulator assembly
def find_regulator_root_info(df):

    for i in range(len(df['ChildTraceID'])):
        if ('PRIMARY STRUCT INTEGRATION KIT' in df['ParentDesc'].iloc[i] or 'PRIMARY STRUCTURE INTEGRATION KIT' in df['ParentDesc'].iloc[i]) and 'REGULATOR ASSEMBLY' in df['ChildDesc'].iloc[i]:
            return df['ParentTraceID'].iloc[i], df['ParentDesc'].iloc[i], df['ParentPN'].iloc[i], df['ParentSN'].iloc[i], df['ChildTraceID'].iloc[i], df['ChildDesc'].iloc[i], df['ChildPN'].iloc[i], df['ChildSN'].iloc[i], df['WoID'].iloc[i], df['TestSerialNumber'].iloc[i], df['Status'].iloc[i]


# check if a node has more children or if it is a leaf of the tree
def continue_tree(node,df):
    temp_df = df[(df['ParentPN'] == node.pn) & (df['ParentDesc'] == node.description) & (df['ParentTraceID'] == node.traceid)]
    return temp_df.shape[0] != 0


# add child nodes to all nodes in clevel in BFS order, output a list of the next nodes that have their own children
def add_next_level(clevel,df,idcount):
    nlevel = []
    for node in clevel:
        temp_df = df[(df['ParentPN'] == node.pn) & (df['ParentDesc'] == node.description) & (df['ParentTraceID'] == node.traceid)]

        for i in range(len(temp_df['ChildTraceID'])): # iterate through each child node of a specific parent
            if temp_df['ParentPN'].iloc[i] == temp_df['ChildPN'].iloc[i]:
                continue
            new_node = TreeNode(temp_df['ChildDesc'].iloc[i], temp_df['ChildPN'].iloc[i],idcount,temp_df['WoID'].iloc[i],temp_df['ChildTraceID'].iloc[i], temp_df['TestSerialNumber'].iloc[i], temp_df['Status'].iloc[i], temp_df['ChildSN'].iloc[i])
            idcount+=1
            node.add_child(new_node)

            if continue_tree(new_node,df): # check if the child node has its own children; add to the next level list if it does
                nlevel.append(new_node)

    return nlevel,idcount


# build a networkx graph given the root node of the tree class
def build_networkx_tree(root):
    G = nx.DiGraph()

    def add_node_to_graph(node):
        G.add_node(node.id, desc = node.description, part_number=node.pn, serial_number=node.sn, work_order=node.wo, traceid = node.traceid, test_sn = node.test_sn, status = node.status)
        for child in node.children:
            G.add_edge(node.id, child.id)
            add_node_to_graph(child)

    add_node_to_graph(root)
    return G


# remove all nodes that have 'Removed' status or are in a subtree rooted at a node with 'Removed' status
def remove_subtrees_with_status(graph, root, status):
    nodes_to_remove = set()

    # identify nodes with 'Removed' status and their subtrees
    def mark_removed_subtrees(node):
        if graph.nodes[node]['status'] == status:
            nodes_to_remove.add(node)
            T = nx.dfs_tree(graph, source=node)
            nodes_to_remove.update(set(T.nodes()))
        for child in graph.successors(node):
            mark_removed_subtrees(child)

    mark_removed_subtrees(root)

    # reverse traversal to remove nodes
    nodes_to_remove = list(nodes_to_remove)
    nodes_to_remove.reverse()  # Start removing from the leaves upwards

    for node in nodes_to_remove:
        if node in graph:
            graph.remove_node(node)

    return graph


# return the networkx graph that represents the entire tree from the table output without 'Removed' nodes
def add_to_table(sat,df):
    idcount=0
    sxid = str(sat)

    beginning_nodes, idcount = find_beginning_nodes(df,sxid) # find the satellite root and thruster assembly nodes
    root = beginning_nodes[0]

    for node in beginning_nodes[1:]:
        root.add_child(node)
    current_level = beginning_nodes[1:]  # set up top of the tree


    while len(current_level) != 0: # add the rest of the nodes of the tree
        new_level,idcount = add_next_level(current_level,df,idcount)
        current_level = new_level

    G = build_networkx_tree(root) # build a networkx graph from the tree
    newG = remove_subtrees_with_status(G, 0, 'Removed') # remove all 'Removed' nodes
    return newG
