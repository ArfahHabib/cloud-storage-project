#!/usr/bin/env python3
"""
infrastructure/app.py
Entry point for AWS CDK.
Run: cdk deploy
"""
import aws_cdk as cdk
from stack import CloudStorageStack

app = cdk.App()

CloudStorageStack(
    app, "CloudStorageStack",
    env=cdk.Environment(
        account=None,   # uses AWS_ACCOUNT_ID env variable or ~/.aws/config
        region="us-east-1"
    ),
    description="CS-308 Cloud Computing — Decentralized Privacy-First Storage"
)

app.synth()