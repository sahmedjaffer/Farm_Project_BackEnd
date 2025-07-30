from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator



class Preferences (Model):
    id = fields.IntField(pk=True)
    user_id = fields.ForeignKeyField('models.User', related_name= "user_preferences")
    preferred_countries = fields.CharField(max_length=100)
    preferred_activities = fields.CharField(max_length=100)
    preferred_hotels = fields.CharField(max_length=100)



#creare pydantic models
product_pydantic = pydantic_model_creator(Preferences, name ="Preferences")
product_pydanticIn = pydantic_model_creator(Preferences, name="PreferencesIn", exclude_readonly = True)