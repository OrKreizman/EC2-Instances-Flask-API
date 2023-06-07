# CiscoAssignment

# EC2 Instances Flask API

This project implements a Flask API to retrieve information about EC2 instances in a specific AWS region.

## Prerequisites

Before running this project, make sure you have the following:

- Python 3.7 installed
- AWS credentials with access to the EC2 service

## Installation

1. Clone the repository:

```bash
git clone https://github.com/OrKreizman/CiscoAssignment.git
```

2. Navigate to the project directory:

```bash
cd EC2-Instances-Flask-API
```

3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

4. Set up your AWS credentials:

Make sure you have your AWS access key ID and secret access key. You can set them as environment variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`, or modify the `access_key_id` and `secret_access_key` variables in the `__main__` block of the `EC2Instances.py` file.

## Usage

To run the Flask API and retrieve information about EC2 instances, follow these steps:

1. Start the Flask server:

```bash
python EC2Instances.py
```

2. Open your web browser and navigate to `http://127.0.0.1:5000/get_ec2_instances`.

3. Make a GET request to retrieve the EC2 instances. You can provide the following query parameters:

- `region`: The AWS region name (e.g., `us-west-2`).
- `sort_by`: The attribute to sort the instances by (optional).
- `page`: The page number for pagination (optional, default is 1).
- `page_size`: The number of instances to show per page (optional, default is 5).

Example request: `http://127.0.0.1:5000/get_ec2_instances?region=us-west-2&sort_by=Name&page=1&page_size=10`

The API will return a JSON response containing the EC2 instances in the specified region, sorted by the specified attribute (if provided), and paginated according to the page and page size.
