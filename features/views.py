from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from features.models import (
    UserEngagementMetrics,
    ErrorAnalysisLog,
    KnowledgeGraphMetrics,
    SpacedRepetitionLog,
    Concept
)
from features.system_metrics import SystemMetricsAggregator

# @staff_member_required  # Disabled for easier testing, re-enable for prod
def patent_admin_dashboard(request):
    """
    Renders the 6-part Admin Dashboard required for the patent filing.
    """
    return render(request, 'features/admin_dashboard.html')

def api_dashboard_data(request):
    """
    Provides the JSON data for Chart.js and vis.js to consume.
    """
    user_id = request.user.id if request.user.is_authenticated else 1
    
    # 1. Engagement Data
    eng_logs = UserEngagementMetrics.objects.all().order_by('-timestamp')[:50]
    engagement_data = {
        'timestamps': [log.timestamp.strftime('%H:%M') for log in reversed(eng_logs)],
        'scores': [float(log.engagement_score or 0) for log in reversed(eng_logs)],
        'loads': [float(log.load_variable_L or 0) for log in reversed(eng_logs)],
    }
    
    # 2. Error Analysis Efficiency
    efficiency = SystemMetricsAggregator.calculate_platform_efficiency()
    
    # 3. Knowledge Graph Data (vis.js format)
    nodes = []
    edges = []
    for kg in KnowledgeGraphMetrics.objects.all():
        color_hex = "#ff4444" if kg.node_color == 'RED' else "#ffbb33" if kg.node_color == 'YELLOW' else "#00C851"
        nodes.append({
            'id': kg.concept.id,
            'label': kg.concept.name,
            'color': color_hex,
            'value': kg.mastery_percent
        })
        
        for prereq in kg.concept.prerequisites.all():
            edges.append({
                'from': prereq.id,
                'to': kg.concept.id,
                'arrows': 'to'
            })
            
    # Fallback mock data if DB is empty
    if not nodes:
        nodes = [
            {'id': 1, 'label': 'Basic Physics', 'color': '#00C851', 'value': 85},
            {'id': 2, 'label': 'Kinematics', 'color': '#ffbb33', 'value': 55},
            {'id': 3, 'label': 'Newton Laws', 'color': '#ff4444', 'value': 20},
        ]
        edges = [
            {'from': 1, 'to': 2, 'arrows': 'to'},
            {'from': 2, 'to': 3, 'arrows': 'to'}
        ]

    # 4. System Metrics
    system_metrics = SystemMetricsAggregator.get_dashboard_summary(user_id)
    
    return JsonResponse({
        'engagement': engagement_data,
        'efficiency': efficiency,
        'knowledge_graph': {'nodes': nodes, 'edges': edges},
        'system': system_metrics
    })
