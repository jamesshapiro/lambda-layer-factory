# Lambda Layer Factory — Deployment Playbook

Three repos, deploy in order. This revision replaces the old auto-publish approach with email-based publish approval via secure UUID links.

---

## Step 1: Terraform Module (commit + push)

New/changed files: `sfn.tf`, `lambda.tf`, `api-gateway.tf`, `dynamodb.tf`

```bash
cd ~/code/terragrunt-infrastructure-modules/lambda-layer-factory
git add sfn.tf lambda.tf api-gateway.tf dynamodb.tf
git commit -m "lambda-layer-factory: email-based publish approval flow"
git push
```

## Step 2: Package and Upload Lambda Code to S3

New files: `send_email.py`, `publish_layer.py`. Changed: `check_cache.py` (now returns `s3_key`).

```bash
cd ~/code/lambda-layer-factory/layer-factory/functions
zip archive.zip check_cache.py get_hash.py reap_instances.py send_email.py publish_layer.py start_layer_creation.py worker.py
aws s3 cp archive.zip s3://athens-build-lambda-code/lambda-layer-factory/archive.zip
```

Grab the new version ID:

```bash
aws s3api head-object --bucket athens-build-lambda-code --key lambda-layer-factory/archive.zip --query VersionId --output text
```

Update `lambda_code_object_version` in `terragrunt.hcl` with the new version ID.

## Step 3: Terragrunt Live Config (commit + push + apply)

```bash
cd ~/code/terragrunt-infrastructure-live
git add athens/us-east-1/default/lambda-layer-factory-backend-v2/
git commit -m "lambda-layer-factory: update lambda code version for publish approval flow"
git push
```

Then apply:

```bash
cd ~/code/terragrunt-infrastructure-live/athens/us-east-1/default/lambda-layer-factory-backend-v2
terragrunt plan    # review first!
terragrunt apply
```

**What to expect in the plan:**

*Created:*
- 2 Lambda functions (`send-email`, `publish-layer`)
- 2 IAM roles + 2 IAM policies + 4 policy attachments (roles + CW logs)
- API Gateway resource `/publish`, GET method, integration, Lambda permission
- DynamoDB TTL enablement

*Updated:*
- SFN definition (email states now invoke `send_email` Lambda instead of SES directly)
- All existing Lambdas (new code version)
- API Gateway deployment (new trigger)

## Step 4: Frontend (commit + push, build + deploy)

Removed: `AdminPanel` component. Cleaned: `DataProvider.js` (removed `autoPublish`/`publishRegions` state), `App.js` (removed `AdminPanel` import).

```bash
cd ~/code/lambda-layer-factory-frontend
git add -A src/components/AdminPanel/ src/components/App/App.js src/components/DataProvider/DataProvider.js
git commit -m "remove AdminPanel, clean up auto-publish state from DataProvider"
git push
npm run build
```

## Step 5: Smoke Test

### Basic request (non-admin email)
1. Visit `demo.lambdalayerfactory.com`
2. Fill in: layer name, **any non-James email**, Python, Python 3.13, a dependency (e.g. `requests` / `2.31.0`)
3. Click "Invoke API"
4. Check inbox — verify styled email arrives with download button, **no publish buttons**

### Admin request (James email)
5. Submit another request with `james.shapiro@gmail.com`
6. Check inbox — verify email has the download button **plus region pill-buttons** (us-east-1, us-east-2, etc.)

### Publish via email link
7. Click the "us-east-1" button in the email
8. Browser should show a styled page with "Layer Published" and the Layer ARN
9. Verify in AWS:
    ```bash
    aws lambda list-layer-versions --layer-name <layer_name>-layer-factory --region us-east-1
    ```
10. Click the same button again — should create a new version (tokens are reusable across regions)

### Cached layer test
11. Submit the same request again (should hit cache)
12. Verify cached email still has publish buttons (if James) since `s3_key` is returned from cache

### Negative cases
13. Visit `/publish` with a bogus token — should show "Invalid or expired publish token" error page
14. Visit `/publish` with missing params — should show "Missing token or region" error page
