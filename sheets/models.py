from django.db import models
from django.db.models import F, Q
from rest_framework.exceptions import ValidationError


def default_upgrade_kits():
    return {
        'T1': {'quantity': 0, 'price': 25000},
        'T2': {'quantity': 0, 'price': 50000},
        'T3': {'quantity': 0, 'price': 100000}
    }


class Manufacturer(models.Model):
    name = models.CharField(max_length=50)


class Team(models.Model):

    name = models.CharField(max_length=50)
    balance = models.IntegerField(default=0)
    manufacturers = models.ManyToManyField(Manufacturer, related_name='teams')
    tanks = models.ManyToManyField('Tank', through='TeamTank', related_name='teams')
    upgrade_kits = models.JSONField(default=default_upgrade_kits)

    def __str__(self):
        return self.name

    def purchase_tank(self, tank):
        if tank.price > self.balance:
            raise ValidationError("Insufficient balance to purchase this tank.")
        if not self.manufacturers.filter(id__in=tank.manufacturers.all()).exists():
            raise ValidationError("This tank is not available from your manufacturers.")
        self.balance -= tank.price
        self.save()
        TeamTank.objects.create(team=self, tank=tank)
        return f"Tank {tank.name} purchased successfully. Remaining balance: {self.balance}"

    def add_upgrade_kit(self, tier, quantity=1):
        if tier in self.UPGRADE_KITS:
            if tier in self.upgrade_kits:
                self.upgrade_kits[tier]['quantity'] += quantity
            self.save()
            return f"Added {quantity} Upgrade Kit(s) of tier {tier} to {self.name}."
        else:
            return "Invalid upgrade kit tier."

    def get_upgrade_kit_discount(self, tier):
        return self.upgrade_kits.get(tier, {"price": 0})["price"]


    def upgrade_tank_manu(self, from_tank, to_tank, extra_upgrade_kit_tiers=[]):
        if not self.tanks.filter(id=from_tank.id).exists():
            raise ValidationError("You do not own this tank.")
        if not self.manufacturers.filter(id__in=to_tank.manufacturers.all()).exists():
            raise ValidationError("This tank is not available from your manufacturers.")

        current_tank = from_tank

        while current_tank != to_tank:
            try:
                upgrade_path = UpgradePath.objects.get(from_tank=current_tank, to_tank__in=Tank.objects.all())
            except UpgradePath.DoesNotExist:
                raise ValidationError(f"No upgrade path found from {current_tank.name}.")

            current_tank = upgrade_path.to_tank

        all_needed_kits = extra_upgrade_kit_tiers
        missing_kits = [kit for kit in all_needed_kits if kit not in self.upgrade_kits or self.upgrade_kits[kit]['quantity'] <= 0]
        if missing_kits:
            raise ValidationError(f"Missing upgrade kits: {', '.join(missing_kits)}")

        total_extra_discount = sum(
            self.get_upgrade_kit_discount(tier) for tier in extra_upgrade_kit_tiers if tier in self.UPGRADE_KITS)
        cost = to_tank.price - from_tank.price if to_tank.price >= from_tank.price else (to_tank.price - from_tank.price) / 2
        cost -= total_extra_discount
        cost = max(cost, 0)

        if cost > self.balance:
            raise ValidationError("Insufficient balance for this upgrade or downgrade.")

        for kit in extra_upgrade_kit_tiers:
            if kit in self.upgrade_kits:
                self.upgrade_kits[kit]['quantity'] -= 1

        self.balance -= cost
        self.tanks.through.objects.filter(team=self, tank=from_tank).delete()
        self.tanks.through.objects.create(team=self, tank=to_tank)
        self.save()

        return f"Tank {from_tank.name} upgraded/downgraded to {to_tank.name}. Total cost: {cost}. Remaining balance: {self.balance}"


    def upgrade_or_downgrade_tank(self, from_tank, to_tank, extra_upgrade_kit_tiers=[]):
        print(self.upgrade_kits)
        if not self.tanks.filter(id=from_tank.id).exists():
            raise ValidationError("You do not own this tank.")

        # Initialize total cost and start from the given tank
        total_cost = 0
        current_tank = from_tank

        required_kits = []
        upgrade_paths = []

        while current_tank != to_tank:
            try:
                upgrade_path = UpgradePath.objects.get(from_tank=current_tank, to_tank__in=Tank.objects.all())
            except UpgradePath.DoesNotExist:
                raise ValidationError(f"No upgrade path found from {current_tank.name}.")

            step_cost = upgrade_path.cost
            required_kit_tier = upgrade_path.required_kit_tier

            if required_kit_tier:
                required_kits.append(required_kit_tier)
                print(self.upgrade_kits)
                if required_kit_tier in self.upgrade_kits and self.upgrade_kits[required_kit_tier]['quantity'] > 0:
                    step_cost -= self.get_upgrade_kit_discount(required_kit_tier)
                else:
                    raise ValidationError(f"Required upgrade kit {required_kit_tier} is missing from inventory.")

            upgrade_paths.append(upgrade_path)
            step_cost = max(step_cost, 0)
            total_cost += step_cost

            current_tank = upgrade_path.to_tank

        # Check availability of required kits and extra kits
        all_needed_kits = set(required_kits + extra_upgrade_kit_tiers)
        missing_kits = [kit for kit in all_needed_kits if
                        kit not in self.upgrade_kits or self.upgrade_kits[kit]['quantity'] <= 0]
        if missing_kits:
            raise ValidationError(f"Missing upgrade kits: {', '.join(missing_kits)}")

        # Ensure that the same kit is not used for both required and extra kits
        available_kits = self.upgrade_kits.copy()
        for kit in required_kits:
            if kit in available_kits and available_kits[kit]['quantity'] > 0:
                available_kits[kit]['quantity'] -= 1
                if available_kits[kit]['quantity'] == 0:
                    del available_kits[kit]
            else:
                raise ValidationError(f"Required upgrade kit {kit} is missing from inventory.")

        for extra_kit in extra_upgrade_kit_tiers:
            if extra_kit in available_kits and available_kits[extra_kit]['quantity'] > 0:
                available_kits[extra_kit]['quantity'] -= 1
                if available_kits[extra_kit]['quantity'] == 0:
                    del available_kits[extra_kit]
            else:
                raise ValidationError(f"Extra upgrade kit {extra_kit} is missing from inventory.")

        # Apply extra kits discount to the entire total cost
        total_extra_discount = sum(
            self.get_upgrade_kit_discount(tier) for tier in extra_upgrade_kit_tiers if tier in self.UPGRADE_KITS)
        total_cost -= total_extra_discount
        total_cost = max(total_cost, 0)

        if total_cost > self.balance:
            raise ValidationError("Insufficient balance for this upgrade or downgrade.")

        # Deduct required kits from the inventory
        for kit in required_kits:
            if kit in self.upgrade_kits:
                self.upgrade_kits[kit]['quantity'] -= 1
                if self.upgrade_kits[kit]['quantity'] == 0:
                    del self.upgrade_kits[kit]

        # Update balance and tank ownership
        self.balance -= total_cost
        self.tanks.through.objects.filter(team=self, tank=from_tank).delete()
        self.tanks.through.objects.create(team=self, tank=to_tank)
        self.save()

        return f"Tank {from_tank.name} upgraded/downgraded to {to_tank.name}. Total cost: {total_cost}. Remaining balance: {self.balance}"


