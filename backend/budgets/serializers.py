from rest_framework import serializers
from .models import Scenario, LineItem


class LineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineItem
        fields = ["id", "scenario", "department", "category",
                  "budget_amount", "actual_amount", "notes"]


class ScenarioSerializer(serializers.ModelSerializer):
    line_items = LineItemSerializer(many=True, read_only=True)

    class Meta:
        model = Scenario
        fields = ["id", "name", "period", "description", "created_at", "line_items"]
