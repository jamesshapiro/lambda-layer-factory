import hashlib
import ulid

def get_ulid():
    return str(ulid.new())[-6:]

def get_hash(dependencies, python_versions):
    dependencies = sorted(dependencies)
    python_versions = sorted(python_versions)
    layer_content = f'{python_versions}::{dependencies}'
    m = hashlib.sha256()
    m.update(layer_content.encode())
    return str(m.hexdigest())

def lambda_handler(event, context):
    my_input = event['input']
    dependencies = my_input['dependencies'].split(',')
    python_versions = my_input['python_versions']
    layer_hash = get_hash(dependencies, python_versions)
    return {'layer_hash': layer_hash, 'ulid': get_ulid()}