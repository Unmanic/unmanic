"""Peewee migrations -- 009_update_foreign_key_on_update_cascade.py.

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

from unmanic.libs.unmodels.taskprobe import TaskProbe
from unmanic.libs.unmodels.taskprobestreams import TaskProbeStreams
from unmanic.libs.unmodels.tasks import Tasks
from unmanic.libs.unmodels.tasksettings import TaskSettings

try:
    import playhouse.postgres_ext as pw_pext
except ImportError:
    pass

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""
    # Re-create the Tasks table
    migrator.remove_model(Tasks, cascade=True)
    migrator.create_table(Tasks)

    # Re-create the TaskSettings table
    migrator.remove_model(TaskSettings, cascade=True)
    migrator.create_table(TaskSettings)

    # Re-create the TaskProbe table
    migrator.remove_model(TaskProbe, cascade=True)
    migrator.create_table(TaskProbe)

    # Re-create the TaskProbeStreams table
    migrator.remove_model(TaskProbeStreams, cascade=True)
    migrator.create_table(TaskProbeStreams)



def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""

