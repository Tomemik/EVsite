from django.test import TestCase
from rest_framework.exceptions import ValidationError

from .models import Manufacturer, Team, Tank, UpgradePath


class TankUpgradeTests(TestCase):

    def setUp(self):
        # Create manufacturers
        self.manufacturer1 = Manufacturer.objects.create(name='Manufacturer1')
        self.manufacturer2 = Manufacturer.objects.create(name='Manufacturer2')

        # Create teams and associate them with manufacturers, setting initial balance
        self.team1 = Team.objects.create(name='Team1', balance=500000)
        self.team1.manufacturers.add(self.manufacturer1, self.manufacturer2)

        self.team2 = Team.objects.create(name='Team2', balance=500000)
        self.team2.manufacturers.add(self.manufacturer2)

        # Create tanks and associate them with multiple manufacturers
        self.tank1 = Tank.objects.create(name='M10', battle_rating=3.7, price=170000)
        self.tank1.manufacturers.add(self.manufacturer1, self.manufacturer2)

        self.tank2 = Tank.objects.create(name='M4', battle_rating=3.7, price=162000)
        self.tank2.manufacturers.add(self.manufacturer2)

        self.tank3 = Tank.objects.create(name='M4A2', battle_rating=4.0, price=192000)
        self.tank3.manufacturers.add(self.manufacturer1)

        self.tank4 = Tank.objects.create(name='M4A2 76W', battle_rating=5.0, price=300000)
        self.tank4.manufacturers.add(self.manufacturer1)

        # Create upgrade paths with upgrade kits
        UpgradePath.objects.create(from_tank=self.tank1, to_tank=self.tank2, required_kit_tier='T1')
        UpgradePath.objects.create(from_tank=self.tank2, to_tank=self.tank3)
        UpgradePath.objects.create(from_tank=self.tank3, to_tank=self.tank4)

    def test_purchase_tank(self):
        try:
            purchase_message = self.team1.purchase_tank(self.tank1)
            self.assertEqual(purchase_message, f"Tank {self.tank1.name} purchased successfully. Remaining balance: {self.team1.balance}")
        except ValidationError as e:
            self.fail(f"Purchase failed with error: {e}")

    def test_upgrade_tank(self):
        try:
            self.team2.purchase_tank(self.tank1)
            self.team2.add_upgrade_kit('T1',2)
            upgrade_message = self.team2.upgrade_or_downgrade_tank(from_tank=self.tank1, to_tank=self.tank4, extra_upgrade_kit_tiers=['T1'])
            self.assertEqual(upgrade_message, f"Tank {self.tank1.name} upgraded/downgraded to {self.tank4.name}. Total cost: {113000}. Remaining balance: {217000}")
        except ValidationError as e:
            self.fail(f"Upgrade failed with error: {e}")

    def test_manu_upgrade(self):
        try:
            self.team1.purchase_tank(self.tank1)
            self.team1.add_upgrade_kit('T1', 2)
            upgrade_message = self.team1.upgrade_tank_manu(from_tank=self.tank1, to_tank=self.tank4, extra_upgrade_kit_tiers=['T1', 'T1'])
            self.assertEqual(upgrade_message, f"Tank {self.tank1.name} upgraded/downgraded to {self.tank4.name}. Total cost: {80000}. Remaining balance: {250000}")
        except ValidationError as e:
            self.fail(f"Upgrade failed with error: {e}")