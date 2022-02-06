curl -X POST [YOUR_API_GATEWAY_ENDPOINT] \
   -H 'Content-Type: application/json' \
   -d '{"layer_name": "reqs_example", "email":[YOUR_EMAIL],"dependencies":"ulid-py==1.1.0,pytz==2021.1","python_versions":["python3.8","python3.9"]}'
