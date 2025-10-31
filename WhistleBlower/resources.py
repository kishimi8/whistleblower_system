from import_export import resources, results
from .models import Report

class reportResource(resources.ModelResource):
    class Meta:
        model = Report