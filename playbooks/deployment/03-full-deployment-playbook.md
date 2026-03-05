# Full Deployment Playbook

```bash
cd ~/code/lambda-layer-factory/layer-factory/functions
zip archive.zip check_cache.py get_hash.py reap_instances.py send_email.py publish_layer.py start_layer_creation.py worker.py
aws s3 cp archive.zip s3://athens-build-lambda-code/lambda-layer-factory/archive.zip

aws s3api head-object --bucket athens-build-lambda-code --key lambda-layer-factory/archive.zip --query VersionId --output text
```

```bash
cd ~/code/terragrunt-infrastructure-live/athens/us-east-1/default/lambda-layer-factory-backend-v2
vim terragrunt.hcl
```

```bash
terragrunt plan
terragrunt apply
```

```bash
cd ~/code/lambda-layer-factory-frontend
npm run build
```
