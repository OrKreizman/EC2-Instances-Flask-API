# -----------------------------------imports---------------------------------------------------------
import json
import os
import boto3
from flask import Flask, jsonify, request
from flask_caching import Cache

# -----------------------------------constants------------------------------------------------------
instance_tags = {'Name', 'ID', 'Type', 'State', 'AvailabilityZone', 'PublicIP', 'PrivateIPs'}
INVALID_REGION_MESSAGE = 'Invalid region name'
INVALID_SORT_BY_MESSAGE = f"Invalid sort by attribute.\nValid attributes to short by are:{', '.join(instance_tags)}"
INVALID_PAGE_SIZE = "Invalid page size.\nPage size must be positive numbers"
INVALID_PAGE_NUM = "Invalid page numbers."

# --------------------------creating flask app----------------------------------------
app = Flask(__name__)
app.config.from_mapping({'CACHE_TYPE': 'SimpleCache', 'CACHE_THRESHOLD': 1000})
cache = Cache(app)


def http_error(text: str):
    """
    Return json with error and exitcode
    :param text: Error message
    :return: Json indicates an error , exit code
    """
    return jsonify({'error': text}), 400


def is_valid_sort_by(sort_by: str):
    """
    Check if tag to sort_by is valid
    :param sort_by: Tag to sort by
    :return: None for valid sort_by tag, error data for invalid
    """
    if sort_by not in instance_tags and sort_by:
        return http_error(INVALID_SORT_BY_MESSAGE)


def is_valid_page_size(page_size: int):
    """
    Check if page size is valid
    :param page_size: Number of instances to show on each page
    :return: None for valid sort_by tag, error data for invalid
    """
    if page_size <= 0:
        return http_error(INVALID_PAGE_SIZE)


def is_valid_region(region_name: str):
    """
    Check if region is valid
    :param region_name: Name of the region
    :return: None for valid sort_by tag, error data for invalid
    """
    tmp_ec2_client = boto3.client('ec2', region_name='eu-west-1')
    valid_regions = set(region['RegionName'] for region in tmp_ec2_client.describe_regions()['Regions'])
    return http_error(INVALID_REGION_MESSAGE) if region_name not in valid_regions else None


def check_parameters_validation(region_name: str, sort_by: str, page_size: int):
    """
    Check if given parameters are valid
    :param region_name: Region name
    :param sort_by: Tag to sort by instances
    :param page_size: Number of page
    :return: None for Valid sort_by tag, error data for invalid
    """
    valid_region = is_valid_region(region_name)
    if valid_region: return valid_region
    valid_sort_by = is_valid_sort_by(sort_by)
    if valid_sort_by: return valid_sort_by
    valid_page_size = is_valid_page_size(page_size)
    if valid_page_size: return valid_page_size


@cache.memoize(200)
def get_all_ec2_instances_in_region(region_name: str, sort_by: str = None):
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


@app.route('/get_ec2_instances', methods=['GET'])
def get_request_ec2_instances():
    """
    Handle Get request.
    :return: list of instances from region, sorted by sort_by, paged by page, page_size.
    """
    # get arguments
    region = request.args.get('region')
    sort_by = request.args.get('sort_by', None)
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 5))

    # check parameters
    is_valid_response = check_parameters_validation(region, sort_by, page_size)
    if is_valid_response is not None:
        return is_valid_response

    # find relevant indices of instances to return
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    # get instances for region and paging
    instances = get_all_ec2_instances_in_region(region, sort_by)[start_index:end_index]

    json_data = json.dumps(instances, indent=4)
    return json_data, {'Content-Type': 'application/json; charset=utf-8'}


if __name__ == '__main__':
    access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
    secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    boto3.Session(aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key)
    app.run(host='127.0.0.1', debug=True)
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
