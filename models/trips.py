from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator



class Trips (Model):
    id = fields.IntField(pk=True)






product_pydantic = pydantic_model_creator(Trips, name ="Trips")
product_pydanticIn = pydantic_model_creator(Trips, name="TripsIn", exclude_readonly = True)