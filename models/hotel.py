from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator


class Hotel (Model):
    id = fields.IntField(pk=True)
    hotel_name = fields.CharField (max_length=100)
    hotel_review_score_word=fields.CharField (max_length=30)
    hotel_review_score= fields.FloatField ()
    hotel_gross_price= fields.CharField (max_length=30)
    hotel_currency=fields.CharField (max_length=3)
    hotel_check_in=fields.CharField (max_length=70)
    hotel_check_out=fields.CharField (max_length=70)
    hotel_photo_url= fields.CharField (max_length=255, null=True)
    related_user = fields.ForeignKeyField("models.User", related_name='selected_hotel')
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)



hotel_pydantic = pydantic_model_creator(Hotel, name ="Hotel")
hotel_pydanticIn = pydantic_model_creator(Hotel, name="HotelIn", exclude_readonly = True)