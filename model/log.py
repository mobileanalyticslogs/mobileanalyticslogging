from peewee import *
from model.base_model import BaseModel
import model.commit


class Log(BaseModel):

    commit = ForeignKeyField(model.commit.Commit, db_column='commit_fk', related_name='logs', on_delete='CASCADE')
    file_path = TextField()
    embed_method = TextField()
    change_type = CharField()
    content = TextField()
    content_update_from = TextField(null=True)
    # verbosity = CharField(null=True)
    # verbosity_type = CharField(null=True)
    # argument_type = CharField(null=True)
    # is_consistent_update = BooleanField(null=True)

    def is_type_added(self):
        return self.change_type == LogChangeType.LOG_ADDED

    def is_type_deleted(self):
        return self.change_type == LogChangeType.LOG_DELETED

    def is_type_updated(self):
        return self.change_type == LogChangeType.LOG_UPDATED


class LogChangeType(object):
    LOG_ADDED = 'LOG_ADDED'
    LOG_DELETED = 'LOG_DELETED'
    LOG_UPDATED = 'LOG_UPDATED'
