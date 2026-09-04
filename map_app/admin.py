from django.contrib.gis import admin
from .models import Campus, Building, Floor, Room, ParkingArea, GreenArea, Tree

# Cấu hình bản đồ mặc định cho phiên bản Django mới
class CustomGeoAdmin(admin.GISModelAdmin):
    gis_widget_kwargs = {
        'attrs': {
            'default_lon': 106.6661,  # Kinh độ cơ sở Lê Văn Sỹ
            'default_lat': 10.7936,   # Vĩ độ cơ sở Lê Văn Sỹ
            'default_zoom': 18,       # Mức zoom cận cảnh
        }
    }

# Áp dụng cấu hình cho tất cả các bảng
admin.site.register(Campus, CustomGeoAdmin)
admin.site.register(Building, CustomGeoAdmin)
admin.site.register(Floor, CustomGeoAdmin)
admin.site.register(Room, CustomGeoAdmin)
admin.site.register(ParkingArea, CustomGeoAdmin)
admin.site.register(GreenArea, CustomGeoAdmin)
admin.site.register(Tree, CustomGeoAdmin)