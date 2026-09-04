from django.shortcuts import render, redirect
from django.core.serializers import serialize
from django.contrib.auth.decorators import login_required
from .models import Campus, Building

def map_view(request):
    campuses_geojson = serialize('geojson', Campus.objects.all())
    buildings_geojson = serialize('geojson', Building.objects.all())
    context = {
        'campuses_geojson': campuses_geojson,
        'buildings_geojson': buildings_geojson,
    }
    return render(request, 'map_app/map.html', context)

@login_required
def dashboard_view(request):
    # 1. Đã sửa lỗi dư chữ "request" ở dòng dưới đây
    if request.user.is_superuser:
        return redirect('/admin/')

    # 2. Nếu là Staff (Dựa vào ô tích Staff status) hoặc Student
    if request.user.is_staff:
        role = "Nhân viên Cơ sở vật chất (Staff)"
    else:
        role = "Khách (Guest/Student)"

    context = {
        'username': request.user.username,
        'role': role
    }
    return render(request, 'map_app/dashboard.html', context)