from django.db.models import JSONField
from django_filters import FilterSet, Filter
from django_filters.fields import Lookup

from catapult.models import CatapultRunConfig

class JSONFilter(Filter):
    field_class = JSONField

    def __init__(self, *args, **kwargs):
        kwargs.pop('label', None)
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in (None, ''):
            return qs
        lookup = f"{self.field_name}__exact"
        return qs.filter(**{lookup: value})

class CatapultRunConfigFilter(FilterSet):
    class Meta:
        model = CatapultRunConfig
        fields = ['content', 'experiment', 'analysis']
        filter_overrides = {
            JSONField: {
                'filter_class': JSONFilter,
            },
        }