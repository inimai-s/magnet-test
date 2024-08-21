# SQL_QUERIES.py
# file that contains all relevant SQL queries to pull satellite parts

import pandas as pd

from sqlalchemy import create_engine

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import build_tree as bt
import output_tables as ot


# call function first to establish connection with server - pass returned engine to other functions
def connect_to_sql_server():
    DATABASE_USERNAME = "satrel" 

    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://'+DATABASE_USERNAME
    app.config['SQLALCHEMY_ECHO'] = True
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)

    # check if the connection is successfully established or not and if yes return an engine object
    with app.app_context():
        try:
            engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], use_setinputsizes=False)
            return engine, db
        except Exception as e:
            return None


# run specific warp query with string input
def run_warp_query(engine, sql_query, *params):
    sql_df = pd.read_sql(sql = sql_query, con = engine, params = params)   
    return sql_df


def get_satpart_children(engine, part_sn, part_pn_like=['%'], child_pn_like=['%']):
    # get as-built children of the given part in warp
    # part_pn_like should be a list of strings that the part PN can be LIKE.
    # child_pn_like should be a list of strings that the child PN can be LIKE.
    
    results = run_warp_query(engine,
        f"""
            WITH genealogy_parent_cte AS (
                SELECT 
                    ChildTraceID, 
                    ParentTraceID
                FROM SpacexERP.trc.GenealogyTraceDetail RootGenealogy
                INNER JOIN SpacexERP.trc.Trace as RootTrace 
                    ON RootGenealogy.ParentTraceID = RootTrace.TraceID
                    AND RootTrace.SerialNumber = ?
                INNER JOIN SpacexERP.inv.Part AS RootPart ON RootPart.PartID = RootTrace.PartID
                    AND (
                        {' OR '.join(["RootPart.PartNumber LIKE '" + pn + "'" for pn in part_pn_like])}
                    )
                UNION ALL

                SELECT 
                    child.ChildTraceID, 
                    child.ParentTraceID
                FROM SpacexERP.trc.GenealogyTraceDetail child
                INNER JOIN genealogy_parent_cte parent
                    ON parent.ChildTraceID = child.ParentTraceID
            )
            SELECT DISTINCT
                all_parent.ChildTraceID,
                all_parent.ParentTraceID,
                ParentPart.Description as ParentDesc,
                ParentPart.PartNumber as ParentPN,
                ParentTrace.SerialNumber as ParentSN,
                ChildPart.Description as ChildDesc,
                ChildPart.PartNumber as ChildPN,
                ChildTrace.SerialNumber as ChildSN,
                r.WorkOrderID as WoID,
                t2.SerialNumber as TestSerialNumber,
                op.SequenceNumber as SequenceNumber,
                CASE 
                   WHEN r2.IssuedQuantity > 0 THEN 'Issued'
                   WHEN r2.IssuedQuantity < 0 THEN 'Removed'
                   ELSE 'Unknown'
                END AS [Status]
            FROM genealogy_parent_cte all_parent
                JOIN SpacexERP.trc.Trace AS ParentTrace ON ParentTrace.TraceID = all_parent.ParentTraceID
                JOIN SpacexERP.inv.Part AS ParentPart ON ParentPart.PartID = ParentTrace.PartID
                JOIN SpacexERP.trc.Trace AS ChildTrace ON ChildTrace.TraceID = all_parent.ChildTraceID
                JOIN SpacexERP.inv.Part AS ChildPart ON ChildPart.PartID = ChildTrace.PartID
                LEFT JOIN SpacexERP.trc.GenealogyTraceDetail t ON t.ChildTraceID = ChildTrace.TraceID AND t.ParentTraceID = ParentTrace.TraceID
                LEFT JOIN SpacexERP.sfc.Requirement r ON r.RequirementID = t.RequirementID and r.PartID = ChildPart.PartID
                LEFT JOIN SpacexERP.sfc.WorkOrder wo ON wo.WorkOrderID = r.WorkOrderID
                LEFT JOIN SpacexERP.sfc.Operation op ON op.WorkOrderID = wo.WorkOrderID
                LEFT JOIN SpacexERP.trc.Trace t2 ON t2.LotCode = CONCAT('WO',wo.BaseID)
                LEFT JOIN SpacexERP.sfc.Requirement r2 ON r2.OperationID = op.OperationID and r2.PartID = ChildPart.PartID

            WHERE {' OR '.join(["ChildPart.PartNumber LIKE '" + pn + "'" for pn in child_pn_like])}
            AND r2.RequirementID is not NULL
        """,
        part_sn
    )
    return results


