from peewee import *
from model.base_model import BaseModel
from playhouse.postgres_ext import DateTimeTZField

# import model.commit


class Repository(BaseModel):
    url = TextField(primary_key=True)
    # app_id = CharField()
    name = CharField(null=True)
    authors_num = IntegerField(null=True)
    commits_num = IntegerField(null=True)
    files_num = BigIntegerField(null=True)
    last_commit_date = DateTimeTZField(null=True)
    first_commit_date = DateTimeTZField(null=True)
    sloc = BigIntegerField(null=True)
    logging_loc = BigIntegerField(null=True)
    # analyzed_date = DateTimeTZField(null=True)

    def get_non_merge_commits(self):
        import model.commit
        return self.commits.where(model.commit.Commit.is_merge_commit is False)
