from rest_framework import serializers
from .models import Manufacturer, Team, Tank, UpgradePath, TeamTank


class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = ['id', 'name']


class TankSerializer(serializers.ModelSerializer):
    manufacturers = ManufacturerSerializer(many=True, read_only=True)

    class Meta:
        model = Tank
        fields = ['id', 'name', 'battle_rating', 'price', 'manufacturers']


class UpgradePathSerializer(serializers.ModelSerializer):
    from_tank = TankSerializer(read_only=True)
    to_tank = TankSerializer(read_only=True)

    class Meta:
        model = UpgradePath
        fields = ['id', 'from_tank', 'to_tank', 'required_kit_tier', 'cost']


class TeamSerializer(serializers.ModelSerializer):
    manufacturers = ManufacturerSerializer(many=True, read_only=True)
    tanks = TankSerializer(many=True, read_only=True, source='tanks.all')
    upgrade_kits = serializers.JSONField(required=False)

    class Meta:
        model = Team
        fields = ['id', 'name', 'balance', 'manufacturers', 'tanks', 'upgrade_kits']
