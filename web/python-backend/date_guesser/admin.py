from django.contrib import admin

from .models import Item, Image, Collection, Stats, Guess, Report, Citation, License, Provider #, CollectionItem #, ImageFormat, 

#admin.site.register(CollectionItem)
#admin.site.register(ImageFormat)
admin.site.register(Citation)
admin.site.register(Collection)
admin.site.register(Guess)
admin.site.register(Image)
admin.site.register(Item)
admin.site.register(License)
admin.site.register(Provider)
admin.site.register(Report)
admin.site.register(Stats)