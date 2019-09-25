FROM python:3.7
ADD . /src
RUN pip install kopf kubernetes boto3 pyyaml
CMD kopf run /src/group_members.py --verbose