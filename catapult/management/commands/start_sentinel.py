import datetime
import time
import os

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from watchdog.observers.polling import PollingObserverVFS
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from catapult.models import File, FolderWatchingLocation, Experiment

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
            file_location = event.src_path
            if event.src_path.endswith(".d"):
                root, file = os.path.split(event.src_path)
                parent_folder = os.path.dirname(root)
                file_location = root
                file_size = get_folder_size(file_location)
            else:
                parent_folder = os.path.dirname(event.src_path)

            exp = Experiment.objects.get_or_create(experiment_name=parent_folder)

            File.objects.create(
                file_path=file_location.replace(self.folder_path, ""),
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
        print(f"{event.src_path} has been modified")
        if self.folder_watching_location.ignore_term in event.src_path:
            return
        if event.is_directory:
            return
        extension = os.path.splitext(event.src_path)[1]
        if extension in self.file_extensions:
            file_size, modified_time, created_time = self.process_file(event.src_path)
            file = File.objects.get(file_path=event.src_path)
            file.size = file_size
            file.save()


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




class Command(BaseCommand):
    """
    A command that watch a folder, check if the folder is a network folder and load data from provided txt files
    """

    def handle(self, *args, **options):
        observers = []
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
            for observer in observers:
                observer.unschedule_all()
                observer.stop()
        for observer in observers:
            observer.join()
