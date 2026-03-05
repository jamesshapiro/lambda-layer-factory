import boto3

CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Simple Lambda@Edge Static Content Response</title>
</head>
<body>
    <p>404 Error! Couldn't find page: {}</p>
</body>
</html>
"""

def get_page_not_found(uri):
    return {
        'status': '404',
        'statusDescription': 'Page Not Found',
        'body': CONTENT.format(uri)
    }

whitelist = [
    '/',
    '/favicon.ico',
    '/logo192.png',
    '/manifest.json',
]

valid_paths = [
    '/login',
    '/about'
]

whitelist.extend(valid_paths)
whitelist.extend([f'{path}/' for path in valid_paths])

prefix_whitelist = [
    '/static/js/',
    '/static/css/'
]

def lambda_handler(event, context):
    request = event['Records'][0]['cf']['request']
    uri = event['Records'][0]['cf']['request']['uri']
    if request['headers']['host'][0]['value'] in [
        'www.lambdalayerfactory.com',
        'www.lambdalayerfactory.com/',
        'http://www.lambdalayerfactory.com',
        'http://www.lambdalayerfactory.com/',
        'https://www.lambdalayerfactory.com',
        'https://www.lambdalayerfactory.com/'
    ]:
        return {
            'status': '301',
            'statusDescription': 'Redirecting to apex domain',
            'headers': {
                'location': [{
                    'key': 'Location',
                    'value': f'https://lambdalayerfactory.com{uri}'
                }]
            }
        }
    result = get_page_not_found(uri)
    if uri in whitelist:
        result = request
    if any(uri.startswith(prefix) for prefix in prefix_whitelist):
        result = request
    return result
    