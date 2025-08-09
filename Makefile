run:
	uvicorn main:app --reload

migrate:
	aerich migrate

applymigrate:
	aerich upgrade
