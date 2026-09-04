"""
Django settings for core project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Kích hoạt đọc biến môi trường từ file .env
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Lấy Secret Key từ file .env để bảo mật
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',  # Kích hoạt lõi bản đồ GeoDjango
    'map_app',             # Khai báo app đồ án của bạn
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Chuyển đổi Database từ SQLite mặc định sang PostgreSQL (PostGIS)
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'

# Email
MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}

import os

# Cấu hình đường dẫn thư viện GIS cho Windows
if os.name == 'nt':
    # Đường dẫn cài đặt OSGeo4W 
    OSGEO4W_ROOT = r"C:\Users\ACER\AppData\Local\Programs\OSGeo4W"
    
    # Cài đặt các biến môi trường để Django biết chỗ tìm dữ liệu
    os.environ['OSGEO4W_ROOT'] = OSGEO4W_ROOT
    os.environ['GDAL_DATA'] = OSGEO4W_ROOT + r"\share\gdal"
    os.environ['PROJ_LIB'] = OSGEO4W_ROOT + r"\share\proj"
    os.environ['PATH'] = OSGEO4W_ROOT + r"\bin;" + os.environ['PATH']

    # === QUAN TRỌNG NHẤT ===
    # Thay 'gdal312.dll' thành đúng tên file bạn đã tìm thấy ở Bước 2
    GDAL_LIBRARY_PATH = OSGEO4W_ROOT + r"\bin\gdal312.dll" 
    GEOS_LIBRARY_PATH = OSGEO4W_ROOT + r"\bin\geos_c.dll"


# Cấu hình điều hướng Đăng nhập / Đăng xuất
LOGIN_REDIRECT_URL = '/map/dashboard/'  
LOGOUT_REDIRECT_URL = '/login/'