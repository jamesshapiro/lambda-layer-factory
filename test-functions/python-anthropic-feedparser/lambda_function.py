import json
import anthropic
import feedparser


def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': json.dumps({
            'anthropic_version': anthropic.__version__,
            'feedparser_version': feedparser.__version__,
        }),
    }
