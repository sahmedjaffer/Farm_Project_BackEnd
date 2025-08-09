from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator


class Flight (Model):
    id = fields.IntField(pk=True)
    departure_airport_info = fields.CharField (max_length=100)
    arrival_airport_info=fields.CharField (max_length=30)
    outbound_price= fields.CharField (max_length=10)
    outbound_currency= fields.CharField (max_length=30)
    outbound_duration_hours=fields.CharField (max_length=3)
    outbound_departure_time=fields.CharField (max_length=70)
    outbound_arrival_time=fields.CharField (max_length=70)
    outbound_cabin_class = fields.TextField()
    outbound_flight_number=fields.CharField (max_length=70)
    outbound_carrier = fields.TextField()
    return_price= fields.CharField (max_length=10)
    return_currency= fields.CharField (max_length=30)
    return_duration_hours=fields.CharField (max_length=3)
    return_departure_time=fields.CharField (max_length=70)
    return_arrival_time=fields.CharField (max_length=70)
    return_cabin_class = fields.TextField()
    return_flight_number=fields.CharField (max_length=70)
    return_carrier = fields.TextField()
    related_user = fields.ForeignKeyField("models.User", related_name='selected_flight')
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)





flight_pydantic = pydantic_model_creator(Flight, name ="Flight")
flight_pydanticIn = pydantic_model_creator(Flight, name="FlightIn", exclude_readonly = True)