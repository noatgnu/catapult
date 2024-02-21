from catapult.models import Analysis

from celery import shared_task


@shared_task
def run_analysis(analysis_id: int):
    analysis = Analysis.objects.get(id=analysis_id)
    analysis.start_analysis()

@shared_task
def run_quant(analysis_id: int):
    analysis = Analysis.objects.get(id=analysis_id)
    analysis.create_quant_file()