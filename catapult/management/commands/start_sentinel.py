import datetime
import logging
import time
import os

import yaml
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from watchdog.observers.polling import PollingObserverVFS
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from catapult.models import File, FolderWatchingLocation, Experiment, CatapultRunConfig

logger = logging.getLogger(f"catapult.sentinel")

def get_folder_size(folder_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

class Watcher(FileSystemEventHandler):
    def __init__(self, folder: FolderWatchingLocation, *args, **kwargs):
        self.folder_path = folder.folder_path
        self.file_extensions = set(folder.extensions.split(","))
        self.ignore_term = folder.ignore_term
        self.network_folder = folder.network_folder
        self.folder_watching_location = folder
        super().__init__(*args, **kwargs)

    def process_file(self, file_path):
        file_size = os.path.getsize(file_path)
        modified_time = os.path.getmtime(file_path)
        created_time = os.path.getctime(file_path)
        return file_size, modified_time, created_time


    def on_created(self, event):
        if self.ignore_term in event.src_path:
            return
        if event.is_directory:
            return
        extension = os.path.splitext(event.src_path)[1]
        if extension in self.file_extensions:
            file_size, modified_time, created_time = self.process_file(event.src_path)
            # get parent folder
            try:
                file = File.objects.get(file_path=event.src_path.replace(self.folder_path, ""))
                file.size = file_size
                file.save()
            except File.DoesNotExist:
                file_location = event.src_path
                if event.src_path.endswith(".d"):
                    root, file = os.path.split(event.src_path)
                    parent_folder = os.path.dirname(root)
                    file_location = root
                    file_size = get_folder_size(file_location)
                else:
                    parent_folder = os.path.dirname(event.src_path)
                exp = Experiment.objects.get_or_create(experiment_name=parent_folder)
                file = File.objects.create(
                    file_path=file_location.replace(self.folder_path, ""),
                    folder_watching_location=self.folder_watching_location,
                    size=file_size,
                    experiment=exp[0],
                )

            print(f"{event.src_path} has been created at {modified_time}")
        elif event.src_path.endswith(".cat.yml") or event.src_path.endswith(".cat.yaml"):
            self.load_config_yaml(event)

    def load_config_yaml(self, event):
        if not CatapultRunConfig.objects.filter(config_file_path=event.src_path).exists():
            logger.info(f"attempting to load config file {event.src_path}")
            try:
                with open(event.src_path, "r") as f:
                    config_data = yaml.safe_load(f)
            except yaml.YAMLError as exc:
                logger.error(f"Error loading yaml file {event.src_path}")
                return None
            if "cat_ready" in config_data:
                if config_data["cat_ready"]:
                    logger.info(f"config file {event.src_path} is ready")
                    parent_folder = os.path.dirname(event.src_path)
                    exp = Experiment.objects.get_or_create(experiment_name=parent_folder)
                    config = CatapultRunConfig.objects.create(
                        experiment=exp[0],
                        config_file_path=event.src_path,
                        folder_watching_location=self.folder_watching_location,
                    )
                    logger.info(f"config file {event.src_path} loaded successfully")

    def on_deleted(self, event):
        if self.folder_watching_location.ignore_term in event.src_path:
            return
        File.objects.filter(file_path=event.src_path).delete()
        logger.info(f"{event.src_path} has been deleted at {datetime.datetime.now()}")

    def on_modified(self, event):
        logger.info(f"{event.src_path} has been modified at {datetime.datetime.now()}")
        if self.folder_watching_location.ignore_term in event.src_path:
            return
        if event.is_directory:
            return
        extension = os.path.splitext(event.src_path)[1]
        if extension in self.file_extensions:
            file_size, modified_time, created_time = self.process_file(event.src_path)
            try:
                file = File.objects.get(file_path=event.src_path.replace(self.folder_path, ""))
                file.size = file_size
                file.save()
            except File.DoesNotExist:
                file_location = event.src_path
                if event.src_path.endswith(".d"):
                    root, file = os.path.split(event.src_path)
                    parent_folder = os.path.dirname(root)
                    file_location = root
                    file_size = get_folder_size(file_location)
                else:
                    parent_folder = os.path.dirname(event.src_path)
                exp = Experiment.objects.get_or_create(experiment_name=parent_folder)
                file = File.objects.create(
                    file_path=file_location.replace(self.folder_path, ""),
                    folder_watching_location=self.folder_watching_location,
                    experiment=exp[0],
                    size=file_size,
                )
        elif event.src_path.endswith(".cat.yml") or event.src_path.endswith(".cat.yaml"):
            self.load_config_yaml(event)

    def on_moved(self, event):
        if self.folder_watching_location.ignore_term in event.src_path:
            return
        if event.is_directory:
            if not event.src_path.endswith(".d"):
                return
        extension = os.path.splitext(event.src_path)[1]
        if extension in self.file_extensions:
            File.objects.filter(file_path=event.src_path).update(file_path=event.dest_path)
        logger.info(f"{event.src_path} has been moved to {event.dest_path} at {datetime.datetime.now()}")


class Command(BaseCommand):
    """
    A command that watch a folder, check if the folder is a network folder and load data from provided txt files
    """

    def handle(self, *args, **options):
        observers = []
        logging_path = "sentinel.log"
        if not logger.hasHandlers():
            # Use FileHandler instead of StreamHandler
            handler = logging.FileHandler(logging_path)
            # Set the format for the handler
            formatter = logging.Formatter('[%(asctime)s: %(levelname)s]  %(message)s')
            handler.setFormatter(formatter)

            logger.addHandler(handler)
        logger.info(f"Logging to {logging_path}")
        for f in FolderWatchingLocation.objects.all():
            w = Watcher(f)
            if w.network_folder:
                observer = PollingObserverVFS(os.stat, os.scandir, 1)
            else:
                observer = Observer()
            observer.schedule(w, f.folder_path, recursive=True)

            observers.append(observer)
            observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping observers")
            for observer in observers:
                observer.unschedule_all()
                observer.stop()
        for observer in observers:
            observer.join()
