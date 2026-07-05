const API = "/api";

function token() {
    return localStorage.getItem("token");
}

async function api(url, options = {}) {

    options.headers = options.headers || {};

    const t = token();

    if (t) {
        options.headers["Authorization"] = "Bearer " + t;
    }

    options.credentials = "same-origin";

    const response = await fetch(API + url, options);

    if (response.status === 401) {

        localStorage.removeItem("token");
        localStorage.removeItem("refresh");

        window.location.href = "/login/";

        return null;
    }

    // DELETE => 204 No Content
    if (response.status === 204) {
        return true;
    }

    const text = await response.text();

    const data = text ? JSON.parse(text) : {};

    if (!response.ok) {
        throw data;
    }

    return data;
}

function apiGet(url) {

    return api(url);

}

function apiPost(url, data) {

    return api(url, {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify(data)

    });

}

function apiPut(url, data) {

    return api(url, {

        method: "PUT",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify(data)

    });

}

function apiPatch(url, data) {

    return api(url, {

        method: "PATCH",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify(data)

    });

}

function apiDelete(url) {

    return api(url, {

        method: "DELETE"

    });

}