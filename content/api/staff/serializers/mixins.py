from django.utils.text import slugify
from rest_framework import serializers

from content.sanitize import sanitize_html


def unique_slug(model, value, instance=None):
    base = slugify(value) or "item"
    slug = base
    index = 2
    queryset = model.objects.all()
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)
    while queryset.filter(slug=slug).exists():
        slug = f"{base}-{index}"
        index += 1
    return slug


def wants_new_slug(serializer, attrs) -> bool:
    """True when the slug should be (re)generated from the title.

    A PATCH that does not mention `slug` must leave it alone. Regenerating it
    on every partial update rewrote hand-picked public URLs — PATCHing only a
    class's fee turned `/curriculum/kg` into `/curriculum/kindergarten` and
    broke every existing link to it. Sending `slug: ""` still means
    "rebuild it from the title".
    """
    if "slug" in attrs:
        return not attrs["slug"]
    return not getattr(serializer.instance, "slug", "")


class SanitizeHtmlMixin:
    """Cleans article HTML on the fields named in html_fields."""

    html_fields: tuple[str, ...] = ()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        for name in self.html_fields:
            value = attrs.get(name)
            if isinstance(value, str):
                attrs[name] = sanitize_html(value)
        return attrs


class SlugFromTitleMixin:
    def validate(self, attrs):
        attrs = super().validate(attrs)
        if wants_new_slug(self, attrs):
            title = attrs.get("title_en") or getattr(self.instance, "title_en", "")
            attrs["slug"] = unique_slug(self.Meta.model, title, self.instance)
        return attrs


class ClearUploadedImagesMixin:
    uploaded_image_fields: tuple[str, ...] = ()

    def to_internal_value(self, data):
        if hasattr(data, "copy"):
            data = data.copy()
        mutable = getattr(data, "_mutable", None)
        if mutable is False:
            data._mutable = True
        for name in self.uploaded_image_fields:
            value = data.get(name) if hasattr(data, "get") else None
            if isinstance(value, str):
                del data[name]
        if mutable is False:
            data._mutable = False
        return super().to_internal_value(data)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        for name in self.uploaded_image_fields:
            url_field = f"{name}_url"
            has_file = bool(attrs.get(name))
            clearing = bool(attrs.get(f"clear_{name}"))
            if (
                url_field in attrs
                and not attrs.get(url_field)
                and not has_file
                and not clearing
            ):
                attrs.pop(url_field)
        return attrs

    def _clear_uploaded_images(self, instance, validated_data):
        for name in self.uploaded_image_fields:
            if not validated_data.pop(f"clear_{name}", False):
                continue
            current = getattr(instance, name)
            if current:
                current.delete(save=False)
            setattr(instance, name, None)
            url_field = f"{name}_url"
            if hasattr(instance, url_field):
                setattr(instance, url_field, "")

    def _drop_urls_replaced_by_uploads(self, validated_data):
        field_names = {field.name for field in self.Meta.model._meta.fields}
        for name in self.uploaded_image_fields:
            if not validated_data.get(name):
                continue
            url_field = f"{name}_url"
            if url_field in field_names:
                validated_data[url_field] = ""

    def update(self, instance, validated_data):
        self._clear_uploaded_images(instance, validated_data)
        self._drop_urls_replaced_by_uploads(validated_data)
        return super().update(instance, validated_data)

    def create(self, validated_data):
        for name in self.uploaded_image_fields:
            validated_data.pop(f"clear_{name}", None)
        self._drop_urls_replaced_by_uploads(validated_data)
        return super().create(validated_data)
