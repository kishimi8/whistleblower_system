import diagrams
from diagrams import Diagram
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB
with Diagram("Simple AWS Web Service", show=False):
   ELB("Load Balancer") >> EC2("Web Server") >> RDS("Database")