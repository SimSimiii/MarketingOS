"""MarketingOS back-office.

Imports `app.*` - the product package - which the buildspec vendors into this
directory at build time so the Lambda bundle carries one copy of the models
and services with zero drift. Locally, put the product backend on PYTHONPATH:

    PYTHONPATH=../../backend uvicorn admin.main:app --port 8001
"""
