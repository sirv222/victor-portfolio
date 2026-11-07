from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.files import File

from cloudinary_storage.storage import (
    MediaCloudinaryStorage,
    RawMediaCloudinaryStorage,
    VideoMediaCloudinaryStorage,
)

media_storage = MediaCloudinaryStorage()
raw_storage = RawMediaCloudinaryStorage()
video_storage = VideoMediaCloudinaryStorage()

media_root = Path(settings.MEDIA_ROOT).resolve()

migrated = 0
skipped = 0
failed = 0

for app_label in ("sitecore", "my_blog"):
    app_config = apps.get_app_config(app_label)

    for model in app_config.get_models():
        for obj in model.objects.all():

            for field in model._meta.get_fields():

                if not getattr(field, "get_internal_type", None):
                    continue

                if field.get_internal_type() not in (
                    "ImageField",
                    "FileField",
                ):
                    continue

                old_name = getattr(obj, field.name)

                if not old_name or not old_name.name:
                    continue

                local_path = (media_root / old_name.name).resolve()

                if not local_path.is_relative_to(media_root):
                    print(f"Skipped unsafe path: {old_name.name}")
                    skipped += 1
                    continue

                if not local_path.is_file():
                    print(f"Local file missing: {local_path}")
                    skipped += 1
                    continue

                extension = local_path.suffix.lower()

                if field.get_internal_type() == "ImageField":
                    storage = media_storage
                elif extension in (".mp4", ".mov", ".avi"):
                    storage = video_storage
                else:
                    storage = raw_storage

                try:
                    if storage.exists(old_name.name):
                        print(f"Already in Cloudinary: {old_name.name}")
                        continue

                    with local_path.open("rb") as file:
                        uploaded_name = storage.save(
                            old_name.name,
                            File(file),
                        )

                    setattr(obj, field.name, uploaded_name)
                    obj.save(update_fields=[field.name])

                    print(f"Migrated: {old_name.name}")
                    migrated += 1

                except Exception as error:
                    print(f"Failed: {old_name.name} - {error}")
                    failed += 1

print("\nMigration summary")
print(f"Migrated: {migrated}")
print(f"Skipped: {skipped}")
print(f"Failed: {failed}")