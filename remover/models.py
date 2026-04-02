from django.db import models

class ImageUpload(models.Model):
    image = models.ImageField(upload_to='uploads/')
    output = models.ImageField(upload_to='outputs/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image {self.id}"