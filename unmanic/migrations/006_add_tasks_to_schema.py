"""Peewee migrations -- 006_add_tasks_to_schema.py.

Some examples (model - class or model name)::

    > Model = migrator.orm['model_name']            # Return model in current state by name

    > migrator.sql(sql)                             # Run custom SQL
    > migrator.python(func, *args, **kwargs)        # Run python code
    > migrator.create_model(Model)                  # Create a model (could be used as decorator)
    > migrator.remove_model(model, cascade=True)    # Remove a model
    > migrator.add_fields(model, **fields)          # Add fields to a model
    > migrator.change_fields(model, **fields)       # Change fields
    > migrator.remove_fields(model, *field_names, cascade=True)
    > migrator.rename_field(model, old_field_name, new_field_name)
    > migrator.rename_table(model, new_table_name)
    > migrator.add_index(model, *col_names, unique=False)
    > migrator.drop_index(model, *col_names)
    > migrator.add_not_null(model, *field_names)
    > migrator.drop_not_null(model, *field_names)
    > migrator.add_default(model, field_name, default)

"""

import datetime as dt
import peewee as pw
from decimal import ROUND_HALF_EVEN

try:
    import playhouse.postgres_ext as pw_pext
except ImportError:
    pass

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    """
    Create the Tasks Models
    """

    @migrator.create_model
    class Tasks(pw.Model):
        abspath = pw.TextField(null=False, unique=True)
        cache_path = pw.TextField(null=True, unique=True)
        status = pw.TextField(null=False)
        success = pw.BooleanField(null=True)
        start_time = pw.DateTimeField(null=True, default=dt.datetime.now)
        finish_time = pw.DateTimeField(null=True, default=dt.datetime.now)
        processed_by_worker = pw.TextField(null=True)
        ffmpeg_log = pw.TextField(null=False, default='')

    @migrator.create_model
    class TaskSettings(pw.Model):
        task_id = pw.ForeignKeyField(Tasks, backref='settings', unique=True, on_delete='CASCADE')
        audio_codec = pw.TextField(null=False)
        audio_stream_encoder = pw.TextField(null=False)
        audio_codec_cloning = pw.TextField(null=False)
        audio_stream_encoder_cloning = pw.TextField(null=False)
        audio_stereo_stream_bitrate = pw.TextField(null=False)
        cache_path = pw.TextField(null=False)
        config_path = pw.TextField(null=False)
        keep_filename_history = pw.BooleanField(null=False)
        debugging = pw.BooleanField(null=False)
        enable_audio_encoding = pw.BooleanField(null=False)
        enable_audio_stream_transcoding = pw.BooleanField(null=False)
        enable_audio_stream_stereo_cloning = pw.BooleanField(null=False)
        enable_inotify = pw.BooleanField(null=False)
        enable_video_encoding = pw.BooleanField(null=False)
        library_path = pw.TextField(null=False)
        log_path = pw.TextField(null=False)
        number_of_workers = pw.IntegerField(null=False)
        out_container = pw.TextField(null=False)
        remove_subtitle_streams = pw.BooleanField(null=False)
        run_full_scan_on_start = pw.BooleanField(null=False)
        schedule_full_scan_minutes = pw.IntegerField(null=False)
        search_extensions = pw.TextField(null=False)
        video_codec = pw.TextField(null=False)
        video_stream_encoder = pw.TextField(null=False)
        video_stream_encoder = pw.TextField(null=False)

    @migrator.create_model
    class TaskProbe(pw.Model):
        task_id = pw.ForeignKeyField(Tasks, backref='probe', on_delete='CASCADE')
        abspath = pw.TextField(null=False)
        basename = pw.TextField(null=False)
        bit_rate = pw.TextField(null=False)
        format_long_name = pw.TextField(null=False)
        format_name = pw.TextField(null=False)
        size = pw.TextField(null=False)
        duration = pw.TextField(null=False)

    @migrator.create_model
    class TaskProbeStreams(pw.Model):
        taskprobe_id = pw.ForeignKeyField(TaskProbe, backref='streams', on_delete='CASCADE')
        codec_type = pw.TextField(null=False)
        codec_long_name = pw.TextField(null=False)
        avg_frame_rate = pw.TextField(null=False)
        bit_rate = pw.TextField(null=False)
        coded_height = pw.TextField(null=False)
        coded_width = pw.TextField(null=False)
        height = pw.TextField(null=False)
        width = pw.TextField(null=False)
        duration = pw.TextField(null=False)
        channels = pw.TextField(null=False)
        channel_layout = pw.TextField(null=False)


def rollback(migrator, database, fake=False, **kwargs):
    """
    Remove the Tasks Models
    """
    migrator.remove_model('Tasks', cascade=True)
