from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'
    verbose_name = 'ReFound'

    def ready(self):
        from . import signals  # noqa: F401
