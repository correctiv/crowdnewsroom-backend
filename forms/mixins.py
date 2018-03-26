from slugify import slugify_de  # TODO


def slugify(value):
    return slugify_de(value, to_lower=True)


class UniqueSlugMixin(object):
    def save(self, *args, **kwargs):
        """
        Sets the slug of the instance based on the instance-method get_slug
        if the slugified name and the slug in the database aren't equal
        """
        if not self.slug:
            self.slug = slugify(self.name)
        if self.__class__.objects.exclude(pk=self.pk).filter(slug=self.slug).exists():
            self.slug = '{}-{}'.format(self.slug, str(self.pk))
        super().save(*args, **kwargs)