# returns a subtree of the full tree outputted from get_satpart_children where the leaves only correspond to magnets
def get_full_magnets_tree(engine, sn):
    results = run_warp_query(engine,
        f"""
            WITH genealogy_parent_cte AS (
                SELECT 
                    ChildTraceID, 
                    ParentTraceID
                FROM SpacexERP.trc.GenealogyTraceDetail RootGenealogy
                INNER JOIN SpacexERP.trc.Trace as RootTrace 
                    ON RootGenealogy.ParentTraceID = RootTrace.TraceID
                    AND RootTrace.SerialNumber = ?
                    INNER JOIN SpacexERP.inv.Part AS RootPart ON RootPart.PartID = RootTrace.PartID
                    AND RootPart.PartNumber LIKE '%SL02-%'
                UNION ALL

                SELECT 
                    child.ChildTraceID, 
                    child.ParentTraceID
                FROM SpacexERP.trc.GenealogyTraceDetail child
                INNER JOIN genealogy_parent_cte parent
                    ON parent.ChildTraceID = child.ParentTraceID
            )
            SELECT DISTINCT
                all_parent.ChildTraceID,
                all_parent.ParentTraceID,
                ParentPart.Description as ParentDesc,
                ParentPart.PartNumber as ParentPN,
                ParentTrace.SerialNumber as ParentSN,
                ChildPart.Description as ChildDesc,
                ChildPart.PartNumber as ChildPN,
                ChildTrace.SerialNumber as ChildSN,
                r.WorkOrderID as WoID,
                t2.SerialNumber as TestSerialNumber,
                CASE 
                   WHEN r2.IssuedQuantity > 0 THEN 'Issued'
                   WHEN r2.IssuedQuantity < 0 THEN 'Removed'
                   ELSE 'Unknown'
                END AS [Status]
            FROM genealogy_parent_cte all_parent
                JOIN SpacexERP.trc.Trace AS ParentTrace ON ParentTrace.TraceID = all_parent.ParentTraceID
                JOIN SpacexERP.inv.Part AS ParentPart ON ParentPart.PartID = ParentTrace.PartID
                JOIN SpacexERP.trc.Trace AS ChildTrace ON ChildTrace.TraceID = all_parent.ChildTraceID
                JOIN SpacexERP.inv.Part AS ChildPart ON ChildPart.PartID = ChildTrace.PartID
                JOIN SpacexERP.trc.GenealogyTraceDetail t ON t.ChildTraceID = ChildTrace.TraceID AND t.ParentTraceID = ParentTrace.TraceID
                JOIN SpacexERP.sfc.Requirement r ON r.RequirementID = t.RequirementID and r.PartID = ChildPart.PartID
                LEFT JOIN SpacexERP.sfc.WorkOrder wo ON wo.WorkOrderID = r.WorkOrderID
                LEFT JOIN SpacexERP.sfc.Operation op ON op.WorkOrderID = wo.WorkOrderID
                LEFT JOIN SpacexERP.trc.Trace t2 ON t2.LotCode = CONCAT('WO',wo.BaseID)
                LEFT JOIN SpacexERP.sfc.Requirement r2 ON r2.OperationID = op.OperationID and r2.PartID = ChildPart.PartID

            WHERE ChildPart.Description LIKE '%PERMANENT MAGNET%' or ChildPart.Description LIKE '%THRUSTER ASSEMBLY%'
            AND r2.RequirementID is not NULL

        """, sn 
    )
    return results


# find the PartNumber associated with each WorkOrderID
def pn_to_wo_mapping(engine):
    results = run_warp_query(engine,
        f"""
        select p.PartNumber,wo.WorkOrderID from SpacexERP.sfc.WorkOrder wo
        join SpacexERP.inv.Part p on p.PartID = wo.PartID
        """                 
    )
    results.to_pickle('pn_wo_map.pkl')
