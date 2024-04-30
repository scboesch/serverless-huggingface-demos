"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import os
from pathlib import Path
from constructs import Construct
from aws_cdk import App, Stack, Duration, RemovalPolicy, Tags
from aws_cdk import (
    aws_lambda as lambda_,
    aws_efs as efs,
    aws_ec2 as ec2,
    aws_apigateway as apigateway
)


class ServerlessHuggingFaceDemoStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # EFS needs to be setup in a VPC
        vpc = ec2.Vpc(self, 'Vpc', max_azs=2)

        # Creates a file system in EFS to store cache models
        fs = efs.FileSystem(self, 'FileSystem',
                            vpc=vpc,
                            removal_policy=RemovalPolicy.DESTROY)
        access_point = fs.add_access_point('MLAccessPoint',
                                           create_acl=efs.Acl(
                                               owner_gid='1001', owner_uid='1001', permissions='750'),
                                           path="/export/models",
                                           posix_user=efs.PosixUser(gid="1001", uid="1001"))

        # Iterates through the Python files in the docker directory
        docker_folder = os.path.dirname(os.path.realpath(__file__)) + "/inference"
        pathlist = Path(docker_folder).rglob('*.py')

        # We need to keep a list of the Docker Lambda functions to add pemissions for the router lambda.
        docker_lambdas = []
        count = 0

        # Will will collect the ARNs of the Docker Lambdas to pass to the router lambda's environment.
        passed_environment_variables = {}

        for path in pathlist:
            count += 1
            base = os.path.basename(path)
            filename = os.path.splitext(base)[0]
            # Lambda Function from docker image
            docker_lambda = lambda_.DockerImageFunction(
                self, filename,
                code=lambda_.DockerImageCode.from_image_asset(docker_folder,
                                                              cmd=[
                                                                  filename+".handler"]
                                                              ),
                memory_size=3000,
                timeout=Duration.seconds(600),
                vpc=vpc,
                filesystem=lambda_.FileSystem.from_efs_access_point(access_point, '/mnt/hf_models_cache'),
                environment={"TRANSFORMERS_CACHE": "/mnt/hf_models_cache"},
            )
            # Save the ARN of each Docker Lambda Function to pass to the router lambda
            passed_environment_variables["functionARN"+str(count)] = docker_lambda.function_arn
            docker_lambdas.append(docker_lambda)
        passed_environment_variables["functionCount"] = str(count)
        passed_environment_variables["secret_region"] = os.environ["CDK_DEFAULT_REGION"]

        # Lambda Function to route requests to the Docker Lambda Functions
        self.router_lambda = lambda_.Function(
            scope=self,
            id="LambdaRouter",
            runtime=lambda_.Runtime.PYTHON_3_12,
            function_name="LambdaRouter",
            code=lambda_.Code.from_asset(
                path="lambda"
            ),
            handler="router.handler",
            # The environment variables for the Lambda function are passed here.
            environment=passed_environment_variables,
        )

        # API Gateway to provide a public endpoint for the router Lambda Function
        api = apigateway.LambdaRestApi(
            self,
            "LambdaRouterApi",
            handler = self.router_lambda,
            proxy = False,
        )
        api_resource = api.root.add_resource("go")
        api_resource.add_method("GET")
        api_resource.add_method("POST")

        # Grant invoke permissions to the router lambda
        for docker_lambda in docker_lambdas:
            docker_lambda.grant_invoke(self.router_lambda)
            

app = App()

stack = ServerlessHuggingFaceDemoStack(app, "ServerlessHuggingFaceDemoStack")
Tags.of(stack).add("AwsSample", "ServerlessHuggingFaceDemo")

app.synth()
