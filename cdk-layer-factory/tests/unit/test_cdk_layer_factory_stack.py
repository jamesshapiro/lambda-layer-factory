import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk_layer_factory.cdk_layer_factory_stack import CdkLayerFactoryStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk_layer_factory/cdk_layer_factory_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CdkLayerFactoryStack(app, "cdk-layer-factory")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
