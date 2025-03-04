from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)
    
class TestModel(models.Model):
    title = models.CharField(max_length=100)
    image = models.CharField(max_length=200, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    
    
