import React from "react"
import { render } from 'react-dom';
import BucketPicker from "./bucketPicker";
import MultiSelectPicker from "./multiSelectPicker";


const actionsWrapper = document.getElementsByClassName("formresponse-details--actions")[0];
const id = actionsWrapper.getAttribute("data-response-id");
const investigationSlug = actionsWrapper.getAttribute("data-investigation-slug");

const bucketElement = document.getElementById("bucket-picker");
render(<BucketPicker responseId={id} />, bucketElement);

const assigneeElement = document.getElementById("assignee-picker");
render(<MultiSelectPicker responseId={id}
                          label={`${gettext("Add or delete ownership")}`}
                          property="assignees"
                          investigationSlug={investigationSlug}
                          itemToString={item => `${item.first_name} ${item.last_name}`}
                            />, assigneeElement);

const tagsElement = document.getElementById("tag-picker");
render(<MultiSelectPicker responseId={id}
                          label={`${gettext("Add or delete tag")}`}
                          property="tags"
                          investigationSlug={investigationSlug}
                          itemToString={item => item.name}
/>, tagsElement);
