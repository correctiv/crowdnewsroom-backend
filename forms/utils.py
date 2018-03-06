import csv

from django.urls import reverse

from forms.models import FormInstance, FormResponse


def create_form_csv(form_id, investigation_id, request, io_object):
    form_instances = FormInstance.objects.filter(form_id=form_id)
    responses = FormResponse.objects.filter(form_instance__form_id=form_id).all()

    fields = set()
    for instance in form_instances:
        fields |= get_keys(instance)

    writer = csv.DictWriter(io_object, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    for form_response in responses:
        try:
            row = form_response.json["formData"]
            path = reverse("response_details", kwargs={"investigation_id": investigation_id,
                                                       "form_id": form_id,
                                                       "response_id": form_response.id})
            url = request.build_absolute_uri(path)
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


def get_keys(form_instance):
    keys = set(form_instance.form_json["properties"].keys())
    file_keys = _get_file_keys(form_instance)
    non_file_fields = keys - file_keys
    extra_fields = {"url", "version", "status", "email", "submission_date"}
    fields = non_file_fields | {"meta_{}".format(field) for field in extra_fields}
    return fields


def _get_file_keys(form_instance):
    file_widgets = ['signatureWidget', 'fileWidget']
    non_property_keys = ["ui:order"]
    return {key for (key, value)
            in form_instance.ui_schema_json.items()
            if key not in non_property_keys
            and value.get("ui:widget") in file_widgets}