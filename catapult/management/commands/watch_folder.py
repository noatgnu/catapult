import datetime
import time
import os

from django.core.management.base import BaseCommand, CommandError
from watchdog.observers.polling import PollingObserverVFS
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from catapult.models import File, FolderWatchingLocation, Experiment

class Watcher(FileSystemEventHandler):
    def __init__(self, network_folder, folder_path, file_extensions, *args, **kwargs):
        self.network_folder = network_folder
        self.folder_path = folder_path
        folder = FolderWatchingLocation.objects.get_or_create(folder_path=folder_path)
        self.folder_watching_location = folder[0]
        self.file_extensions = set(file_extensions)
        print(self.folder_watching_location)
        super().__init__(*args, **kwargs)

    def process_file(self, file_path):
        file_size = os.path.getsize(file_path)
        modified_time = os.path.getmtime(file_path)
        created_time = os.path.getctime(file_path)
        return file_size, modified_time, created_time


    def on_created(self, event):
        if self.folder_watching_location.ignore_term in event.src_path:
            return
        if event.is_directory:
            if not event.src_path.endswith(".d"):
                return
        extension = os.path.splitext(event.src_path)[1]
        if extension in self.file_extensions:
            file_size, modified_time, created_time = self.process_file(event.src_path)
            # get parent folder
            parent_folder = os.path.dirname(event.src_path)
            exp = Experiment.objects.get_or_create(experiment_name=parent_folder)

            File.objects.create(
                file_path=event.src_path,
                experiment=exp[0],
                folder_watching_location=self.folder_watching_location,
                size=file_size,
            )
            print(f"{event.src_path} has been created at {modified_time}")


    def on_deleted(self, event):
        if self.folder_watching_location.ignore_term in event.src_path:
            return
        File.objects.filter(file_path=event.src_path).delete()
        print(f"{event.src_path} has been deleted at {datetime.datetime.now()}")

    def on_modified(self, event):
        if self.folder_watching_location.ignore_term in event.src_path:
            return
        if event.is_directory:
            if not event.src_path.endswith(".d"):
                return
        extension = os.path.splitext(event.src_path)[1]
        if extension in self.file_extensions:
            file_size, modified_time, created_time = self.process_file(event.src_path)
            file = File.objects.get(file_path=event.src_path)
            file.size = file_size
            file.save()
            print(f"{event.src_path} has been modified at {created_time}")

    def on_moved(self, event):
        if self.folder_watching_location.ignore_term in event.src_path:
            return
        if event.is_directory:
            if not event.src_path.endswith(".d"):
                return
        extension = os.path.splitext(event.src_path)[1]
        if extension in self.file_extensions:
            File.objects.filter(file_path=event.src_path).update(file_path=event.dest_path)
        print(f"{event.src_path} to {event.dest_path} at {datetime.datetime.now()}")

    def start_watching(self):
        if self.network_folder:
            observer = PollingObserverVFS(os.stat, os.scandir, 1)
        else:
            observer = Observer()
        observer.schedule(self, self.folder_path, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


class Command(BaseCommand):
    """
    A command that watch a folder, check if the folder is a network folder and load data from provided txt files
    """

    def add_arguments(self, parser):
        parser.add_argument('folder_path', type=str, help='Path to the folder to be watched')
        parser.add_argument('network_folder', type=bool, help='Is the folder a network folder?')
        parser.add_argument('file_extensions', type=str, help='File extension to be watched. Delimited by comma. (.d,.wiff,.raw,.mzML,.dia)')


    def handle(self, *args, **options):
        network_folder = options['network_folder']
        folder_path = options['folder_path']
        folder_path = os.path.abspath(folder_path)
        #folder_path = folder_path.replace("\\", "/")
        file_extensions = options['file_extensions'].split(",")
        watcher = Watcher(network_folder, folder_path, file_extensions)
        watcher.start_watching()


