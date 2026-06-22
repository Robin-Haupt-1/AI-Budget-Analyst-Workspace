from rest_framework import viewsets
from .models import Scenario, LineItem
from .serializers import ScenarioSerializer, LineItemSerializer


class ScenarioViewSet(viewsets.ModelViewSet):
    queryset = Scenario.objects.prefetch_related("line_items").all()
    serializer_class = ScenarioSerializer


class LineItemViewSet(viewsets.ModelViewSet):
    serializer_class = LineItemSerializer

    def get_queryset(self):
        qs = LineItem.objects.all()
        scenario_id = self.request.query_params.get("scenario")
        return qs.filter(scenario_id=scenario_id) if scenario_id else qs
