import os
import unittest

import boto3
import EC2Instances
import requests
from moto import mock_ec2


class EC2WebServerIntegration(unittest.TestCase):

    def get_all_ec2_instances_in_region(self, region_name: str, sort_by: str = None):
        ec2_client = boto3.client('ec2', region_name=region_name)
        response = ec2_client.describe_instances()['Reservations']
        instances = list()
        for reservation in response:
            for instance in reservation['Instances']:
                # Extract desired attributes (name, id, type, state, az, public IP, private IPs)
                instance_details = {
                    'Name': instance.get('Tags')[0]['Value'],
                    'ID': instance['InstanceId'],
                    'Type': instance['InstanceType'],
                    'State': instance['State']['Name'],
                    'AvailabilityZone': instance['Placement']['AvailabilityZone'],
                    'PublicIP': instance.get('PublicIpAddress', 'N/A'),
                    'PrivateIPs': [private_ip['PrivateIpAddress'] for private_ip in instance['NetworkInterfaces']]
                }
                instances.append(instance_details)
        if sort_by: instances.sort(key=lambda x: x[sort_by])
        return instances

    def test_web_server(self):
        access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
        secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        boto3.Session(aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key)
        region = "eu-west-1"
        url = f"http://52.211.88.229/get_ec2_instances?region={region}"
        response = requests.get(url)
        # Check the status code of the response
        self.assertEqual(response.status_code, 200,
                         "Test failed: Request failed with status code {response.status_code}")
        expected_result = self.get_all_ec2_instances_in_region(region)
        self.assertEqual(response.json(), expected_result, "Web server returned an unexpected response")


class EC2InstancesTestCase(unittest.TestCase):
    def setUp(self):
        # Perform any setup actions before each test case
        # For example, create an instance of your EC2 class or set up a test environment
        self.region = 'eu-west-1'
        self.client = boto3.client('ec2', region_name=self.region)
        self.ec2 = boto3.resource('ec2', self.region)
        self.app = EC2Instances.app
        self.app_test = self.app.test_client()

        # self.app.config.update({"TESTING": True}

    def create_instance(self, name: str):
        image_response = self.client.describe_images()
        image_id = image_response['Images'][0]['ImageId']
        self.ec2.create_instances(ImageId=image_id, MinCount=1, MaxCount=1, TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': name
                    },
                ]
            }])

    @mock_ec2
    def test_instance_exists(self):
        """
        Create an EC2 instance and Test if exists in the specified region
        :return:
        """
        self.create_instance(name="TestInstanceExistsInstance")
        instances = EC2Instances.get_all_ec2_instances_in_region(self.region, None)
        self.assertEqual(len(instances), 1, "No instances found in the region")

    @mock_ec2
    def test_instance_properties(self):
        # Test specific properties of the EC2 instance
        self.create_instance(name="MyFirstInstance")
        instances = EC2Instances.get_all_ec2_instances_in_region(self.region)
        instance_tags = {'Name', 'ID', 'Type', 'State', 'AvailabilityZone', 'PublicIP', 'PrivateIPs'}
        for instance in instances:
            for tag in instance_tags:
                self.assertIsNotNone(instance.get(tag), f"Instance {tag} is missing")

    @mock_ec2
    def test_sorting(self):
        """Test that instances returned sorted according to sort_by attribute"""
        self.create_instance(name="A_Instance")
        self.create_instance(name="B_Instance")
        self.create_instance(name="C_Instance")
        instances = EC2Instances.get_all_ec2_instances_in_region(self.region, sort_by='Name')
        self.assertEqual(instances[0]['Name'], "A_Instance")
        self.assertEqual(instances[1]['Name'], "B_Instance")
        self.assertEqual(instances[2]['Name'], "C_Instance")

    # start testing the app
    @mock_ec2
    def test_empty_result(self):
        empty_result = self.app_test.get('/get_ec2_instances',
                                         query_string=dict(region=self.region))
        self.assertEqual(empty_result.status_code, 200)
        self.assertListEqual(empty_result.json, [])

    @mock_ec2
    def test_paging(self):
        self.create_instance(name="MyFirstInstance")
        self.create_instance(name="MySecondInstance")
        page_size = 1
        instances = self.app_test.get('/get_ec2_instances', query_string=dict(region=self.region)).json
        page_one_instances = self.app_test.get('/get_ec2_instances',
                                               query_string=dict(region=self.region, page_size=page_size, page=1)).json
        page_two_instances = self.app_test.get('/get_ec2_instances',
                                               query_string=dict(region=self.region, page_size=page_size, page=2)).json
        self.assertEqual(2, len(instances))
        self.assertListEqual(instances, page_one_instances + page_two_instances)

    @mock_ec2
    def test_invalid_region(self):
        invalid_result_status = self.app_test.get('/get_ec2_instances',
                                                  query_string=dict(region="Invalid name")).status_code
        self.assertEqual(invalid_result_status, 400)

    @mock_ec2
    def test_missing_region(self):
        invalid_result_status = self.app_test.get('/get_ec2_instances',
                                                  query_string=dict()).status_code
        self.assertEqual(invalid_result_status, 400)

    @mock_ec2
    def test_invalid_page_size(self):
        invalid_result_status = self.app_test.get('/get_ec2_instances',
                                                  query_string=dict(region=self.region, page_size=0)).status_code
        self.assertEqual(invalid_result_status, 400)

    # def test_out_of_limit_page(self):


if __name__ == '__main__':
    unittest.main()
