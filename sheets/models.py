from django.db import models
from django.db.models import F, Q
from rest_framework.exceptions import ValidationError


class Manufacturer(models.Model):
    name = models.CharField(max_length=50)


class Team(models.Model):

    UPGRADE_KITS = {
        'T1': {'quantity': 0, 'price': 25000},
        'T2': {'quantity': 0, 'price': 50000},
        'T3': {'quantity': 0, 'price': 100000}
    }

    name = models.CharField(max_length=50)
    balance = models.IntegerField(default=0)
    manufacturers = models.ManyToManyField(Manufacturer, related_name='teams')
    tanks = models.ManyToManyField('Tank', through='TeamTank', related_name='teams')
    upgrade_kits = models.JSONField(default=UPGRADE_KITS.copy())

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
        cost = to_tank.price - from_tank.price if to_tank.battle_rating >= from_tank.battle_rating else (to_tank.price - from_tank.price) / 2
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
        if self.from_tank.battle_rating > self.to_tank.battle_rating:
            self.cost = abs(price_difference / 2)
        else:
            self.cost = abs(price_difference)

class TeamTank(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    tank = models.ForeignKey(Tank, on_delete=models.CASCADE)
    is_upgradable = models.BooleanField(default=True)
