from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower
from django.core.files import File
from django.db.models import Min, Max
from django.core.exceptions import ObjectDoesNotExist
import datetime

# Create your models here.


class Provider(models.Model):
    short_name = models.CharField(max_length=100, blank=False, primary_key=True)
    long_name = models.CharField(max_length=200, blank=False)
    url = models.CharField(max_length=512, null=True)

    def __str__(self) -> str:
        return self.long_name


class License(models.Model):
    short_name = models.CharField(max_length=100, blank=False, primary_key=True)
    long_name = models.CharField(max_length=200)

    def __str__(self) -> str:
        return f"{self.long_name} ({self.short_name})"


class Item(models.Model):
    id = models.CharField(
        max_length=64, primary_key=True, blank=False
    )  # SHA256 hash of item/page
    item = models.CharField(max_length=200)
    page = models.IntegerField(null=True, blank=True)
    image_url = models.CharField(max_length=512, null=True, blank=True)
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE)
    date = models.DateField(
        "The (parsed) date this item was created at (e.g. when an illustration was drawn or a photograph was taken)."
    )
    date_raw = models.CharField(
        "The creation date, as stated in the original entry.",
        max_length=200,
        blank=True,
        null=True,
    )
    label = models.CharField(
        "Human readable label.", max_length=200, blank=True, null=True
    )
    alt_label = models.CharField(
        "Alternative human readable label.", max_length=200, blank=True, null=True
    )
    description = models.CharField(
        "Description of the item.", max_length=500, blank=True, null=True
    )
    date_precision = models.IntegerField(
        "Date precision as defined by Wikidata.",
        choices=[
            (0, "billion years"),
            (3, "million years"),
            (4, "hundred thousand years"),
            (6, "millennium"),
            (7, "century"),
            (8, "decade"),
            (9, "year"),
            (10, "month"),
            (11, "day"),
            (12, "hour"),
            (13, "minute"),
            (14, "second"),
        ],
        blank=True,
        null=True,
    )
    skip = models.BooleanField('Items with "skip" enabled are not used.', default=False)

    def __str__(self) -> str:
        return self.id

    @classmethod
    def min_year(cls):
        try:
            return cls.objects.all().aggregate(Min("date"))["date__min"].year
        except ObjectDoesNotExist:
            return 0

    @classmethod
    def max_year(cls):
        try:
            return cls.objects.all().aggregate(Max("date"))["date__max"].year
        except ObjectDoesNotExist:
            return datetime.datetime.now().year

    def get_absolute_url(self):
        return f"{self.id}/"


# class ImageFormat(models.Model):
#     name = models.CharField(max_length=200)
#     ending = models.CharField(max_length=50)

#     def __str__(self) -> str:
#         return self.name


class Image(models.Model):
    item = models.OneToOneField(Item, on_delete=models.CASCADE)
    image_id = models.CharField(max_length=64, primary_key=True, blank=False)
    # format = models.ForeignKey(ImageFormat, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="historical_images")
    license = models.ForeignKey(License, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.image_id

    def set_image(self, path: str, name: str):
        self.image.save(name, File(open(path, "rb")))
        self.save()


class Stats(models.Model):
    class Meta:
        verbose_name_plural = "stats"

    item = models.OneToOneField(Item, on_delete=models.CASCADE, primary_key=True)
    views = models.PositiveIntegerField(default=0)
    skips = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.item}: {self.views}/{self.skips}"


class Guess(models.Model):
    class Meta:
        verbose_name_plural = "guesses"

    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    guess = models.IntegerField()
    datetime = models.DateTimeField("Time the guess was submitted", auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.datetime}: Off by {abs(self.guess - self.item.date.year)}"


class Collection(models.Model):
    collection = models.CharField(max_length=200, primary_key=True)
    items = models.ManyToManyField(Item)

    def __str__(self) -> str:
        return self.collection


# class CollectionItem(models.Model):
#     item = models.ForeignKey(Item, on_delete=models.CASCADE)
#     collection = models.ForeignKey(Collection, on_delete=models.CASCADE)

#     def __str__(self) -> str:
#         return f"{self.collection}/{self.item}"


class Citation(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    style = models.CharField(max_length=100)
    citation = models.TextField()

    # class Meta:
    #     constraints = [
    #         UniqueConstraint( # Make the combination of item/style unique
    #             Lower("item"),
    #             Lower("style"),
    #             name="item_style_unique"
    #         )
    #     ]

    def __str__(self) -> str:
        return self.item.id + "/" + self.style


class Report(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    reason = models.TextField()
    datetime = models.DateTimeField()

    def __str__(self) -> str:
        return f"{self.datetime}: {self.reason}"