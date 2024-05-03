sudo yum update -y
sudo yum search docker
sudo yum install docker -y
sudo systemctl enable docker.service
sudo systemctl start docker.service
sudo systemctl status docker.service

echo "ulid-py==1.1.0" >> requirements.txt
mkdir -p "python/lib/python3.9/site-packages/"
mkdir -p "python/lib/python3.10/site-packages/"
mkdir -p "python/lib/python3.11/site-packages/"
mkdir -p "python/lib/python3.12/site-packages/"

sudo su

docker run -v "$PWD":/var/task "public.ecr.aws/sam/build-python3.9" /bin/sh -c "pip install -r requirements.txt -t python/lib/python3.9/site-packages/; exit"
docker run -v "$PWD":/var/task "public.ecr.aws/sam/build-python3.10" /bin/sh -c "pip install -r requirements.txt -t python/lib/python3.10/site-packages/; exit"
docker run -v "$PWD":/var/task "public.ecr.aws/sam/build-python3.11" /bin/sh -c "pip install -r requirements.txt -t python/lib/python3.11/site-packages/; exit"
docker run -v "$PWD":/var/task "public.ecr.aws/sam/build-python3.12" /bin/sh -c "pip install -r requirements.txt -t python/lib/python3.12/site-packages/; exit"

zip -r ulid-archive.zip python > /dev/null
aws s3 cp ulid-archive.zip s3://athens-lambda-layers

aws lambda publish-layer-version --layer-name ulid-layer --description "ULID Layer" --zip-file fileb://ulid-archive.zip --compatible-runtimes "python3.9" "python3.10" "python3.11" "python3.12" --region "us-east-1"
