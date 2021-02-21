"""Peewee migrations -- 008_add_hardware_decoding_settings.py.

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
    """Write your migrations here."""
    # Add enable_hardware_accelerated_decoding field to Settings Model
    migrator.add_fields('settings', enable_hardware_accelerated_decoding=pw.BooleanField(null=False, default=False))
    # Add enable_hardware_accelerated_decoding field to TaskSettings Model
    migrator.add_fields('tasksettings', enable_hardware_accelerated_decoding=pw.BooleanField(null=False, default=False))
    # Add enable_hardware_accelerated_decoding field to HistoricTaskSettings Model
    migrator.add_fields('historictasksettings',
                        enable_hardware_accelerated_decoding=pw.BooleanField(null=False, default=False))


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""
    # Remove the enable_hardware_accelerated_decoding field from the Settings Model
    migrator.remove_fields('settings', 'enable_hardware_accelerated_decoding', cascade=True)
    # Remove the enable_hardware_accelerated_decoding field from the TaskSettings Model
    migrator.remove_fields('tasksettings', 'enable_hardware_accelerated_decoding', cascade=True)
    # Remove the enable_hardware_accelerated_decoding field from the HistoricTaskSettings Model
    migrator.remove_fields('historictasksettings', 'enable_hardware_accelerated_decoding', cascade=True)
