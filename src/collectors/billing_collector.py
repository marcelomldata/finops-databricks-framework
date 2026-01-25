from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, current_timestamp
import os

def collect_billing_azure(
    spark: SparkSession,
    workspace_name: str,
    workspace_url: str,
    subscription_id: str,
    days_back: int = 30
) -> None:
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.costmanagement import CostManagementClient
    from azure.mgmt.costmanagement.models import QueryDefinition, QueryTimePeriod
    
    credential = DefaultAzureCredential()
    client = CostManagementClient(credential, subscription_id)
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)
    
    query_definition = QueryDefinition(
        type="ActualCost",
        timeframe="Custom",
        time_period=QueryTimePeriod(
            from_property=start_date,
            to=end_date
        ),
        dataset={
            "granularity": "Daily",
            "aggregation": {
                "totalCost": {"name": "PreTaxCost", "function": "Sum"}
            },
            "grouping": [
                {"type": "Dimension", "name": "ResourceId"},
                {"type": "Dimension", "name": "ResourceType"},
                {"type": "Dimension", "name": "ResourceGroupName"}
            ]
        }
    )
    
    scope = f"/subscriptions/{subscription_id}"
    result = client.query.usage(scope, query_definition)
    
    billing_data = []
    current_ts = datetime.utcnow()
    
    if result.rows:
        for row in result.rows:
            billing_data.append({
                "workspace_name": workspace_name,
                "workspace_url": workspace_url,
                "cloud": "azure",
                "date": row[0],
                "resource_id": row[1] if len(row) > 1 else None,
                "resource_type": row[2] if len(row) > 2 else None,
                "resource_group": row[3] if len(row) > 3 else None,
                "cost": float(row[4]) if len(row) > 4 else 0.0,
                "currency": "USD",
                "collect_timestamp": current_ts
            })
    
    if billing_data:
        df = spark.createDataFrame(billing_data)
        df.write \
            .format("delta") \
            .mode("append") \
            .option("mergeSchema", "true") \
            .save("dbfs:/finops/bronze/billing/costs")

def collect_billing_aws(
    spark: SparkSession,
    workspace_name: str,
    workspace_url: str,
    region: str,
    days_back: int = 30
) -> None:
    import boto3
    from datetime import datetime
    
    ce_client = boto3.client('ce', region_name=region)
    
    end_date = datetime.utcnow().strftime('%Y-%m-%d')
    start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    response = ce_client.get_cost_and_usage(
        TimePeriod={
            'Start': start_date,
            'End': end_date
        },
        Granularity='DAILY',
        Metrics=['UnblendedCost'],
        GroupBy=[
            {'Type': 'DIMENSION', 'Key': 'SERVICE'},
            {'Type': 'DIMENSION', 'Key': 'RESOURCE_ID'}
        ]
    )
    
    billing_data = []
    current_ts = datetime.utcnow()
    
    for result in response.get('ResultsByTime', []):
        date = result['TimePeriod']['Start']
        for group in result.get('Groups', []):
            service = group['Keys'][0] if len(group['Keys']) > 0 else None
            resource_id = group['Keys'][1] if len(group['Keys']) > 1 else None
            cost = float(group['Metrics']['UnblendedCost']['Amount'])
            
            billing_data.append({
                "workspace_name": workspace_name,
                "workspace_url": workspace_url,
                "cloud": "aws",
                "date": date,
                "service": service,
                "resource_id": resource_id,
                "cost": cost,
                "currency": result.get('Estimated', False),
                "collect_timestamp": current_ts
            })
    
    if billing_data:
        df = spark.createDataFrame(billing_data)
        df.write \
            .format("delta") \
            .mode("append") \
            .option("mergeSchema", "true") \
            .save("dbfs:/finops/bronze/billing/costs")

def collect_billing_gcp(
    spark: SparkSession,
    workspace_name: str,
    workspace_url: str,
    project_id: str,
    days_back: int = 30
) -> None:
    from google.cloud import billing_v1
    from google.oauth2 import service_account
    
    credentials_path = os.getenv("GCP_CREDENTIALS_PATH")
    if credentials_path:
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
    else:
        from google.auth import default
        credentials, _ = default()
    
    client = billing_v1.CloudBillingClient(credentials=credentials)
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)
    
    billing_data = []
    current_ts = datetime.utcnow()
    
    project_name = f"projects/{project_id}"
    
    try:
        filter_str = f'project.id="{project_id}" AND usage_start_time >= "{start_date.isoformat()}" AND usage_start_time <= "{end_date.isoformat()}"'
        
        from google.cloud import bigquery
        bq_client = bigquery.Client(credentials=credentials, project=project_id)
        
        query = f"""
        SELECT
            usage_start_time,
            service.description as service,
            resource.name as resource_id,
            cost,
            currency
        FROM `{project_id}.billing_export.gcp_billing_export_v1_*`
        WHERE _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE('{start_date.date()}'))
            AND FORMAT_DATE('%Y%m%d', DATE('{end_date.date()}'))
        """
        
        query_job = bq_client.query(query)
        results = query_job.result()
        
        for row in results:
            billing_data.append({
                "workspace_name": workspace_name,
                "workspace_url": workspace_url,
                "cloud": "gcp",
                "date": row.usage_start_time.strftime('%Y-%m-%d') if row.usage_start_time else None,
                "service": row.service,
                "resource_id": row.resource_id,
                "cost": float(row.cost) if row.cost else 0.0,
                "currency": row.currency if row.currency else "USD",
                "collect_timestamp": current_ts
            })
    except Exception as e:
        pass
    
    if billing_data:
        df = spark.createDataFrame(billing_data)
        df.write \
            .format("delta") \
            .mode("append") \
            .option("mergeSchema", "true") \
            .save("dbfs:/finops/bronze/billing/costs")
