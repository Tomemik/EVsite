from django.contrib import admin
from .models import Manufacturer, Team, Tank, UpgradePath, TeamTank, Match, TeamMatch, default_upgrade_kits, \
    MatchResult, Substitute, TankLost, TeamResult


class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'balance')
    search_fields = ('name',)
    readonly_fields = ('upgrade_kits',)

    def save_model(self, request, obj, form, change):
        obj.upgrade_kits = {tier: data.copy() for tier, data in default_upgrade_kits().items()}
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


class TeamMatchInline(admin.TabularInline):
    model = TeamMatch
    extra = 1
    filter_horizontal = ('tanks',)
    fields = ('team', 'side', 'tanks')
    show_change_link = True


class MatchAdmin(admin.ModelAdmin):
    list_display = ('datetime', 'mode', 'gamemode', 'best_of_number', 'map_selection')
    search_fields = ('mode', 'gamemode', 'map_selection')
    inlines = [TeamMatchInline]
    list_filter = ('mode', 'gamemode', 'datetime')


class TeamMatchAdmin(admin.ModelAdmin):
    list_display = ('match', 'team', 'side')
    search_fields = ('match__datetime', 'team__name')
    filter_horizontal = ('tanks',)
    list_filter = ('side',)


class TankLostInline(admin.TabularInline):
    model = TankLost
    extra = 1


class SubstituteInline(admin.TabularInline):
    model = Substitute
    extra = 1


class TeamResultInline(admin.TabularInline):
    model = TeamResult
    extra = 1


class MatchResultAdmin(admin.ModelAdmin):
    list_display = ('match', 'winning_side', 'judge')
    inlines = [TankLostInline, SubstituteInline, TeamResultInline]

    def judge(self, obj):
        return obj.judge.name if obj.judge else '-'


admin.site.register(MatchResult, MatchResultAdmin)
admin.site.register(Manufacturer, ManufacturerAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Tank, TankAdmin)
admin.site.register(UpgradePath, UpgradePathAdmin)
admin.site.register(TeamTank, TeamTankAdmin)
admin.site.register(Match, MatchAdmin)
admin.site.register(TeamMatch, TeamMatchAdmin)