class Tank(models.Model):

    name = models.CharField(max_length=50)
    battle_rating = models.FloatField(default=1.0)
    price = models.IntegerField(default=0)
    rank = models.IntegerField(default=1)
    type = models.CharField(max_length=50, default='MT')
    upgrades = models.ManyToManyField('self', through='UpgradePath', symmetrical=False, related_name='downgrades')
    manufacturers = models.ManyToManyField(Manufacturer, related_name='tanks')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.pk:
            old_price = Tank.objects.get(pk=self.pk).price
        else:
            old_price = None

        super().save(*args, **kwargs)

        if old_price is not None and old_price != self.price:
            for upgrade_path in UpgradePath.objects.filter(from_tank=self):
                upgrade_path.cost = upgrade_path.calculate_cost()
                upgrade_path.save()
            for upgrade_path in UpgradePath.objects.filter(to_tank=self):
                upgrade_path.cost = upgrade_path.calculate_cost()
                upgrade_path.save()


class UpgradePath(models.Model):
    from_tank = models.ForeignKey(Tank, related_name='upgrade_from', on_delete=models.CASCADE)
    to_tank = models.ForeignKey(Tank, related_name='upgrade_to', on_delete=models.CASCADE)
    required_kit_tier = models.CharField(max_length=50, blank=True, null=True)
    cost = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        self.calculate_cost()
        super().save(*args, **kwargs)

    def calculate_cost(self):
        """Calculate the cost based on price differences and battle rating."""
        price_difference = self.to_tank.price - self.from_tank.price
        print(price_difference)
        if self.from_tank.price > self.to_tank.price:
            self.cost = abs(price_difference / 2)
        else:
            self.cost = abs(price_difference)


