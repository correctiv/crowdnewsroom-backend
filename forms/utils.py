import csv

from django.urls import reverse

from forms.models import FormInstance, FormResponse


def create_form_csv(form, investigation_slug, build_absolute_uri, io_object, filter_params={}):
    form_instances = FormInstance.objects.filter(form_id=form.id)
    responses = FormResponse.objects\
        .filter(form_instance__form_id=form.id)\
        .filter(**filter_params)\
        .order_by("id")\
        .all()

    extra_fields = {"url", "version", "status", "email", "submission_date", "id"}
    fields = {"meta_{}".format(field) for field in extra_fields}
    for instance in form_instances:
        fields |= instance.json_properties

    writer = csv.DictWriter(io_object, fieldnames=sorted(fields), extrasaction='ignore')
    writer.writeheader()
    for form_response in responses:
        try:
            row = {}
            for field in form_response.rendered_fields():
                if field['type'] == "link":
                    row[field["json_name"]] = build_absolute_uri(field["value"])
                else:
                    row[field["json_name"]] = field["value"]

            path = reverse("response_details", kwargs={"investigation_slug": investigation_slug,
                                                       "form_slug": form.slug,
                                                       "response_id": form_response.id})
            url = build_absolute_uri(path)
            meta_data = {"meta_version": form_response.form_instance.version,
                         "meta_id": form_response.id,
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
