import json
import time
import boto3
import requests
import pandas as pd
import pyarrow.parquet as pq
from airflow import DAG
from base64 import b64encode
from datetime import datetime, timedelta
from airflow.providers.amazon.aws.operators.s3 import S3CopyObjectOperator
from airflow.operators.python_operator import PythonOperator

#declarations
region_name = 'ap-southeast-1'

emr_client = boto3.client('emr', region_name=region_name)
s3_client = boto3.client('s3',region_name=region_name)
livy_url = 'http://{master_dns}:8998/batches'

   
def read_config(**kwargs):

    bucket_name=kwargs['dag_run'].conf.get('land_bucket', 'shriraaman.s-landingbucket-01')
    key=kwargs['dag_run'].conf.get('config', 'notfound')
    print(bucket_name,key)
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    json_data = json.loads(response['Body'].read().decode('utf-8'))
    print("Read JSON data:", json_data)
    fin_active_land=str(json_data['actives']['landing_bucket'])
    active_raw=str(json_data['actives']['source_bucket'])
    fin_view_land=str(json_data['viewership']['landing_bucket'])
    view_raw=str(json_data['viewership']['source_bucket'])
    
    active_stage=str(json_data['actives']['destination_bucket'])
    view_stage=str(json_data['viewership']['destination_bucket'])
    
    
    fin_active_raw=active_raw+"raw-actives.parquet"
    fin_view_raw=view_raw+"raw-viewership.parquet"
    
    comma_field=str(json_data['actives']['transformations']['to_string']['location'])
    active_decimal=[]
    view_decimal=[]
    active_lat=json_data['actives']['transformations']['to_decimal']['latitude']
    active_long=json_data['actives']['transformations']['to_decimal']['longitude']
    active_decimal+=[active_lat,active_long]
    
    view_lat=json_data['viewership']['transformations']['to_decimal']['latitude']
    view_long=json_data['viewership']['transformations']['to_decimal']['longitude']
    view_decimal+=[view_lat,view_long]
    
    kwargs['ti'].xcom_push(key='active_land', value=fin_active_land)
    kwargs['ti'].xcom_push(key='active_raw', value=fin_active_raw)
    kwargs['ti'].xcom_push(key='active_stage', value=active_stage)
    kwargs['ti'].xcom_push(key='view_land', value=fin_view_land)
    kwargs['ti'].xcom_push(key='view_raw', value=fin_view_raw)
    kwargs['ti'].xcom_push(key='view_stage', value=view_stage)
    kwargs['ti'].xcom_push(key='active_decimal_field', value=active_decimal)
    kwargs['ti'].xcom_push(key='view_decimal_field', value=view_decimal)
    kwargs['ti'].xcom_push(key='comma_field', value=comma_field)


def staging_check(source_loc,dest_loc,decimal_field,comma_field,source_rows):
    
    dest_table = pq.read_table(dest_loc).to_pandas()
    dest_rows = len(dest_table)
    
    if not source_rows == dest_rows :
        raise Exception(f"Data consistency check failed. Contents of {source_loc} and {dest_loc} do not match.")
        
    print(f"Data consistency check Passed. Contents of {source_loc} and {dest_loc} match.")
    
    
    
    for dec in decimal_field:
        decimal_check = dest_table[dec].apply(lambda x: len(str(x).split('.')[-1]) == 7 if pd.notnull(x) else True).all()
        print(decimal_check)
        if not decimal_check:
            raise Exception(f"Data transformation check failed. Contents of {dest_loc}-{dec} is not Decimal with 7 precision.")
        
        print(f"Data transformation check Passed. Contents of {dest_loc}-{dec} is Decimal with 7 precision.")
    
    
    comma_check = dest_table[comma_field].apply(lambda x: isinstance(x, str) and ',' in x if pd.notnull(x) else True).all()
    
    if not comma_check:
        raise Exception(f"Data transformation check failed. Contents of {dest_loc} is not Comma-separated string.")
    
    print(f"Data transformation check Passed. Contents of {dest_loc} is Comma-separated string.")
    
    dest_table=None

    
    
    
