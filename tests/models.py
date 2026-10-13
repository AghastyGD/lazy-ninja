from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)


class Tag(models.Model):
    name = models.CharField(max_length=100)


class Detail(models.Model):
    label = models.CharField(max_length=100)
    
class TestModel(models.Model):
    title = models.CharField(max_length=100)
    image = models.CharField(max_length=200, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    detail = models.OneToOneField(Detail, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)


class TaggedModel(models.Model):
    title = models.CharField(max_length=100)
    tags = models.ManyToManyField(Tag, through="TaggedModelTag")


class TaggedModelTag(models.Model):
    item = models.ForeignKey(TaggedModel, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    
    
