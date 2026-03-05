# Deploy: Multi-Language Build Support + Runtime Updates + Layer Suffix

**What changed:**
- Backend: added build logic for Node.js, Ruby, Java (previously only Python worked)
- Backend: extracted `get_wrapup_commands()` to share zip/S3/publish logic across languages
- Backend: layer suffix is `-lf` for `james.shapiro@gmail.com`, `-layer-factory` for everyone else
- Backend: unsupported languages (Go, Rust, C++, Custom, .NET) now raise a clear error instead of crashing
- Frontend: removed deprecated runtimes (Python 3.9, Node.js 18.x), added new ones (Python 3.14, Node.js 24.x, Java 25, .NET 8/9/10)
- Frontend: fixed runtime IDs to match AWS identifiers (`node20.x` → `nodejs20.x`, `java8-amazon-linux-2` → `java8.al2`)
- `send_email.py` stores email in DynamoDB publish record so `publish_layer.py` can apply the correct suffix

---

## 1. Commit & push Lambda code

```bash
cd ~/code/lambda-layer-factory
git add cdk-layer-factory/functions/send_email.py cdk-layer-factory/functions/publish_layer.py
git commit -m "store email in publish record, conditional -lf suffix for james"
git push
```

## 2. Upload Lambda archive to S3

```bash
cd ~/code/lambda-layer-factory/cdk-layer-factory/functions
zip archive.zip check_cache.py get_hash.py reap_instances.py send_email.py publish_layer.py start_layer_creation.py worker.py
aws s3 cp archive.zip s3://athens-build-lambda-code/lambda-layer-factory/archive.zip
```

## 3. Update live config with new code version

```bash
aws s3api head-object \
  --bucket athens-build-lambda-code \
  --key lambda-layer-factory/archive.zip \
  --query VersionId --output text
```

Paste that version ID into `lambda_code_object_version` in:
`~/code/terragrunt-infrastructure-live/athens/us-east-1/default/lambda-layer-factory-backend-v2/terragrunt.hcl`

## 4. Commit & push backend v2

```bash
cd ~/code/terragrunt-infrastructure-live
git add athens/us-east-1/default/lambda-layer-factory-backend-v2/lambda_function/start_layer_creation.py athens/us-east-1/default/lambda-layer-factory-backend-v2/terragrunt.hcl
git commit -m "lambda-layer-factory: multi-language build support, conditional -lf suffix, update code version"
git push
```

## 5. Terragrunt apply

```bash
cd ~/code/terragrunt-infrastructure-live/athens/us-east-1/default/lambda-layer-factory-backend-v2
terragrunt plan
terragrunt apply
```

**Expect updated:** all Lambda code versions (new S3 object version)

## 6. Commit & push frontend

```bash
cd ~/code/lambda-layer-factory-frontend
git add src/constants.js
git commit -m "update runtimes: drop deprecated, add Python 3.14/Node 24.x/Java 25/.NET, fix runtime IDs"
git push
npm run build
```

## 7. Smoke test

| # | Test | Expected |
|---|------|----------|
| 1 | Submit Python 3.14 request with `james.shapiro@gmail.com` | Layer builds, email arrives |
| 2 | Click publish pill in email | Layer published as `<name>-lf` |
| 3 | `aws lambda list-layer-versions --layer-name <name>-lf --region us-east-1` | Layer version exists |
| 4 | Submit Ruby 3.4 request (e.g. `nokogiri`) | Layer builds with `gem install`, email arrives |
| 5 | Submit Node.js 22.x request (e.g. `lodash`) | Layer builds with `npm install`, email arrives |
| 6 | Submit Java 21 request (e.g. `com.google.guava:guava:33.0.0-jre`) | Layer builds with Maven, email arrives |
| 7 | Submit request with a different email, click publish | Layer published as `<name>-layer-factory` |
| 8 | Select Go/Rust/C++/.NET and submit | Clear error: "Unsupported language for layer building" |
| 9 | Verify Python 3.9 and Node.js 18.x no longer appear in dropdown | Removed from UI |
| 10 | Verify .NET 8/9/10 and Java 25 appear in dropdowns | New options visible |
