from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='adbms-dashboard'),
    path('non-repeatable-read/', views.non_repeatable_read, name='non-repeatable-read'),
    path('phantom-read/', views.phantom_read, name='phantom-read'),
    path('deadlock/', views.deadlock_simulation, name='deadlock'),
    path('indexing/', views.indexing_benchmark, name='indexing-benchmark'),
    path('query-optimization/', views.query_optimization, name='query-optimization'),
    path('partitioning/', views.partitioning_demo, name='partitioning-demo'),
    path('row-locking/', views.row_locking_demo, name='row-locking'),
    path('triggers/', views.trigger_demo, name='trigger-demo'),
    path('normalization/', views.normalization_demo, name='normalization-demo'),
    path('mvcc-visibility/', views.mvcc_visibility_demo, name='mvcc-visibility'),
    path('monitoring/', views.monitoring_stats_demo, name='monitoring-stats'),
    path('replication/', views.replication_demo, name='replication-demo'),
]
