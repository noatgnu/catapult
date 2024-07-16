import os.path
from argparse import ArgumentParser

from django.core.management import BaseCommand

from catapult.models import FolderWatchingLocation


class Command(BaseCommand):
    help = "Run a database background worker"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--path",
            nargs="?",
            type=str,
            help="Path to the folder",
        )
        parser.add_argument(
            "--ignore_term",
            nargs="?",
            type=str,
            default="DONOTPROCESS",
            help="Ignore term",
        )
        parser.add_argument(
            "--extension",
            nargs="?",
            type=str,
            default=".raw,.wiff,.d,.mzML,.dia",
            help="File format",
        )
        parser.add_argument(
            "--network",
            action="store_true",
            help="Is network folder",
        )

    def handle(self, path, ignore_term, extension, network, *args, **options):
        if not os.path.exists(path):
            raise ValueError(f"Folder {path} does not exist")
        if FolderWatchingLocation.objects.filter(folder_path=path).exists():
            raise ValueError(f"Folder {path} is already being watched")
        FolderWatchingLocation.objects.create(
            folder_path=path,
            ignore_term=ignore_term,
            extension=extension,
            network=network,
        )

