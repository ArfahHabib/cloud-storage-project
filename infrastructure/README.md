# Infrastructure — AWS CDK (All Members)

This folder deploys ALL AWS resources automatically.
Instead of clicking in the console, run ONE command and everything is created.

## First-time setup
```bash
cd infrastructure
pip install -r requirements.txt
npm install -g aws-cdk
cdk bootstrap   # only needed once per AWS account
```

## Deploy everything
```bash
cdk deploy
```

After deploy, the terminal prints:
```
Outputs:
  CloudStorageStack.UserPoolId       = us-east-1_xxxxxxx
  CloudStorageStack.UserPoolClientId = xxxxxxxxxxxxxxxxx
  CloudStorageStack.KmsKeyId         = xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

Copy these values into your root `.env` file.

## Destroy everything (clean up to avoid AWS charges)
```bash
cdk destroy
```
Note: Buckets and DynamoDB are set to RETAIN — delete them manually in the console to avoid lingering charges.