def pre_validation(**kwargs):
    active_land =str(kwargs['ti'].xcom_pull(task_ids='read_config_job', key='active_land'))
    active_raw=str(kwargs['ti'].xcom_pull(task_ids='read_config_job', key='active_raw'))
    print(active_land)
    
    view_land=str(kwargs['ti'].xcom_pull(task_ids='read_config_job', key='view_land'))
    view_raw=str(kwargs['ti'].xcom_pull(task_ids='read_config_job', key='view_raw'))
    print(view_land)
    
    source_pq=pq.ParquetFile(active_land)
    sou_metadata = source_pq.metadata
    source_rows = sou_metadata.num_rows
    
    dest_pq=pq.ParquetFile(active_raw)
    dest_metadata = dest_pq.metadata
    dest_rows = dest_metadata.num_rows
    
    source_pq=pq.ParquetFile(view_land)
    sou_metadata1 = source_pq.metadata
    source_rows1 = sou_metadata1.num_rows
    
    dest_pq=pq.ParquetFile(view_raw)
    dest_metadata1 = dest_pq.metadata
    dest_rows1 = dest_metadata1.num_rows
    
    if not (source_rows == dest_rows  and source_rows1 == dest_rows1) :
        raise Exception(f"Data consistency check failed. Contents of Landing and Raw bucket do not match.")
        
    print(f"Data consistency check Passed. Contents of Landing and Raw bucket match.")
    



#emr cluster creation
def create_emr_cluster(**kwargs):
    
    emr_cluster_config = {
        'Name': 'airflow_test_f',
        'ReleaseLabel': 'emr-7.0.0',
        'Applications': [{'Name': 'Spark'}, {'Name': 'Livy'},{'Name': 'Hadoop'},{'Name': 'Hive'}, {'Name': 'JupyterEnterpriseGateway'}],
        'LogUri': 's3://aws-logs-552490513043-ap-southeast-1/elasticmapreduce/',
        'VisibleToAllUsers': True,
        'Instances': {
            'InstanceGroups': [
                {
                    'Name': 'Primary node',
                    'Market': 'ON_DEMAND',
                    'InstanceRole': 'MASTER',
                    'InstanceType': 'm5.xlarge',
                    'InstanceCount': 1, 
                }],
                
            'Ec2SubnetId': 'subnet-07cb6228eeed39914',
            'Ec2KeyName': '5599-sparksub',
            'KeepJobFlowAliveWhenNoSteps': True,
            'TerminationProtected': False,
        },
        'Configurations': [  
            {
                "Classification": "delta-defaults", 
                "Properties": {"delta.enabled": "true"}
            }
        ],
        'JobFlowRole': 'EMR_EC2_DefaultRole',
        'ServiceRole': 'EMR_DefaultRole',
        
            
    }
  

    response = emr_client.run_job_flow(**emr_cluster_config)
    cluster_id = response['JobFlowId']
    kwargs['ti'].xcom_push(key='cluster_id', value=cluster_id)
    print("clusterid:"+cluster_id)
    
    waiter = emr_client.get_waiter('cluster_running')
    waiter.wait(ClusterId=cluster_id)
    
    response = emr_client.describe_cluster(ClusterId=cluster_id)
    master_dns = response['Cluster']['MasterPublicDnsName']
    kwargs['ti'].xcom_push(key='master_dns', value=master_dns)

#livy submission job
def submit_livy_job(**kwargs):
    master_dns = kwargs['ti'].xcom_pull(task_ids='create_emr_cluster', key='master_dns')   
    s3_pyspark_file_path = str(kwargs['dag_run'].conf.get('pyspark', 's3://shriraaman.s-landingbucket-01/source/finspark.py'))
    livy_payload = {"file": s3_pyspark_file_path}
    print(livy_payload)
    livy_urlf = livy_url.format(master_dns=master_dns)
    
    livy_response = requests.post(livy_urlf, json=livy_payload)
    
    if livy_response.status_code in [200, 201]:
        batch_id = livy_response.json().get('id')

        print('Livy job submitted successfully. Batch ID:', batch_id)
    else:
        print('Error submitting Livy job. Response:', livy_response.text)
        
        
    livy_fin_url=livy_urlf+"/"+str(batch_id)+"/state"
    print(livy_fin_url)
    getr = requests.get(livy_fin_url)
    #print("befor:"+getr.text)
    states='running'
    while states not in ['success', 'dead']:
        time.sleep(30)
        try:
            print("before:"+states)
            getr = requests.get(livy_fin_url)
            
            states = getr.json()['state']
            #print(states)
            
        except requests.RequestException as e:
            
            print("Error during API request:", e)
        

