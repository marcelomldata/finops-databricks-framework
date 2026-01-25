from datetime import datetime
from typing import Dict, List
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, current_timestamp
from src.utils.cloud_detector import detect_cloud_from_url, detect_metastore_type

def collect_storage_metrics_unity(
    spark: SparkSession,
    workspace_name: str,
    workspace_url: str
) -> None:
    cloud = detect_cloud_from_url(workspace_url)
    current_ts = datetime.utcnow()
    
    catalogs_df = spark.sql("SHOW CATALOGS")
    catalogs = [row.catalog for row in catalogs_df.collect()]
    
    table_data = []
    
    for catalog in catalogs:
        try:
            spark.sql(f"USE CATALOG {catalog}")
            schemas_df = spark.sql("SHOW SCHEMAS")
            schemas = [row.databaseName for row in schemas_df.collect()]
            
            for schema in schemas:
                try:
                    spark.sql(f"USE {catalog}.{schema}")
                    tables_df = spark.sql("SHOW TABLES")
                    tables = [(row.tableName, row.isTemporary) for row in tables_df.collect()]
                    
                    for table_name, is_temp in tables:
                        if is_temp:
                            continue
                        
                        try:
                            full_table_name = f"{catalog}.{schema}.{table_name}"
                            desc_df = spark.sql(f"DESCRIBE DETAIL {full_table_name}")
                            detail = desc_df.collect()[0] if desc_df.count() > 0 else None
                            
                            if detail:
                                history_df = spark.sql(f"DESCRIBE HISTORY {full_table_name} LIMIT 1")
                                history = history_df.collect()[0] if history_df.count() > 0 else None
                                
                                table_data.append({
                                    "workspace_name": workspace_name,
                                    "workspace_url": workspace_url,
                                    "cloud": cloud,
                                    "metastore_type": "unity_catalog",
                                    "catalog": catalog,
                                    "schema": schema,
                                    "table_name": table_name,
                                    "full_table_name": full_table_name,
                                    "table_type": detail.format if hasattr(detail, 'format') else "",
                                    "location": detail.location if hasattr(detail, 'location') else "",
                                    "provider": detail.provider if hasattr(detail, 'provider') else "",
                                    "num_files": detail.numFiles if hasattr(detail, 'numFiles') else 0,
                                    "size_in_bytes": detail.sizeInBytes if hasattr(detail, 'sizeInBytes') else 0,
                                    "partition_columns": str(detail.partitionColumns if hasattr(detail, 'partitionColumns') else []),
                                    "last_modified": detail.lastModified if hasattr(detail, 'lastModified') else None,
                                    "last_access": history.timestamp if history and hasattr(history, 'timestamp') else None,
                                    "collect_timestamp": current_ts
                                })
                        except Exception as e:
                            continue
                except Exception as e:
                    continue
        except Exception as e:
            continue
    
    if table_data:
        df = spark.createDataFrame(table_data)
        df.write \
            .format("delta") \
            .mode("append") \
            .option("mergeSchema", "true") \
            .save("dbfs:/finops/bronze/storage/tables")

def collect_storage_metrics_hive(
    spark: SparkSession,
    workspace_name: str,
    workspace_url: str
) -> None:
    cloud = detect_cloud_from_url(workspace_url)
    current_ts = datetime.utcnow()
    
    databases_df = spark.sql("SHOW DATABASES")
    databases = [row.databaseName for row in databases_df.collect()]
    
    table_data = []
    
    for database in databases:
        try:
            spark.sql(f"USE {database}")
            tables_df = spark.sql("SHOW TABLES")
            tables = [(row.tableName, row.isTemporary) for row in tables_df.collect()]
            
            for table_name, is_temp in tables:
                if is_temp:
                    continue
                
                try:
                    full_table_name = f"{database}.{table_name}"
                    desc_df = spark.sql(f"DESCRIBE DETAIL {full_table_name}")
                    detail = desc_df.collect()[0] if desc_df.count() > 0 else None
                    
                    if detail:
                        history_df = spark.sql(f"DESCRIBE HISTORY {full_table_name} LIMIT 1")
                        history = history_df.collect()[0] if history_df.count() > 0 else None
                        
                        table_data.append({
                            "workspace_name": workspace_name,
                            "workspace_url": workspace_url,
                            "cloud": cloud,
                            "metastore_type": "hive",
                            "catalog": None,
                            "schema": database,
                            "table_name": table_name,
                            "full_table_name": full_table_name,
                            "table_type": detail.format if hasattr(detail, 'format') else "",
                            "location": detail.location if hasattr(detail, 'location') else "",
                            "provider": detail.provider if hasattr(detail, 'provider') else "",
                            "num_files": detail.numFiles if hasattr(detail, 'numFiles') else 0,
                            "size_in_bytes": detail.sizeInBytes if hasattr(detail, 'sizeInBytes') else 0,
                            "partition_columns": str(detail.partitionColumns if hasattr(detail, 'partitionColumns') else []),
                            "last_modified": detail.lastModified if hasattr(detail, 'lastModified') else None,
                            "last_access": history.timestamp if history and hasattr(history, 'timestamp') else None,
                            "collect_timestamp": current_ts
                        })
                except Exception as e:
                    continue
        except Exception as e:
            continue
    
    if table_data:
        df = spark.createDataFrame(table_data)
        df.write \
            .format("delta") \
            .option("mergeSchema", "true") \
            .mode("append") \
            .save("dbfs:/finops/bronze/storage/tables")

def collect_storage_metrics(
    spark: SparkSession,
    workspace_name: str,
    workspace_url: str
) -> None:
    metastore_type = detect_metastore_type(spark)
    
    if metastore_type == "unity_catalog":
        collect_storage_metrics_unity(spark, workspace_name, workspace_url)
    else:
        collect_storage_metrics_hive(spark, workspace_name, workspace_url)
