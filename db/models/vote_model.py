from pymongo.write_concern import WriteConcern
from pymodm import fields, MongoModel


class Vote(MongoModel):
    title = fields.CharField()
    cases = fields.ListField()
    is_completed = fields.BooleanField(default=False)
    chat_id = fields.IntegerField()
    voted_users = fields.ListField()

    class Meta:
        write_concern = WriteConcern(j=True)
        connection_alias = "votes"
