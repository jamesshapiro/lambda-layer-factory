sudo yum update -y
sudo yum search docker
sudo yum install docker -y
sudo systemctl enable docker.service
sudo systemctl start docker.service
sudo systemctl status docker.service

echo "ulid-py==1.1.0" >> requirements.txt
mkdir -p "python/lib/python3.6/site-packages/"
mkdir -p "python/lib/python3.7/site-packages/"
mkdir -p "python/lib/python3.8/site-packages/"
mkdir -p "python/lib/python3.9/site-packages/"

sudo su

docker run -v "$PWD":/var/task "public.ecr.aws/sam/build-python3.6" /bin/sh -c "pip install -r requirements.txt -t python/lib/python3.6/site-packages/; exit"
docker run -v "$PWD":/var/task "public.ecr.aws/sam/build-python3.7" /bin/sh -c "pip install -r requirements.txt -t python/lib/python3.7/site-packages/; exit"
docker run -v "$PWD":/var/task "public.ecr.aws/sam/build-python3.8" /bin/sh -c "pip install -r requirements.txt -t python/lib/python3.8/site-packages/; exit"
docker run -v "$PWD":/var/task "public.ecr.aws/sam/build-python3.9" /bin/sh -c "pip install -r requirements.txt -t python/lib/python3.9/site-packages/; exit"

zip -r ulid-archive.zip python > /dev/null
aws s3 cp ulid-archive.zip s3://athens-lambda-layers

aws lambda publish-layer-version --layer-name ulid-layer --description "ULID Layer" --zip-file fileb://ulid-archive.zip --compatible-runtimes "python3.6" "python3.7" "python3.8" "python3.9" --region "us-east-1"
