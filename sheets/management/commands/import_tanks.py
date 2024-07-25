import csv
from django.core.management.base import BaseCommand
from ...models import Tank

class Command(BaseCommand):
    help = 'Import tanks from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file to import')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        with open(csv_file, newline='') as file:
            reader = csv.DictReader(file)

            for row in reader:
                if row['Tank Name']:
                    tank, created = Tank.objects.get_or_create(
                        name=row['Tank Name'],
                        defaults={
                            'battle_rating': float(row['Actual BR']),
                            'price': int(row['Cost']),
                            'rank': int(row['Rank']),
                            'type': row['Type'],
                        }
                    )
                    if not created:
                        tank.battle_rating = float(row['Actual BR'])
                        tank.price = int(row['Cost'])
                        tank.rank = int(row['Rank'])
                        tank.type = row['Type']
                        tank.save()

        self.stdout.write(self.style.SUCCESS('Successfully imported tanks'))