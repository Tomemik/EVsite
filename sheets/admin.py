from django.contrib import admin
from .models import Manufacturer, Team, Tank, UpgradePath, TeamTank


class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'balance')
    search_fields = ('name',)
    readonly_fields = ('upgrade_kits',)

    def save_model(self, request, obj, form, change):
        obj.upgrade_kits = {tier: data.copy() for tier, data in Team.UPGRADE_KITS.items()}
        super().save_model(request, obj, form, change)


class TankAdmin(admin.ModelAdmin):
    list_display = ('name', 'battle_rating', 'price', 'rank', 'type')
    search_fields = ('name', 'type')
    list_filter = ('type', 'rank')


class UpgradePathAdmin(admin.ModelAdmin):
    list_display = ('from_tank', 'to_tank', 'required_kit_tier', 'cost')
    search_fields = ('from_tank__name', 'to_tank__name')
    list_filter = ('required_kit_tier',)


class TeamTankAdmin(admin.ModelAdmin):
    list_display = ('team', 'tank', 'is_upgradable')
    search_fields = ('team__name', 'tank__name')
    list_filter = ('is_upgradable',)


admin.site.register(Manufacturer, ManufacturerAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Tank, TankAdmin)
admin.site.register(UpgradePath, UpgradePathAdmin)
admin.site.register(TeamTank, TeamTankAdmin)