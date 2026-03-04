import boto3
import os
import time

ddb_client = boto3.client('dynamodb')

TABLE_NAME = os.environ['DDB_TABLE_NAME']


def html_response(status_code, title, body_html):
    html = f'''<html><head><meta charset="UTF-8"></head>
<body style="margin:0; padding:0; background-color:#f7f5f0;">
<table role="presentation" width="100%" style="background-color:#f7f5f0; font-family:Georgia,serif;">
<tr><td align="center" style="padding:24px 0;">
<table role="presentation" width="600" style="max-width:600px; width:100%;">
<tr><td style="background-color:#1a1a1a; color:#f7f5f0; padding:24px; text-align:center; font-weight:200; letter-spacing:0.1em; border-radius:12px 12px 0 0;">Lambda Layer Factory</td></tr>
<tr><td style="background:#ffffff; border-left:1px solid #d6d1c9; border-right:1px solid #d6d1c9; padding:32px;">
<table role="presentation" width="100%">
<tr><td style="color:#c45d3e; font-size:14px; letter-spacing:0.15em; text-transform:uppercase; font-family:monospace; padding-bottom:16px;">{title}</td></tr>
{body_html}
</table>
</td></tr>
<tr><td style="text-align:center; color:#8c8780; font-size:11px; padding:16px; background:#f7f5f0; border-top:1px solid #d6d1c9; border-radius:0 0 12px 12px;">Lambda Layer Factory</td></tr>
</table>
</td></tr></table></body></html>'''
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'text/html'},
        'body': html,
    }


def lambda_handler(event, context):
    params = event.get('queryStringParameters') or {}
    token = params.get('token', '')
    region = params.get('region', '')

    if not token or not region:
        return html_response(400, 'Error',
            '<tr><td style="color:#1a1a1a; font-size:16px; line-height:1.6;">Missing token or region parameter.</td></tr>')

    response = ddb_client.get_item(
        TableName=TABLE_NAME,
        Key={'PK1': {'S': f'PUBLISH#{token}'}}
    )

    if 'Item' not in response:
        return html_response(404, 'Error',
            '<tr><td style="color:#1a1a1a; font-size:16px; line-height:1.6;">Invalid or expired publish token.</td></tr>')

    item = response['Item']
    ttl = int(item['TTL']['N'])
    if time.time() > ttl:
        return html_response(410, 'Expired',
            '<tr><td style="color:#1a1a1a; font-size:16px; line-height:1.6;">This publish link has expired.</td></tr>')

    s3_bucket = item['S3_BUCKET']['S']
    s3_key = item['S3_KEY']['S']
    layer_name = item['LAYER_NAME']['S']
    runtimes = list(item['RUNTIMES']['SS'])

    lambda_client = boto3.client('lambda', region_name=region)

    result = lambda_client.publish_layer_version(
        LayerName=f'{layer_name}-layer-factory',
        Description=f'{layer_name} created by Layer Factory',
        Content={
            'S3Bucket': s3_bucket,
            'S3Key': s3_key,
        },
        CompatibleRuntimes=runtimes,
    )

    layer_arn = result['LayerVersionArn']

    return html_response(200, 'Layer Published',
        f'<tr><td style="color:#1a1a1a; font-size:16px; line-height:1.6; padding-bottom:8px;">'
        f'Layer <strong>{layer_name}</strong> published to <strong>{region}</strong>.</td></tr>'
        f'<tr><td style="color:#8c8780; font-size:13px; line-height:1.6; word-break:break-all;">'
        f'<strong>Layer ARN:</strong> {layer_arn}</td></tr>')
