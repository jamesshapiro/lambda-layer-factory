import hashlib
import ulid

def get_ulid():
    return str(ulid.new())[-6:]

def get_hash(dependencies, runtimes):
    dependencies = sorted(dependencies)
    runtimes = sorted(runtimes)
    layer_content = f'{runtimes}::{dependencies}'
    m = hashlib.sha256()
    m.update(layer_content.encode())
    return str(m.hexdigest())

def lambda_handler(event, context):
    my_input = event['input']
    dependencies = my_input['dependencies'].split(',')
    runtimes = my_input['runtimes']
    layer_hash = get_hash(dependencies, runtimes)
    return {'layer_hash': layer_hash, 'ulid': get_ulid()}