import json


def lambda_handler(event, context):
    """Test that layer dependencies are importable."""
    results = {}
    test_imports = event.get('test_imports', ['requests'])
    for module_name in test_imports:
        try:
            mod = __import__(module_name)
            version = getattr(mod, '__version__', 'unknown')
            results[module_name] = {'status': 'ok', 'version': version}
        except ImportError as e:
            results[module_name] = {'status': 'error', 'message': str(e)}
    return {
        'statusCode': 200,
        'body': json.dumps(results, indent=2),
    }
