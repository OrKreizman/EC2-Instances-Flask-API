import os
import unittest

import boto3
import EC2Instances
import requests
from moto import mock_ec2


class EC2WebServerIntegration(unittest.TestCase):
    """
    Integration test:
    Test if the web server return the expected result to a get request.
    important: Make sure you have your AWS access key ID and secret access key.
        You can set them as environment variables AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
    """

    def get_all_ec2_instances_in_region(self, region_name: str, sort_by: str = None):
        """
            Get all ec2 instances in specific region
            :param region_name: Region name
            :param sort_by: Tag to use to sort instances by
            :return: List of all ec2 instances in specific region
        """
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
        """
        Test that the server return right answer with the right status code for a request
        :return: None
        """
        access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
        secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        boto3.Session(aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key)
        region = "eu-west-1"
        url = f"http://52.211.88.229/get_ec2_instances?region={region}"
        response = requests.get(url)
        self.assertEqual(response.status_code, 200,
                         "Test failed: Request failed with status code {response.status_code}")
        expected_result = self.get_all_ec2_instances_in_region(region)
        self.assertEqual(response.json(), expected_result, "Web server returned an unexpected response")


class EC2InstancesTestCase(unittest.TestCase):
    """
    Test EC2Instance including get requests and main functions
    imported: in order to run the test you need to disable caching
    """

    def setUp(self):
        self.region = 'eu-west-1'
        self.client = boto3.client('ec2', region_name=self.region)
        self.ec2 = boto3.resource('ec2', self.region)
        self.app = EC2Instances.app
        self.app_test = self.app.test_client()

    def create_instance(self, name: str):
        """
        create ec2 instance (using mock ec2 session)
        :param name: Name of the wanted EC2 instance
        :return: None
        """
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
        """
        Test that get_all_ec2_instances_in_region returns all wanted tags
        :return: None
        """
        self.create_instance(name="MyFirstInstance")
        instances = EC2Instances.get_all_ec2_instances_in_region(self.region)
        instance_tags = {'Name', 'ID', 'Type', 'State', 'AvailabilityZone', 'PublicIP', 'PrivateIPs'}
        for instance in instances:
            for tag in instance_tags:
                self.assertIsNotNone(instance.get(tag), f"Instance {tag} is missing")

    @mock_ec2
    def test_sorting(self):
        """
        Test that instances returned sorted according to sort_by attribute
        :return: None
        """
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
        """
        Test that get request with no active instances return empty list.
        :return:
        """
        empty_result = self.app_test.get('/get_ec2_instances',
                                         query_string=dict(region=self.region))
        self.assertEqual(empty_result.status_code, 200)
        self.assertListEqual(empty_result.json, [])

    @mock_ec2
    def test_paging(self):
        """
        Test that the paging process works as expected -
        (connecting two pages results and compare them with the expected result without paging.
        :return:
        """
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
        """
        Test that in case of invalid region the returned status code is 400
        :return:
        """
        invalid_result_status = self.app_test.get('/get_ec2_instances',
                                                  query_string=dict(region="Invalid name")).status_code
        self.assertEqual(invalid_result_status, 400)

    @mock_ec2
    def test_missing_region(self):
        """
        Test that in case of missing region the returned status code is 400
        :return:
        """
        invalid_result_status = self.app_test.get('/get_ec2_instances',
                                                  query_string=dict()).status_code
        self.assertEqual(invalid_result_status, 400)

    @mock_ec2
    def test_invalid_page_size(self):
        """
        Test that in case of invalid page size the returned status code is 400
        :return:
        """
        invalid_result_status = self.app_test.get('/get_ec2_instances',
                                                  query_string=dict(region=self.region, page_size=0)).status_code
        self.assertEqual(invalid_result_status, 400)


if __name__ == '__main__':
    unittest.main()
