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
        depth = 1

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
    team_name = serializers.CharField(source='team.name', write_only=True)
    team = serializers.SlugRelatedField(slug_field='name', read_only=True)

    class Meta:
        model = TeamResult
        fields = ['team', 'team_name', 'bonuses', 'penalties']


class TankLostSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', write_only=True)
    team = serializers.SlugRelatedField(slug_field='name', read_only=True)
    tank_name = serializers.CharField(source='tank.name', write_only=True)
    tank = serializers.SlugRelatedField(slug_field='name', read_only=True)

    class Meta:
        model = TankLost
        fields = ['team', 'team_name', 'tank', 'tank_name', 'quantity']


class SubstituteSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', write_only=True)
    team = serializers.SlugRelatedField(slug_field='name', read_only=True)
    team_played_for_name = serializers.CharField(source='team_played_for.name', write_only=True)
    team_played_for = serializers.SlugRelatedField(slug_field='name', read_only=True)

    class Meta:
        model = Substitute
        fields = ['team', 'team_name', 'activity', 'side', 'team_played_for', 'team_played_for_name']


class MatchResultSerializer(serializers.ModelSerializer):
    team_results = TeamResultSerializer(many=True)
    tanks_lost = TankLostSerializer(many=True)
    substitutes = SubstituteSerializer(many=True)
    judge_name = serializers.CharField(source='judge.name', write_only=True)
    judge = serializers.SlugRelatedField(slug_field='name', read_only=True)
    match_id = serializers.IntegerField(source='match.id', write_only=True)
    match = serializers.SlugRelatedField(slug_field='id', read_only=True)

    class Meta:
        model = MatchResult
        fields = ['match', 'match_id', 'winning_side', 'judge', 'judge_name', 'team_results', 'tanks_lost',
                  'substitutes']
        depth = 1

    def create(self, validated_data):
        match_data = validated_data.pop('match')
        match = Match.objects.get(id=match_data.id)
        judge_data = validated_data.pop('judge')
        judge = Team.objects.get(name=judge_data['name'])

        team_results_data = validated_data.pop('team_results')
        tanks_lost_data = validated_data.pop('tanks_lost')
        substitutes_data = validated_data.pop('substitutes')

        match_result = MatchResult.objects.create(match=match, judge=judge, **validated_data)

        for team_result_data in team_results_data:
            team_name = team_result_data.pop('team')['name']
            team = Team.objects.get(name=team_name)
            TeamResult.objects.create(match_result=match_result, team=team, **team_result_data)

        for tank_lost_data in tanks_lost_data:
            team_name = tank_lost_data.pop('team')['name']
            tank_name = tank_lost_data.pop('tank')['name']
            team = Team.objects.get(name=team_name)
            tank = Tank.objects.get(name=tank_name)
            TankLost.objects.create(match_result=match_result, team=team, tank=tank, **tank_lost_data)

        for substitute_data in substitutes_data:
            team_name = substitute_data.pop('team')['name']
            team_played_for_name = substitute_data.pop('team_played_for')['name']
            team = Team.objects.get(name=team_name)
            team_played_for = Team.objects.get(name=team_played_for_name)
            Substitute.objects.create(match_result=match_result, team=team, team_played_for=team_played_for, **substitute_data)

        return match_result