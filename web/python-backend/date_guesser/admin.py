from django.contrib import admin

from .models import Item, Image, ImageFormat, Collection, Stats, Guess, Report, Citation, CollectionItem

admin.site.register(Citation)
admin.site.register(Collection)
admin.site.register(CollectionItem)
admin.site.register(Guess)
admin.site.register(Image)
admin.site.register(ImageFormat)
admin.site.register(Item)
admin.site.register(Report)
admin.site.register(Stats)