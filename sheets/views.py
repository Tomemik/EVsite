from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Team, Manufacturer, Tank
from .serializers import TeamSerializer, ManufacturerSerializer, TankSerializer


# Create your views here.


class AllTeamsView(APIView):
    def get(self, request):
        teams = Team.objects.all()
        serializer = TeamSerializer(teams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = TeamSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
        print(serializer.errors)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TeamDetailView(APIView):
    def get(self, request, pk):
        team = Team.objects.get(pk=pk)
        serializer = TeamSerializer(team)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        team = Team.objects.get(pk=pk)
        serializer = TeamSerializer(team, data=request.data)
        if serializer.is_valid():
            serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class ManufacturerDetailView(APIView):
    def get(self, request, pk):
        manufacturer = Manufacturer.objects.get(pk=pk)
        serializer = ManufacturerSerializer(manufacturer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        manufacturer = Manufacturer.objects.get(pk=pk)
        serializer = ManufacturerSerializer(manufacturer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class ManufacturerListView(APIView):
    def get(self, request):
        manufacturers = Manufacturer.objects.all()
        serializer = ManufacturerSerializer(manufacturers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ManufacturerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TankDetailView(APIView):
    def get(self, request, pk):
        tank = Tank.objects.get(pk=pk)
        serializer = TankSerializer(tank)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        tank = Tank.objects.get(pk=pk)
        serializer = TankSerializer(tank, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

