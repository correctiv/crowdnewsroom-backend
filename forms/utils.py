import csv

from django.urls import reverse

from forms.models import FormInstance, FormResponse


def create_form_csv(form, investigation_slug, build_absolute_uri, io_object):
    form_instances = FormInstance.objects.filter(form_id=form.id)
    responses = FormResponse.objects.filter(form_instance__form_id=form.id).order_by("id").all()

    fields = set()
    for instance in form_instances:
        fields |= get_keys(instance)

    writer = csv.DictWriter(io_object, fieldnames=sorted(fields), extrasaction='ignore')
    writer.writeheader()
    for form_response in responses:
        try:
            row = form_response.json
            path = reverse("response_details", kwargs={"investigation_slug": investigation_slug,
                                                       "form_slug": form.slug,
                                                       "response_id": form_response.id})
            url = build_absolute_uri(path)
            meta_data = {"meta_version": form_response.form_instance.version,
                         "meta_url": url,
                         "meta_status": form_response.get_status_display(),
                         "meta_email": form_response.email,
                         "meta_submission_date": form_response.submission_date}
            row.update(meta_data)
            writer.writerow(row)

        except TypeError:
            print("Skipping row")
        except KeyError:
            print("Skipping row")


def get_keys(form_instance: FormInstance):
    keys = form_instance.json_properties
    file_keys = _get_file_keys(form_instance)
    non_file_fields = keys - file_keys
    extra_fields = {"url", "version", "status", "email", "submission_date"}
    fields = non_file_fields | {"meta_{}".format(field) for field in extra_fields}
    return fields


def _get_file_keys(form_instance: FormInstance):
    # TODO: Signature does not work
    file_widgets = ['signatureWidget', 'fileWidget']

    file_keys = set()

    ui_schema = form_instance.ui_schema_json
    for step in form_instance.form_json:
        schema = step["schema"]
        for (property_name, property_values) in schema["properties"].items():
            if ui_schema.get(schema["slug"], {}).get(property_name, {}).get("ui:widget") in file_widgets:
                file_keys.add(property_name)
            elif property_values.get("format") == "data-url":
                file_keys.add(property_name)
            elif property_values.get("type") == "array" \
                    and property_values.get("items", {}).get("format") == "data-url":
                file_keys.add(property_name)

    return file_keys
