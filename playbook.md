# Lambda Layer Factory — Deployment Playbook

Three repos, deploy in order.

---

## Step 1: Terraform Module (commit + push)

```bash
cd ~/code/terragrunt-infrastructure-modules/lambda-layer-factory
git add api-gateway.tf lambda.tf sfn.tf vars.tf outputs.tf layers/
# resources.py deletion:
git add resources.py
git commit -m "lambda-layer-factory: fix hardcoded values, add outputs, clean up vars"
git push
```

## Step 2: Package and Upload Lambda Code to S3

Package the lambda functions into an archive and upload to the code bucket so Terragrunt can reference them:

```bash
cd ~/code/terragrunt-infrastructure-live/athens/us-east-1/default/lambda-layer-factory-backend-v2/lambda_function
zip -r archive.zip *.py *.sh
aws s3 cp archive.zip s3://athens-build-lambda-code/lambda-layer-factory/archive.zip
```

After uploading, grab the new version ID (needed for `lambda_code_object_version` in terragrunt.hcl):

```bash
aws s3api head-object --bucket athens-build-lambda-code --key lambda-layer-factory/archive.zip --query VersionId --output text
```

Update `lambda_code_object_version` in `terragrunt.hcl` if the version ID changed.

## Step 3: Terragrunt Live Config (commit + push + apply)

```bash
cd ~/code/terragrunt-infrastructure-live
git add athens/us-east-1/default/lambda-layer-factory-backend-v2/
git commit -m "lambda-layer-factory: add clean v2 live config"
git push
```

Then apply:

```bash
cd ~/code/terragrunt-infrastructure-live/athens/us-east-1/default/lambda-layer-factory-backend-v2
terragrunt plan    # review first!
terragrunt apply
```

**What to watch for in the plan:**
- SFN definition update (email variable + S3 bucket reference)
- Lambda `get_hash` config change (timeout 30 -> 10)
- New outputs being added
- No unexpected resource recreation

After apply, grab the outputs:

```bash
terragrunt output api_invoke_url
terragrunt output -raw api_key
```

## Step 4: Frontend (set env vars, commit + push, build + deploy)

Create `.env` with the API outputs:

```bash
cd ~/code/lambda-layer-factory-frontend
cat > .env <<EOF
REACT_APP_API_URL=<api_invoke_url from step 2>/layer
REACT_APP_API_KEY=<api_key from step 2>
EOF
```

Commit:

```bash
git add -A
git commit -m "restyle frontend, update runtimes, remove deprecated languages"
git push
```

Build and deploy to S3 + invalidate CloudFront:

```bash
npm run build
aws s3 cp --recursive dist/ s3://demo.lambdalayerfactory.com
aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths "/*"
```

*(You'll need the CloudFront distribution ID — check `terragrunt output` from the static-site module or the AWS console.)*

## Step 5: Smoke Test

1. Visit `demo.lambdalayerfactory.com`
2. Verify warm beige background + paper texture + Noto Serif JP typography
3. Check language dropdown — no .NET, Node 16.x, or Ruby 3.2
4. Select Python — verify 3.13 appears
5. Select Node — verify 22.x appears
6. Add a dependency, invoke API, confirm request goes through
