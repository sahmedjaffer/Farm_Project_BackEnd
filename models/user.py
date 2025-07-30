from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
import uuid



class User (Model):
    id = fields.UUIDField(pk=True, default = uuid.uuid4)
    first_name = fields.CharField(max_length=30, nullable=False)
    las_name = fields.CharField(max_length=30, nullable=False)
    email = fields.CharField(max_length=100)
    hashed_password = fields.CharField(max_length=100)