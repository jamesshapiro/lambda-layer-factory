# Prompt Log

## Refactor Request - 2026-03-04

I want to completely refactor this application so that instead of CDK it gets deployed via my standard terragrunt workflow (see `/home/james/code/terragrunt-infrastructure-live/athens/us-east-1/default/video-player-upload-pipeline` and `/home/james/code/terragrunt-infrastructure-modules/video-processing-pipeline` for a working example from another project). I also need to support all of the latest Python versions as well, along with every other major language supported by Lambda. We also need to update the code for the frontend, which lives in the `/home/james/code/lambda-layer-factory-frontend` directory. Also, I want to restyle it to Japanese / Anthropic inspired. See the about.html page styling in `/home/james/code/tic-tac-toe` to see what I'm getting at.
