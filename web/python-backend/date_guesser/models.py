from django.db import models

# Create your models here.

class Item(models.Model):
    item = models.CharField(max_length=200, primary_key=True, blank=False) # Combine id/page
    # page = models.IntegerField(primary_key=True)
    date = models.DateField("The (parsed) date this item was created at (e.g. when an illustration was drawn or a photograph was taken).")
    date_raw = models.CharField("The creation date, as stated in the original entry.", max_length=200)
    skip = models.BooleanField("Items with \"skip\" enabled are not used.", default=False)

    def __str__(self) -> str:
        return self.item

class ImageFormat(models.Model):
    name = models.CharField(max_length=200)
    ending = models.CharField(max_length=50)

    def __str__(self) -> str:
        return self.name

class Image(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    image_id = models.CharField(max_length=64, primary_key=True, blank=False)
    format = models.ForeignKey(ImageFormat, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.image_id + self.ending if self.ending is not None else ""

class Stats(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    views = models.PositiveIntegerField(default=0)
    skips = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.item}: {self.views}/{self.skips}"

class Guess(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    guess = models.IntegerField()
    datetime = models.DateTimeField("Time the guess was submitted")

    def __str__(self) -> str:
        return f"{self.datetime}: {self.guess}"

class Collection(models.Model):
    collection = models.CharField(max_length=200, primary_key=True)

    def __str__(self) -> str:
        return self.collection

class CollectionItem(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.collection}/{self.item}"

class Citation(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    style = models.CharField(max_length=100, primary_key=True)
    citation = models.TextField()

    def __str__(self) -> str:
        return f"[{self.style}] {self.citation}"

class Report(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    reason = models.TextField()
    datetime = models.DateTimeField()

    def __str__(self) -> str:
        return f"{self.datetime}: {self.reason}"