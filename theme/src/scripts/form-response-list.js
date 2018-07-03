import queryString from "query-string";


var bulkActions = document.querySelector("#bulk-actions");

var selectedResponsesCheckboxes = document.querySelectorAll("input[name='selected_responses']");
var selectAllCheckbox = document.getElementById("selectAllResponsesCheckbox");

var pagePicker = document.getElementById("page-picker");
if (pagePicker) {
    pagePicker.addEventListener("change", function (event) {
        const currentSearch = queryString.parse(window.location.search);
        currentSearch.page = event.target.value;
        window.location.search = queryString.stringify(currentSearch)
    });
}

const pageSizePicker = document.getElementById("page-size-picker");
if (pageSizePicker) {
    pageSizePicker.addEventListener("change", function (event) {
        const currentSearch = queryString.parse(window.location.search);
        currentSearch.paginate_by = event.target.value;
        window.location.search = queryString.stringify(currentSearch)
    });
}

function updateFilterVisibility(){
    var selectedCount = document.querySelectorAll("input[name='selected_responses']:checked").length;
    var submitButton = bulkActions.querySelector("input[type='submit']");
    submitButton.value = submitButton.dataset.template.replace("COUNT", selectedCount);
    if (selectedCount > 0){
        bulkActions.classList.add("slidein");
    } else {
        bulkActions.classList.remove("slidein");
    }
}

function updateSelectAllState(){
    var values = [].slice.call(selectedResponsesCheckboxes);
    var allChecked = values.every(function(checkbox) { return checkbox.checked; });
    var noneChecked = values.every(function(checkbox) { return !checkbox.checked; });
    // need to disable indeterminate for checked to be read
    selectAllCheckbox.indeterminate = false;
    if (allChecked) {
        selectAllCheckbox.checked = true;
    } else if (noneChecked) {
        selectAllCheckbox.checked = false;
    } else {
        selectAllCheckbox.indeterminate = true;
    }
}

selectedResponsesCheckboxes.forEach(function(input) {
    input.onclick = function() {
        updateFilterVisibility();
        updateSelectAllState();
    }
});


selectAllCheckbox.addEventListener("click", function(event){
    selectedResponsesCheckboxes.forEach(function(input){
        input.checked = event.target.checked;
        updateFilterVisibility();
    });
});


updateFilterVisibility();
