from peewee import *
from model.base_model import BaseModel
from playhouse.postgres_ext import DateTimeTZField

import model.repository


class Commit(BaseModel):
    repo = ForeignKeyField(model.repository.Repository, db_column='repo_fk', related_name='commits',
                                 on_delete='CASCADE')
    commit_id = CharField()
    parent_commit_id = CharField(null=True)
    is_merge_commit = BooleanField(default=False)
    author_email = CharField(null=True)
    author_name = CharField(null=True)
    authored_date = DateTimeTZField(null=True)
    committer_email = CharField(null=True)
    committer_name = CharField(null=True)
    committed_date = DateTimeTZField(null=True)
    message = TextField(null=True)
    sloc = BigIntegerField(null=True)
    # logging_loc = BigIntegerField(null=True)
    code_churn = BigIntegerField(null=True)
    # logging_code_churn = BigIntegerField(null=True)
