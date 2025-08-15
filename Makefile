run:
	uvicorn main:app --reload

migrate:
	aerich migrate 

applymigrate:
	aerich upgrade 

create:
	aerich init-db
