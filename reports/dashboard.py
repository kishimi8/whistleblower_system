from django.utils.translation import gettext_lazy as _
from .models import Report
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

def dashboard_callback(request, context):
    # KPIs
    total_reports = Report.objects.count()
    new_reports = Report.objects.filter(status='new').count()
    closed_reports = Report.objects.filter(status='closed').count()
    
    # Weekly Trend Data (Last 7 days)
    today = timezone.now().date()
    last_week = today - timedelta(days=7)
    
    daily_stats = (
        Report.objects.filter(created_at__date__gte=last_week)
        .values('created_at__date')
        .annotate(count=Count('id'))
        .order_by('created_at__date')
    )
    
    # Format data for chart
    dates = [str(day['created_at__date']) for day in daily_stats]
    counts = [day['count'] for day in daily_stats]
    
    # Status Distribution
    status_stats = Report.objects.values('status').annotate(count=Count('id'))
    status_labels = [stat['status'].replace('_', ' ').title() for stat in status_stats]
    status_data = [stat['count'] for stat in status_stats]

    context.update({
        "kpi": [
            {
                "title": _("Total Reports"),
                "metric": total_reports,
                "footer": _("All time"),
            },
            {
                "title": _("New Reports"),
                "metric": new_reports,
                "footer": _("Action required"),
            },
             {
                "title": _("Closed Cases"),
                "metric": closed_reports,
                "footer": _("Resolved"),
            },
        ],
        "charts": [
            {
                "title": _("Submissions Over Time"),
                "type": "line",
                "data": {
                    "labels": dates,
                    "datasets": [
                        {
                            "label": _("New Reports"),
                            "data": counts,
                            "borderColor": "#3b82f6",
                            "backgroundColor": "rgba(59, 130, 246, 0.1)",
                        }
                    ],
                },
            },
            {
                "title": _("Case Status Distribution"),
                "type": "doughnut",
                "data": {
                    "labels": status_labels,
                    "datasets": [
                        {
                            "data": status_data,
                            "backgroundColor": [
                                "#3b82f6", # Blue
                                "#fbbf24", # Amber
                                "#10b981", # Emerald
                                "#ef4444", # Red
                            ],
                        }
                    ],
                },
            },
        ]
    })
    return context