class TeamTank(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    tank = models.ForeignKey(Tank, on_delete=models.CASCADE)
    is_upgradable = models.BooleanField(default=True)


class Match(models.Model):
    MODE_CHOICES = [
        ('traditional', 'Traditional'),
        ('advanced', 'Advanced'),
        ('evolved', 'Evolved'),
    ]

    GAMEMODE_CHOICES = [
        ('annihilation', 'Annihilation'),
        ('domination', 'Domination'),
        ('flag_tank', 'Flag Tank'),
    ]

    MONEY_RULES = [
        ('money_rule', 'Money Rule'),
        ('even_split', 'Even Split'),
    ]

    datetime = models.DateTimeField()
    mode = models.CharField(max_length=50, choices=MODE_CHOICES)
    gamemode = models.CharField(max_length=50, choices=GAMEMODE_CHOICES)
    best_of_number = models.IntegerField()
    map_selection = models.CharField(max_length=255)
    money_rules = models.CharField(max_length=50, choices=MONEY_RULES)
    special_rules = models.TextField(blank=True, null=True)
    teams = models.ManyToManyField(Team, through='TeamMatch', related_name='matches')
    was_played  = models.BooleanField(default=False)

    def __str__(self):
        return f"Match on {self.datetime} - {self.mode} - {self.gamemode}"


class TeamMatch(models.Model):
    SIDE_CHOICES = [
        ('team_1', 'Team 1'),
        ('team_2', 'Team 2'),
    ]

    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    tanks = models.ManyToManyField(Tank, related_name='team_matches')
    side = models.CharField(max_length=10, choices=SIDE_CHOICES, default='team_1')

    def __str__(self):
        return f"{self.team.name} in {self.match} with: \n {self.tanks}"


class MatchResult(models.Model):
    match = models.OneToOneField(Match, on_delete=models.CASCADE)
    winning_side = models.CharField(max_length=10, choices=TeamMatch.SIDE_CHOICES)
    judge = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name='judged_matches')

    def calculate_average_rank(self):
        tanks = Tank.objects.filter(team_matches__match=self.match)

        total_rank_br = sum(tank.rank * tank.battle_rating for tank in tanks)
        total_br = sum(tank.battle_rating for tank in tanks)

        if total_br > 0:
            average_rank = total_rank_br / total_br
        else:
            average_rank = 0

        return round(average_rank)

    def calculate_base_reward(self, average_rank):

        advanced_rewards = [
            {"rank": 1, "winner": 20000, "loser": 15000},
            {"rank": 2, "winner": 40000, "loser": 30000},
            {"rank": 3, "winner": 60000, "loser": 45000},
            {"rank": 4, "winner": 80000, "loser": 60000},
            {"rank": 5, "winner": 100000, "loser": 75000},
        ]

        flag_rewards = [
            {"rank": 1, "winner": 35000, "loser": 15000},
            {"rank": 2, "winner": 60000, "loser": 25000},
            {"rank": 3, "winner": 85000, "loser": 40000},
            {"rank": 4, "winner": 11000, "loser": 50000},
            {"rank": 5, "winner": 150000, "loser": 70000},
        ]

        trad_bo5_rewards = [
            {"rank": 1, "winner": 20000, "loser": 15000},
            {"rank": 2, "winner": 40000, "loser": 30000},
            {"rank": 3, "winner": 55000, "loser": 40000},
            {"rank": 4, "winner": 75000, "loser": 55000},
            {"rank": 5, "winner": 95000, "loser": 70000},
        ]

        trad_bo3_rewards = [
            {"rank": 1, "winner": 15000, "loser": 12000},
            {"rank": 2, "winner": 30000, "loser": 23000},
            {"rank": 3, "winner": 45000, "loser": 34000},
            {"rank": 4, "winner": 60000, "loser": 45000},
            {"rank": 5, "winner": 75000, "loser": 56000},
        ]

        mode = self.match.mode
        game_mode = self.match.gamemode
        best_of = self.match.best_of_number

        if mode == "traditional":
            if best_of == 3:
                return trad_bo3_rewards[min(int(round(average_rank)-1), 4)]["winner"], trad_bo3_rewards[min(int(round(average_rank)-1), 4)]["loser"]
            if best_of == 5:
                return trad_bo5_rewards[min(int(round(average_rank)-1), 4)]["winner"], trad_bo5_rewards[min(int(round(average_rank)-1), 4)]["loser"]
        elif mode == "advanced":
            if game_mode == "flag":
                return flag_rewards[min(int(round(average_rank)-1), 4)]["winner"], flag_rewards[min(int(round(average_rank)-1), 4)]["loser"]
            else:
                return advanced_rewards[min(int(round(average_rank)-1), 4)]["winner"], advanced_rewards[min(int(round(average_rank)-1), 4)]["loser"]

        return 0, 0

    def calculate_rewards(self):
        average_rank = self.calculate_average_rank()
        winner_base_reward, loser_base_reward = self.calculate_base_reward(average_rank)
        print(average_rank)
        print(winner_base_reward, loser_base_reward)

        team_rewards = {team.id: 0 for team in Team.objects.all()}

        teams_on_side = {
            'team_1': list(TeamMatch.objects.filter(match=self.match, side='team_1').values_list('team_id', flat=True)),
            'team_2': list(TeamMatch.objects.filter(match=self.match, side='team_2').values_list('team_id', flat=True)),
        }

        num_teams_on_side = {
            'team_1': len(teams_on_side['team_1']),
            'team_2': len(teams_on_side['team_2']),
        }

        total_loss_penalty_team_1 = 0
        total_gain_reward_team_1 = 0
        total_loss_penalty_team_2 = 0
        total_gain_reward_team_2 = 0

        for tank_lost in self.tanks_lost.all():
            team_id = tank_lost.team.id
            tank_price = tank_lost.tank.price
            quantity = tank_lost.quantity
            side = 'team_1' if team_id in teams_on_side['team_1'] else 'team_2'
            other_side = 'team_2' if side == 'team_1' else 'team_1'

            loss_penalty = tank_price * 0.02 * quantity
            gain_reward = tank_price * 0.03 * quantity

            if side == 'team_1':
                total_loss_penalty_team_1 += loss_penalty
                total_gain_reward_team_2 += gain_reward
            else:
                total_gain_reward_team_1 += gain_reward
                total_loss_penalty_team_2 += loss_penalty

        if self.winning_side == 'team_1':
            winner_base_reward = winner_base_reward + total_gain_reward_team_1 - total_loss_penalty_team_1
            loser_base_reward = loser_base_reward + total_gain_reward_team_2 - total_loss_penalty_team_2
        else:
            winner_base_reward = winner_base_reward + total_loss_penalty_team_2 + total_gain_reward_team_2
            loser_base_reward = loser_base_reward + total_gain_reward_team_1 - total_loss_penalty_team_1

        winning_teams = teams_on_side[self.winning_side]
        losing_teams = teams_on_side['team_1' if self.winning_side == 'team_2' else 'team_2']

        substitutes_rewards = {
            'team_1': 0,
            'team_2': 0,
        }
        '''
        for substitute in self.substitutes.all():
            team_id = substitute.team.id
            activity = substitute.activity
            side = 'team_1' if team_id in teams_on_side['team_1'] else 'team_2'
            reward_percentage = 0.05 * activity
            base_reward = winner_base_reward if side == self.winning_side else loser_base_reward

            substitute_reward = base_reward * reward_percentage / num_teams_on_side[side]
            substitutes_rewards[side] += substitute_reward
            team_rewards[team_id] += substitute_reward
        '''
        if self.winning_side == 'team_1':
            winner_base_reward = winner_base_reward - substitutes_rewards['team_1']
            loser_base_reward = loser_base_reward - substitutes_rewards['team_2']
        else:
            winner_base_reward = winner_base_reward - substitutes_rewards['team_2']
            loser_base_reward = loser_base_reward - substitutes_rewards['team_1']

        if self.match.mode in ["traditional", "flag"]:
            for team in winning_teams:
                team_rewards[team] = winner_base_reward
            for team in losing_teams:
                team_rewards[team] = loser_base_reward
        else:
            winner_total_reward = winner_base_reward
            loser_total_reward = loser_base_reward

            for team in winning_teams:
                team_rewards[team] += winner_total_reward / len(winning_teams)
            for team in losing_teams:
                team_rewards[team] += loser_total_reward / len(losing_teams)

        for team_result in self.team_results.all():
            team_id = team_result.team.id
            if team_result.bonuses:
                team_rewards[team_id] += 10000 * team_result.bonuses
            if team_result.penalties:
                team_rewards[team_id] -= 10000 * average_rank * team_result.penalties
            print(team_id, team_rewards[team_id])

        for team_id, reward in team_rewards.items():
            team = Team.objects.get(id=team_id)
            team.balance += reward
            team.save()


class TeamResult(models.Model):
    match_result = models.ForeignKey(MatchResult, on_delete=models.CASCADE, related_name='team_results')
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    bonuses = models.FloatField(blank=True, null=True)
    penalties = models.FloatField(blank=True, null=True)


class TankLost(models.Model):
    match_result = models.ForeignKey(MatchResult, on_delete=models.CASCADE, related_name='tanks_lost')
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    tank = models.ForeignKey(Tank, on_delete=models.CASCADE)
    quantity = models.IntegerField()


class Substitute(models.Model):
    match_result = models.ForeignKey(MatchResult, on_delete=models.CASCADE, related_name='substitutes')
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    activity = models.IntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])