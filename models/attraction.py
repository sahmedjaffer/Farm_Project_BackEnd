from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator


class Attraction (Model):
    id = fields.IntField(pk=True)
    attraction_name = fields.CharField (max_length=100)
    attraction_description=fields.TextField()
    attraction_price= fields.CharField (max_length=30)
    attraction_availability_date= fields.CharField (max_length=30)
    attraction_average_review=fields.CharField (max_length=10)
    attraction_total_review=fields.CharField (max_length=10)
    attraction_photo=fields.CharField (max_length=200)
    attraction_daily_timing= fields.CharField (max_length=20)
    related_user = fields.ForeignKeyField("models.User", related_name='selected_attraction')
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)



attraction_pydantic = pydantic_model_creator(Attraction, name ="Attraction")
attraction_pydanticIn = pydantic_model_creator(Attraction, name="AttractionIn", exclude_readonly = True)