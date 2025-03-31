from django.db import models

# Create your models here.
class StockData(models.Model):
    symbol = models.TextField(null=False)
    data = models.TextField(null=True)