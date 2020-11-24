import csv

import bugsnag
from django.urls import reverse

from forms.models import FormInstance, FormResponse


def create_form_csv(form, investigation_slug, build_absolute_uri, io_object, filter_params={}):
    form_instances = FormInstance.objects.filter(form_id=form.id)
    responses = FormResponse.objects\
        .filter(form_instance__form_id=form.id)\
        .filter(**filter_params)\
        .order_by("id")\
        .all()

    extra_fields = {"url", "version", "status",
                    "submission_date", "id", "tags", "comments"}
    fields = {"meta_{}".format(field) for field in extra_fields}
    
    for form_response in responses:
        for field in form_response.rendered_fields():
            try:
                if field['label'] != None and field['label'] != '':
                    fields.add(field['label'])
                else:
                    try:
                        if field['title'] != None and field['title'] != '':
                            fields.add(field['title'])
                        else:
                            fields.add(field['json_name'])
                    except:
                        fields.add(field['json_name'])
            except:
                try:
                    if field['title'] != None and field['title'] != '':
                        fields.add(field['title'])
                    else:
                        fields.add(field['json_name'])
                except:
                    fields.add(field['json_name'])

    writer = csv.DictWriter(io_object, fieldnames=sorted(
        fields, key=lambda x: str(x)), extrasaction='ignore')
    writer.writeheader()

    for form_response in responses:
        try:
            row = {}
            for field in form_response.rendered_fields():
                if field['type'] == 'link':
                    field['value'] = build_absolute_uri(field['value'])
                try:
                    if field['label'] != None and field['label'] != '':
                        row[field["label"]] = field["value"]
                    else:
                        try:
                            if field['title'] != None and field['title'] != '':
                                row[field["title"]] = field["value"]
                            else:
                                row[field["json_name"]] = field["value"]
                        except:
                            row[field["json_name"]] = field["value"]
                except:
                    try:
                        if field['title'] != None and field['title'] != '':
                            row[field["title"]] = field["value"]
                        else:
                            row[field["json_name"]] = field["value"]
                    except:
                        row[field["json_name"]] = field["value"]

            path = reverse("response_details", kwargs={"investigation_slug": investigation_slug,
                                                        "form_slug": form.slug,
                                                        "response_id": form_response.id})
            url = build_absolute_uri(path)
            meta_data = {"meta_version": form_response.form_instance.version,
                            "meta_id": form_response.id,
                            "meta_url": url,
                            "meta_status": form_response.get_status_display(),
                            "meta_submission_date": form_response.submission_date,
                            "meta_tags": ", ".join([tag.name.replace(",", " ")
                                                    for tag
                                                    in form_response.tags.all()]),
                            "meta_comments": ", ".join([comment.author.first_name + ' ' + comment.author.last_name + ' (' +  comment.date.strftime('%d.%m.%Y %H:%M') + '): ' 
                                                        + comment.text.replace(",", " ")
                                                    for comment
                                                    in form_response.visible_comments])}
            row.update(meta_data)

            writer.writerow(row)

        except TypeError as e:
            bugsnag.notify(e)
            print("Skipping row")
        except KeyError as e:
            bugsnag.notify(e)
            print("Skipping row")
