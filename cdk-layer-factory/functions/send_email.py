import boto3
import os
import uuid
import time

ses_client = boto3.client('ses')
ddb_client = boto3.client('dynamodb')

TABLE_NAME = os.environ['DDB_TABLE_NAME']
SES_SENDER = os.environ['SES_SENDER_EMAIL']
PUBLISH_API_URL = os.environ['PUBLISH_API_URL']
S3_BUCKET = os.environ['S3_BUCKET']
ADMIN_EMAIL = os.environ['ADMIN_EMAIL']

PUBLISH_REGIONS = [
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'eu-west-1', 'eu-west-2', 'eu-central-1',
    'ap-northeast-1', 'ap-southeast-1', 'ap-southeast-2',
]

SEVEN_DAYS = 7 * 24 * 60 * 60


def build_publish_buttons(token):
    buttons = ''
    for region in PUBLISH_REGIONS:
        url = f'{PUBLISH_API_URL}?token={token}&region={region}'
        buttons += (
            f'<a href="{url}" style="display:inline-block; background:#c45d3e; '
            f'color:#ffffff; padding:8px 16px; border-radius:100px; '
            f'text-decoration:none; font-family:monospace; font-size:11px; '
            f'letter-spacing:0.05em; margin:4px;" target="_blank">'
            f'{region}</a>'
        )
    return buttons


def build_email_html(layer_name, presigned_url, dependencies, publish_section=''):
    return f'''<html><head><meta charset="UTF-8"></head>
<body style="margin:0; padding:0; background-color:#f7f5f0;">
<table role="presentation" width="100%" style="background-color:#f7f5f0; font-family:Georgia,serif;">
<tr><td align="center" style="padding:24px 0;">
<table role="presentation" width="600" style="max-width:600px; width:100%;">
<tr><td style="background-color:#1a1a1a; color:#f7f5f0; padding:24px; text-align:center; font-weight:200; letter-spacing:0.1em; border-radius:12px 12px 0 0;">Lambda Layer Factory</td></tr>
<tr><td style="background:#ffffff; border-left:1px solid #d6d1c9; border-right:1px solid #d6d1c9; padding:32px;">
<table role="presentation" width="100%">
<tr><td style="color:#c45d3e; font-size:14px; letter-spacing:0.15em; text-transform:uppercase; font-family:monospace; padding-bottom:16px;">Layer Created</td></tr>
<tr><td style="color:#1a1a1a; font-size:16px; line-height:1.6; padding-bottom:8px;">Your layer <strong>{layer_name}</strong> is ready for download.</td></tr>
<tr><td style="padding:16px 0;"><a href="{presigned_url}" style="background:#c45d3e; color:#ffffff; padding:12px 32px; border-radius:100px; text-decoration:none; display:inline-block; font-family:monospace; font-size:13px; letter-spacing:0.1em;">Download Layer</a></td></tr>
<tr><td style="color:#8c8780; font-size:13px; line-height:1.6;">Link is valid for 7 days. If it expires, invoke the factory again for a new link.</td></tr>
<tr><td style="color:#8c8780; font-size:13px; border-top:1px solid #d6d1c9; padding-top:16px; margin-top:24px;"><strong>Dependencies:</strong> {dependencies}</td></tr>
{publish_section}
</table>
</td></tr>
<tr><td style="text-align:center; color:#8c8780; font-size:11px; padding:16px; background:#f7f5f0; border-top:1px solid #d6d1c9; border-radius:0 0 12px 12px;">Lambda Layer Factory</td></tr>
</table>
</td></tr></table></body></html>'''


def lambda_handler(event, context):
    email = event['email']
    layer_name = event['layer_name']
    dependencies = event['dependencies']
    presigned_url = event['presigned_url']
    runtimes = event['runtimes']
    s3_key = event.get('s3_key', '')
    ulid = event['ulid']

    publish_section = ''

    if email == ADMIN_EMAIL and s3_key:
        token = str(uuid.uuid4())
        now = int(time.time())

        ddb_client.put_item(
            TableName=TABLE_NAME,
            Item={
                'PK1': {'S': f'PUBLISH#{token}'},
                'S3_BUCKET': {'S': S3_BUCKET},
                'S3_KEY': {'S': s3_key},
                'LAYER_NAME': {'S': layer_name},
                'RUNTIMES': {'SS': runtimes if isinstance(runtimes, list) else [runtimes]},
                'CREATED_AT': {'N': str(now)},
                'TTL': {'N': str(now + SEVEN_DAYS)},
            }
        )

        buttons_html = build_publish_buttons(token)
        publish_section = (
            f'<tr><td style="color:#1a1a1a; font-size:14px; border-top:1px solid #d6d1c9; '
            f'padding-top:16px; margin-top:24px;">'
            f'<strong>Publish as Lambda Layer:</strong></td></tr>'
            f'<tr><td style="padding:12px 0;">{buttons_html}</td></tr>'
        )

    html = build_email_html(layer_name, presigned_url, dependencies, publish_section)

    ses_client.send_email(
        Source=f'Layer Factory Update <{SES_SENDER}>',
        Destination={'ToAddresses': [email]},
        Message={
            'Subject': {'Data': f'{layer_name} CREATED! (Run-ID: {ulid})'},
            'Body': {'Html': {'Data': html}},
        }
    )

    return {'status': 'sent', 'email': email}
