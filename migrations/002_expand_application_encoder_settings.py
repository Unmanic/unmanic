"""Peewee migrations -- 002_expand_application_encoder_settings.py.

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

import peewee as pw

try:
    import playhouse.postgres_ext as pw_pext
except ImportError:
    pass

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    # Add enable_video_encoding field to Settings Model
    migrator.add_fields('settings', enable_video_encoding=pw.BooleanField(null=False, default=True))
    # Add enable_audio_encoding field to Settings Model
    migrator.add_fields('settings', enable_audio_encoding=pw.BooleanField(null=False, default=True))
    # Add enable_audio_stream_transcoding field to Settings Model
    migrator.add_fields('settings', enable_audio_stream_transcoding=pw.BooleanField(null=False, default=True))
    # Add audio_stream_encoder field to Settings Model
    migrator.add_fields('settings', audio_stream_encoder=pw.TextField(null=False, default='aac'))
    # Add enable_audio_stream_stereo_cloning field to Settings Model
    migrator.add_fields('settings', enable_audio_stream_stereo_cloning=pw.BooleanField(null=False, default=True))
    # Add audio_codec_cloning field to Settings Model
    migrator.add_fields('settings', audio_codec_cloning=pw.TextField(null=False, default='aac'))
    # Add audio_stream_encoder_cloning field to Settings Model
    migrator.add_fields('settings', audio_stream_encoder_cloning=pw.TextField(null=False, default='aac'))


def rollback(migrator, database, fake=False, **kwargs):
    # Remove the enable_video_ecoding field from the Settings Model
    migrator.remove_fields('settings', 'enable_video_ecoding', cascade=True)
    # Remove the enable_audio_encoding field from the Settings Model
    migrator.remove_fields('settings', 'enable_audio_encoding', cascade=True)
    # Remove the enable_audio_stream_transcoding field from the Settings Model
    migrator.remove_fields('settings', 'enable_audio_stream_transcoding', cascade=True)
    # Remove the audio_stream_encoder field from the Settings Model
    migrator.remove_fields('settings', 'audio_stream_encoder', cascade=True)
    # Remove the enable_audio_stream_stereo_cloning field from the Settings Model
    migrator.remove_fields('settings', 'enable_audio_stream_stereo_cloning', cascade=True)
    # Remove the audio_codec_cloning field from the Settings Model
    migrator.remove_fields('settings', 'audio_codec_cloning', cascade=True)
    # Remove the audio_stream_encoder_cloning field from the Settings Model
    migrator.remove_fields('settings', 'audio_stream_encoder_cloning', cascade=True)
