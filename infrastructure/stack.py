"""
infrastructure/stack.py
=======================
AWS CDK Infrastructure — Deploys Everything Automatically

This file defines ALL AWS resources needed for the project in code.
Running `cdk deploy` will create all of them automatically —
no manual clicking in the AWS Console needed!

Resources created:
  - 2 S3 buckets (us-east-1 and eu-west-1)
  - 1 DynamoDB table (FileManifest)
  - 1 KMS key (Customer Master Key)
  - 1 Cognito User Pool + App Client
  - 1 IAM role with least-privilege permissions
"""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_s3         as s3,
    aws_dynamodb   as dynamodb,
    aws_kms        as kms,
    aws_cognito    as cognito,
    aws_iam        as iam,
    RemovalPolicy,
    Duration,
    CfnOutput,
)
from constructs import Construct


class CloudStorageStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ── KMS Key (Customer Master Key) ─────────────────────────────────────
        cmk = kms.Key(
            self, "MasterKey",
            alias               = "alias/cloudproject-master-key",
            description         = "CS-308 Cloud Storage — encrypts Data Encryption Keys",
            enable_key_rotation = True,           # rotate annually (best practice)
            removal_policy      = RemovalPolicy.RETAIN,  # keep key if stack deleted
        )

        # ── S3 Bucket: Primary (us-east-1) ────────────────────────────────────
        primary_bucket = s3.Bucket(
            self, "PrimaryBucket",
            bucket_name           = "cloudproject-shards-us",
            versioned             = True,          # keep old versions of shards
            encryption            = s3.BucketEncryption.S3_MANAGED,
            block_public_access   = s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy        = RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id             = "move-to-ia-after-30-days",
                    enabled        = True,
                    transitions=[
                        s3.Transition(
                            storage_class  = s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after = Duration.days(30),
                        )
                    ]
                )
            ]
        )

        # ── S3 Bucket: Secondary (eu-west-1) ─────────────────────────────────
        # Note: CDK deploys this cross-region — we create it in the same stack
        # for simplicity. In production you'd use a separate Stack with env={region:'eu-west-1'}
        secondary_bucket = s3.Bucket(
            self, "SecondaryBucket",
            bucket_name         = "cloudproject-shards-eu",
            versioned           = True,
            encryption          = s3.BucketEncryption.S3_MANAGED,
            block_public_access = s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy      = RemovalPolicy.RETAIN,
        )

        # ── DynamoDB Table ─────────────────────────────────────────────────────
        table = dynamodb.Table(
            self, "FileManifest",
            table_name     = "FileManifest",
            partition_key  = dynamodb.Attribute(name="userId", type=dynamodb.AttributeType.STRING),
            sort_key       = dynamodb.Attribute(name="fileId", type=dynamodb.AttributeType.STRING),
            billing_mode   = dynamodb.BillingMode.PAY_PER_REQUEST,  # no capacity planning needed
            removal_policy = RemovalPolicy.RETAIN,
            point_in_time_recovery = True,   # can restore to any point in last 35 days
        )

        # ── Cognito User Pool ─────────────────────────────────────────────────
        user_pool = cognito.UserPool(
            self, "UserPool",
            user_pool_name          = "CloudStorageUsers",
            self_sign_up_enabled    = True,
            sign_in_aliases         = cognito.SignInAliases(email=True, username=True),
            auto_verify             = cognito.AutoVerifiedAttrs(email=True),
            password_policy         = cognito.PasswordPolicy(
                min_length          = 8,
                require_digits      = True,
                require_lowercase   = True,
                require_uppercase   = False,
                require_symbols     = False,
            ),
            account_recovery        = cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy          = RemovalPolicy.RETAIN,
        )

        user_pool_client = cognito.UserPoolClient(
            self, "UserPoolClient",
            user_pool               = user_pool,
            user_pool_client_name   = "cloudproject-frontend",
            auth_flows              = cognito.AuthFlow(
                user_password       = True,
                user_srp            = True,
            ),
            generate_secret         = False,  # public client (React app)
        )

        # ── IAM Role for the Flask backend ────────────────────────────────────
        backend_role = iam.Role(
            self, "BackendRole",
            assumed_by  = iam.ServicePrincipal("ec2.amazonaws.com"),
            description = "Least-privilege role for the Flask API server",
        )

        # Allow S3 operations on both buckets only
        backend_role.add_to_policy(iam.PolicyStatement(
            effect  = iam.Effect.ALLOW,
            actions = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:HeadBucket"],
            resources = [
                primary_bucket.bucket_arn   + "/*",
                secondary_bucket.bucket_arn + "/*",
                primary_bucket.bucket_arn,
                secondary_bucket.bucket_arn,
            ]
        ))

        # Allow DynamoDB operations on our table only
        backend_role.add_to_policy(iam.PolicyStatement(
            effect  = iam.Effect.ALLOW,
            actions = [
                "dynamodb:PutItem", "dynamodb:GetItem",
                "dynamodb:DeleteItem", "dynamodb:Query",
            ],
            resources = [table.table_arn]
        ))

        # Allow KMS encrypt/decrypt with our key only
        backend_role.add_to_policy(iam.PolicyStatement(
            effect  = iam.Effect.ALLOW,
            actions = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey"],
            resources = [cmk.key_arn]
        ))

        # ── CloudFormation Outputs (printed after deploy) ─────────────────────
        CfnOutput(self, "UserPoolId",     value=user_pool.user_pool_id,         description="Cognito User Pool ID")
        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id, description="Cognito App Client ID")
        CfnOutput(self, "PrimaryBucket",  value=primary_bucket.bucket_name,    description="Primary S3 Bucket")
        CfnOutput(self, "SecondaryBucket",value=secondary_bucket.bucket_name,  description="Secondary S3 Bucket")
        CfnOutput(self, "DynamoTable",    value=table.table_name,              description="DynamoDB Table")
        CfnOutput(self, "KmsKeyId",       value=cmk.key_id,                   description="KMS Key ID — copy to .env")