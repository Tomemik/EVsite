from rest_framework import serializers
from .models import Manufacturer, Team, Tank, UpgradePath, TeamTank, Match, TeamMatch, Substitute, MatchResult, \
    TankLost, TeamResult


class TankSerializerSlim(serializers.ModelSerializer):
    class Meta:
        model = Tank
        fields = ['name']


class TankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tank
        fields = ['id', 'name', 'battle_rating', 'price', 'rank', 'type']


class ManufacturerSerializer(serializers.ModelSerializer):
    tanks = TankSerializer(many=True, read_only=True)

    class Meta:
        model = Manufacturer
        fields = ['id', 'name', 'tanks']


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


class TeamMatchSerializer(serializers.ModelSerializer):
    tanks = TankSerializerSlim(many=True)
    team = serializers.SlugRelatedField(slug_field='name', queryset=Team.objects.all())

    class Meta:
        model = TeamMatch
        fields = ['team', 'tanks', 'side']

    def create(self, validated_data):
        tanks_data = validated_data.pop('tanks')
        team_match = TeamMatch.objects.create(**validated_data)
        for tank_data in tanks_data:
            tank, created = Tank.objects.get_or_create(**tank_data)
            team_match.tanks.add(tank)
        return team_match

class MatchSerializer(serializers.ModelSerializer):
    teammatch_set = TeamMatchSerializer(many=True)

    class Meta:
        model = Match
        fields = [
            'datetime', 'mode', 'gamemode', 'best_of_number',
            'map_selection', 'money_rules', 'special_rules', 'teammatch_set'
        ]

    def create(self, validated_data):
        team_matches_data = validated_data.pop('teammatch_set')
        match = Match.objects.create(**validated_data)
        for team_match_data in team_matches_data:
            tanks_data = team_match_data.pop('tanks')
            team_match = TeamMatch.objects.create(match=match, **team_match_data)
            for tank_data in tanks_data:
                tank, created = Tank.objects.get_or_create(**tank_data)
                team_match.tanks.add(tank)
        return match

    def update(self, instance, validated_data):
        team_matches_data = validated_data.pop('teammatch_set')
        instance.datetime = validated_data.get('datetime', instance.datetime)
        instance.mode = validated_data.get('mode', instance.mode)
        instance.gamemode = validated_data.get('gamemode', instance.gamemode)
        instance.best_of_number = validated_data.get('best_of_number', instance.best_of_number)
        instance.map_selection = validated_data.get('map_selection', instance.map_selection)
        instance.money_rules = validated_data.get('money_rules', instance.money_rules)
        instance.special_rules = validated_data.get('special_rules', instance.special_rules)
        instance.save()

        instance.teammatch_set.all().delete()
        for team_match_data in team_matches_data:
            tanks_data = team_match_data.pop('tanks')
            team_match = TeamMatch.objects.create(match=instance, **team_match_data)
            for tank_data in tanks_data:
                tank, created = Tank.objects.get_or_create(**tank_data)
                team_match.tanks.add(tank)
        return instance


class SlimTeamSerializer(serializers.ModelSerializer):

    class Meta:
        model = Team
        fields = ['name']


class SlimTeamMatchSerializer(serializers.ModelSerializer):
    team = SlimTeamSerializer()

    class Meta:
        model = TeamMatch
        fields = ['team', 'side']


class SlimMatchSerializer(serializers.ModelSerializer):
    teammatch_set = SlimTeamMatchSerializer(many=True, read_only=True)

    class Meta:
        model = Match
        fields = ['datetime', 'teammatch_set']


class TeamResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamResult
        fields = ['team', 'bonuses', 'penalties']


class TankLostSerializer(serializers.ModelSerializer):
    class Meta:
        model = TankLost
        fields = ['team', 'tank', 'quantity']


class SubstituteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Substitute
        fields = ['team', 'activity']


class MatchResultSerializer(serializers.ModelSerializer):
    team_results = TeamResultSerializer(many=True)
    tanks_lost = TankLostSerializer(many=True)
    substitutes = SubstituteSerializer(many=True)

    class Meta:
        model = MatchResult
        fields = ['match', 'winning_side', 'judge', 'team_results', 'tanks_lost', 'substitutes']

    def create(self, validated_data):
        team_results_data = validated_data.pop('team_results')
        tanks_lost_data = validated_data.pop('tanks_lost')
        substitutes_data = validated_data.pop('substitutes')

        match_result = MatchResult.objects.create(**validated_data)

        for team_result_data in team_results_data:
            TeamResult.objects.create(match_result=match_result, **team_result_data)

        for tank_lost_data in tanks_lost_data:
            TankLost.objects.create(match_result=match_result, **tank_lost_data)

        for substitute_data in substitutes_data:
            Substitute.objects.create(match_result=match_result, **substitute_data)

        return match_result