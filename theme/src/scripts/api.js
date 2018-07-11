import  Cookie  from "js-cookie";

const authorizedFetch = (url, settings) =>
  fetch(url, Object.assign({ credentials: "same-origin" }, settings)).then(
    response => response.json()
  );

const mutatingFetch = (url, settings) => {
  const csrfValue = Cookie.get("csrftoken");
  const baseSettings = {
    headers: {
      "content-type": "application/json",
      "X-CSRFToken": csrfValue
    }
  };

  return authorizedFetch(url, Object.assign(baseSettings, settings));
}

const authorizedPUT = (url, settings) => {
  return mutatingFetch(url, Object.assign({method: "PATCH"}, settings));
};

const authorizedPOST = (url, settings) => {
  return mutatingFetch(url, Object.assign({method: "POST"}, settings));
};

const authorizedDELETE = (url, settings) => {
  const csrfValue = Cookie.get("csrftoken");
  const baseSettings = {
    method: "DELETE",
    headers: {
      "content-type": "application/json",
      "X-CSRFToken": csrfValue
    },
    credentials: "same-origin"
  };

  return fetch(url, Object.assign(baseSettings, settings));
};

export { authorizedFetch, authorizedPUT, authorizedPOST, authorizedDELETE };
