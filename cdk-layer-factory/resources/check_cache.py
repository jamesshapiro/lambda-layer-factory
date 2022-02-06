import boto3
import os

s3_client = boto3.client('s3')
ddb_client = boto3.client('dynamodb')

table_name = os.environ['DDB_TABLE_NAME']
layer_bucket = os.environ['S3_BUCKET']

def lambda_handler(event, context):
    my_input = event['input']
    print(f'{event=}')
    print(f'{my_input=}')
    layer_hash = my_input['hashresult']['layer_hash']
    response = ddb_client.get_item(
        TableName=table_name,
        Key={
            'PK1': {'S': layer_hash}
        }
    )
    print(f'{response=}')
    if 'Item' in response:
        key = response['Item']['S3_KEY']['S']
        bucket_name = response['Item']['S3_BUCKET']['S']
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': key
            },
            ExpiresIn=21600
        )
        return {'presigned_url': url}
    return {'presigned_url': 'NOT FOUND!'}