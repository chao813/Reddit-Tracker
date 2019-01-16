from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from django.conf import settings


# Create your models here.
class Profile(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	image = models.ImageField(default='default.jpg', upload_to='profile_pics')

	def __str__(self):
		return "{} Profile".format(self.user.username)

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)

		img = Image.open(self.image.path)

		if img.height > 300 or img.width > 300:
			output_size = (300, 300)
			img.thumbnail(output_size)
			img.save(self.image.path)


class Input(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	keyword = models.CharField(blank=False, null=True, max_length = 80)
	subreddit = models.CharField(blank=False, null=True, max_length = 80)
	scan_type = models.CharField(max_length= 20, default=False, choices=(('post', 'Post'),('comment','Comment')))
	enter_email_or_phone_number = models.CharField(blank=False, null=True, max_length = 80, help_text='Phone numbers have to be in +1XXXXXXXXXX format')
	disable = models.BooleanField(default=False, help_text='Check box to disable tracking')

