import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import tasks.metrics_sync as metrics_sync
import tasks.route_update as route_update

log = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def setup_scheduler():
    scheduler.add_job(
        metrics_sync.run, 
        trigger=IntervalTrigger(hours=24), 
        id='job_sync_metrics', 
        name='Sincronização Diária de Métricas',
        replace_existing=True
    )
    
    scheduler.add_job(
        route_update.run, 
        trigger=IntervalTrigger(hours=1), 
        id='job_update_routes', 
        name='Atualização Horária de Rotas',
        replace_existing=True
    )