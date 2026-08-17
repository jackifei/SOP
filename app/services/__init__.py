"""业务服务层，后续可在此接入相机、MES、数据库、统计等真实服务。"""

from .dashboard_service import DashboardService
from .config_service import ConfigService
from .image_hub import ImageHub, image_hub
from .production_stats_service import ProductionStatsService

__all__ = ["ConfigService", "DashboardService", "ImageHub", "image_hub", "ProductionStatsService"]