def post_validation(**kwargs):
    active_raw = kwargs['ti'].xcom_pull(task_ids='read_config_job', key='active_raw')
    active_stag = kwargs['ti'].xcom_pull(task_ids='read_config_job', key='active_stage')
    view_raw= kwargs['ti'].xcom_pull(task_ids='read_config_job', key='view_raw')
    view_stag= kwargs['ti'].xcom_pull(task_ids='read_config_job', key='view_stage')
    
    
    active_decimal_field = kwargs['ti'].xcom_pull(task_ids='read_config_job', key='active_decimal_field')
    view_decimal_field = kwargs['ti'].xcom_pull(task_ids='read_config_job', key='view_decimal_field')
    comma_field=kwargs['ti'].xcom_pull(task_ids='read_config_job', key='comma_field')

    source_pq=pq.ParquetFile(active_raw)
    smetadata = source_pq.metadata
    active_source_rows = smetadata.num_rows
    print(f'The number of rows in the {active_raw} Parquet file is: {active_source_rows}')
  
        
    source_pq1=pq.ParquetFile(view_raw)
    metadata1= source_pq1.metadata
    view_source_rows = metadata1.num_rows
    print(f'The number of rows in the {view_raw} Parquet file is: {view_source_rows}')
    
    
    staging_check(active_raw,active_stag,active_decimal_field,comma_field,active_source_rows)
    staging_check(view_raw,view_stag,view_decimal_field,comma_field,view_source_rows)
        
        
#cluster termination
def terminate_emr_cluster(**kwargs):
    cluster_id = kwargs['ti'].xcom_pull(task_ids='create_emr_cluster', key='cluster_id')
    
    
    emr_client.terminate_job_flows(JobFlowIds=[cluster_id])


#dag
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'emr_spark_dag',
    default_args=default_args,
    schedule_interval=None,
)


read_config_task=PythonOperator(
    task_id="read_config_job",
    python_callable=read_config,
    provide_context=True,
    dag=dag,
)

copy_active_task = S3CopyObjectOperator(
    task_id='copy_files_active_task',
    source_bucket_key="{{ task_instance.xcom_pull(task_ids='read_config_job', key='active_land') }}",
    dest_bucket_key="{{ task_instance.xcom_pull(task_ids='read_config_job', key='active_raw') }}",
    dag=dag,
)


copy_view_task = S3CopyObjectOperator(
    task_id='copy_files_view_task',
    source_bucket_key="{{ task_instance.xcom_pull(task_ids='read_config_job', key='view_land') }}",
    dest_bucket_key="{{ task_instance.xcom_pull(task_ids='read_config_job', key='view_raw') }}",
    dag=dag,
)


pre_task = PythonOperator(
    task_id='pre_validation_task',
    python_callable=pre_validation,
    provide_context=True,
    dag=dag,
)
 
 

create_emr_cluster_task = PythonOperator(
    task_id='create_emr_cluster',
    python_callable=create_emr_cluster,
    provide_context=True,
    dag=dag,
)

submit_livy_task = PythonOperator(
    task_id='submit_livy_job',
    python_callable=submit_livy_job,
    provide_context=True,
    dag=dag,
)


post_task = PythonOperator(
    task_id='post_validation_task',
    python_callable=post_validation,
    provide_context=True,
    dag=dag,
)
 
 
terminate_emr_cluster_task = PythonOperator(
    task_id='terminate_emr_cluster',
    python_callable=terminate_emr_cluster,
    provide_context=True,
    dag=dag,

)

#task 
read_config_task >> copy_active_task >> copy_view_task >> pre_task >> create_emr_cluster_task >> submit_livy_task >> post_task >> terminate_emr_cluster_task
