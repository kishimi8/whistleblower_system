from import_export import resources, results
from .models import Report

class Reportresource(resources.ModelResource):
    class Meta:
        model = Report