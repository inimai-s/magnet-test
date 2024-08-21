# DISPLAY_INTERACTIVE_TREE.PY
# display interactive html file that shows full tree of satellite parts for thruster and regulator assemblies

import pandas as pd
import networkx as nx

from bokeh.models import Circle
from bokeh.plotting import figure, output_file
from bokeh.plotting import from_networkx
from bokeh.io import save
from bokeh.models import Label
import SQL_queries as sq

# SXID as string - change as necessary
sxid = '11072'

engine,db = sq.connect_to_sql_server()
df = sq.get_satpart_children(engine,sxid,['%SL02-%'])


# tree node class that stores relevant information for each part
class TreeNode:
    def __init__(self, description, pn, id, sn = None):
        self.description = description
        self.pn = pn
        self.sn = sn
        self.children = []
        self.parent = []
        self.id = id

    def add_child(self, child_node):
        self.children.append(child_node)
        child_node.parent.append(self)

    def __repr__(self):
        return f'TreeNode({self.description}, PN: {self.pn}, SN: {self.sn})'


# return the part information for the total thruster assembly
def find_thruster_root_info():

    for i in range(len(df['ChildTraceID'])):
        if 'STARLINK SATELLITE' in df['ParentDesc'].iloc[i] and 'THRUSTER ASSEMBLY' in df['ChildDesc'].iloc[i] and sxid == df['ParentSN'].iloc[i]:
            return df['ParentDesc'].iloc[i], df['ParentPN'].iloc[i], df['ChildDesc'].iloc[i], df['ChildPN'].iloc[i], df['ChildSN'].iloc[i]


# return the part information for the primary struct integration kit and regulator assembly
def find_regulator_root_info():

    for i in range(len(df['ChildTraceID'])):
        if ('PRIMARY STRUCT INTEGRATION KIT' in df['ParentDesc'].iloc[i] or 'PRIMARY STRUCTURE INTEGRATION KIT' in df['ParentDesc'].iloc[i]) and 'REGULATOR ASSEMBLY' in df['ChildDesc'].iloc[i]:
            return df['ParentDesc'].iloc[i], df['ParentPN'].iloc[i], df['ParentSN'].iloc[i], df['ChildDesc'].iloc[i], df['ChildPN'].iloc[i], df['ChildSN'].iloc[i]


# check if a node has more children or if it is a leaf of the tree
def continue_tree(node):
    temp_df = df[(df['ParentPN'] == node.pn) & (df['ParentDesc'] == node.description)]
    return temp_df.shape[0] != 0


# add child nodes to all nodes in clevel in BFS order, output a list of the next nodes that have their own children
def add_next_level(clevel):
    global idcount
    nlevel = []
    for node in clevel:
        temp_df = df[(df['ParentPN'] == node.pn) & (df['ParentDesc'] == node.description)]

        for i in range(len(temp_df['ChildTraceID'])):
            if temp_df['ParentPN'].iloc[i] == temp_df['ChildPN'].iloc[i]:
                continue
            new_node = TreeNode(temp_df['ChildDesc'].iloc[i], temp_df['ChildPN'].iloc[i],idcount)
            idcount+=1
            node.add_child(new_node)

            if continue_tree(new_node):
                nlevel.append(new_node)

    return nlevel


# build a networkx graph given the root node of the tree class
def build_networkx_tree(root):
    G = nx.DiGraph()

    def add_node_to_graph(node):
        G.add_node(node.id, desc = node.description, part_number=node.pn, serial_number=node.sn)
        for child in node.children:
            G.add_edge(node.id, child.id)
            add_node_to_graph(child)

    add_node_to_graph(root)
    return G


colormap = []

# add beginning nodes of the satellite root, thruster assembly, and regulator assembly
idcount = 0
sat_description, sat_pn, thruster_description, thruster_pn, thruster_sn = find_thruster_root_info()
prim_struct_description, prim_struct_pn, prim_struct_sn, regulator_description, regulator_pn, regulator_sn = find_regulator_root_info()
root = TreeNode(sat_description, sat_pn, idcount, sxid)
idcount+=1
thruster_assembly = TreeNode(thruster_description, thruster_pn, idcount, thruster_sn)
idcount+=1
prim_struct = TreeNode(prim_struct_description, prim_struct_pn, idcount, prim_struct_sn)
idcount+=1
regulator_assembly = TreeNode(regulator_description, regulator_pn, idcount, regulator_sn)
idcount+=1


# add all thruster constituent parts
root.add_child(thruster_assembly)
current_level = [thruster_assembly]
colormap.extend(['purple','blue'])
while len(current_level) != 0:
    new_level = add_next_level(current_level)
    current_level = new_level

cutoff = idcount

for i in range(2, cutoff - 2):
    colormap.append('blue')


# add all regulator constituent parts
root.add_child(prim_struct)
prim_struct.add_child(regulator_assembly)
colormap.extend(['red','green'])
current_level = [regulator_assembly]
while len(current_level) != 0:
    new_level = add_next_level(current_level)
    current_level = new_level

for i in range(cutoff, idcount):
    colormap.append('green')


# build networkx graph from custom tree
G = build_networkx_tree(root)
pos = nx.bfs_layout(G,0)

HOVER_TOOLTIPS = [
            ("Name", "@desc"),
            ("Part number", "@part_number"),
            ("Serial number", "@serial_number"),
        ]

# create html bokeh plot
plot = figure(tooltips=HOVER_TOOLTIPS,
                tools="pan,wheel_zoom,save,reset", active_scroll='wheel_zoom', title='Thruster & Regulator Components for Satellite '+sxid, sizing_mode='stretch_both', width=1000, height=5000)

network_graph = from_networkx(G, nx.bfs_layout(G,0), scale=5, center=(0, 0), pos=pos)
network_graph.node_renderer.data_source.data['colors'] = colormap
network_graph.node_renderer.glyph = Circle(radius=0.01,radius_dimension='min', fill_color='colors')

for node_id in G.nodes:
    node_description = G.nodes[node_id]['desc']
    label = Label(x=pos[node_id][0] + 0.002, y=pos[node_id][1], text=node_description, 
                  text_font_size="7pt", text_color="black", 
                  text_align='left', text_baseline='bottom')
    plot.add_layout(label)

plot.renderers.append(network_graph)
output_file(filename=str(f'{sxid}tree.html'))
save(plot, filename=f'{sxid}tree.html')
