from django.db import models
from django.utils.translation import gettext


class ProjectBaseModel(models.Model):
	created_ts = models.DateTimeField(auto_now_add=True, verbose_name=gettext('Created Time'))
	updated_ts = models.DateTimeField(auto_now=True, verbose_name=gettext('Updated Time'))

	class Meta:
		abstract = True
