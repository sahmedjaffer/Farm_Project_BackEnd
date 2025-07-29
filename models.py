from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
import uuid


class Product(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=30, nullable=False)
    quantity_in_stock = fields.IntField(dafault=0)
    quantity_sold= fields.IntField(default=0)
    unit_price = fields.DecimalField(default=0.00, max_digits=8, decimal_places=3)
    revenue= fields.DecimalField(default=0.00, max_digits=20, decimal_places=3)
    supplied_by = fields.ForeignKeyField('models.Supplier', related_name= "goods_supplied")


class Supplier(Model):
    id = fields.IntField(pk=True)
    uuid = fields.UUIDField(default = uuid.uuid4)
    name = fields.CharField(max_length=30)
    company = fields.CharField(max_length=30)
    email = fields.CharField(max_length=100)
    phone = fields.CharField(max_length=15)
    
#creare pydantic models
product_pydantic = pydantic_model_creator(Product, name ="Product")
product_pydanticIn = pydantic_model_creator(Product, name="ProductIn", exclude_readonly = True)

supplier_pydantic = pydantic_model_creator(Supplier, name = "Supplier")
supplier_pydanticIn = pydantic_model_creator(Supplier, name = "SupplierIn", exclude_readonly = True)