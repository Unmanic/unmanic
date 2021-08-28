"""Peewee migrations -- 001_rename_ffmpeg_log_to_log.py.

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
from decimal import ROUND_HALF_EVEN

try:
    import playhouse.postgres_ext as pw_pext
except ImportError:
    pass

SQL = pw.SQL

"""NOTES:
The migrator function 'rename_field' has a bug: https://github.com/klen/peewee_migrate/issues/99
The simple work-around to this was to skip this method and just directly append a migration to the migrator's ops list.
Eg. `migrator.ops.append(migrator.migrator.rename_column('tasks', 'ffmpeg_log', 'log'))`
"""


"""Note:
This migration is required for legacy installations.
The old Unmanic had a ffmpeg_log column which had a NOT NULL contraint on it.
If this column is left as is, no items will be able to be added to the task queue.
"""
def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""
    # Rename 'ffmpeg_log' field to 'log'' in Tasks model
    if any(cm for cm in database.get_columns('tasks') if cm.name == 'ffmpeg_log'):
        migrator.ops.append(migrator.migrator.rename_column('tasks', 'ffmpeg_log', 'log'))


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""
    # Reverse rename 'ffmpeg_log' field to 'log'' in Tasks model
    if any(cm for cm in database.get_columns('tasks') if cm.name == 'log'):
        migrator.ops.append(migrator.migrator.rename_column('tasks', 'log', 'ffmpeg_log'))
