#!/usr/bin/env python3
import aws_cdk as cdk

from cdk_layer_factory.cdk_layer_factory_stack import CdkLayerFactoryStack

app = cdk.App()
my_stack = CdkLayerFactoryStack(app, "LayerFactory",
    env={'region': 'us-east-1'}
)

app.synth()
