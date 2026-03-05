#!/bin/bash
set -e

echo "=== Step 1: Bust the nokogiri cache ==="
cd ~/code/lambda-layer-factory/playbooks/test/07-uv-env
uv run 07-bust-cache-and-retest.py nokogiri

echo ""
echo "=== Step 2: Redeploy latest Lambda code ==="
cd ~/code/lambda-layer-factory/playbooks/deployment
bash 08-redeploy-playbook.sh

echo ""
echo "=== Done! ==="
echo "Submit a Ruby 3.3 / nokogiri build via demo.lambdalayerfactory.com"
echo ""
echo "Then check logs with:"
echo "  aws s3 ls s3://layer-factory/logs/ | grep nokogiri | sort -k1,2 | tail -5"
echo "  aws s3 cp \"\$(aws s3 ls s3://layer-factory/logs/ | grep nokogiri | sort -k1,2 | tail -1 | awk '{print \"s3://layer-factory/logs/\"\$4}')\" /tmp/build.log && cat /tmp/build.log"
