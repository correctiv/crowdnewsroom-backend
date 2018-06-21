import queryString from "query-string";


var bulkActions = document.querySelector("#bulk-actions");
bulkActions.classList.add("d-none");

var selectedResponsesCheckboxes = document.querySelectorAll("input[name='selected_responses']");
var selectAllCheckbox = document.getElementById("selectAllResponsesCheckbox");

var pagePicker = document.getElementById("page-picker");
pagePicker.addEventListener("change", function(event){
    console.log(event);
    const currentSearch = queryString.parse(window.location.search);
    currentSearch.page = event.target.value;
    console.log(currentSearch);
    window.location.search = queryString.stringify(currentSearch)
});

function updateFilterVisibility(){
    var selectedCount = document.querySelectorAll("input[name='selected_responses']:checked").length;
    if (selectedCount > 0){
        bulkActions.classList.remove("d-none");
        var submitButton = bulkActions.querySelector("input[type='submit']");
        submitButton.value = submitButton.dataset.template.replace("COUNT", selectedCount);
    } else {
        bulkActions.classList.add("d-none");
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
