export const api = async (path, options = {}) => {
    const res = await fetch(`/api${path}`, {
        headers: {"Content-Type": "application/json"},
        ...options,
    });

    const isJson = res.headers.get("content-type")?.includes("application/json");
    const data = isJson ? await res.json() : null;
    const totalHeader = res.headers.get("X-Total-Count");
    const total = totalHeader ? Number(totalHeader) : null;

    return {
        ok: res.ok,
        status: res.status,
        data,
        total: Number.isFinite(total) ? total : null,
    };
};

export const createToast = (toastElement) => {
    let timer = null;

    const showToast = (message, isError = false) => {
        if (!toastElement) return;
        toastElement.textContent = message || "";
        toastElement.classList.toggle("is-visible", Boolean(message));
        toastElement.classList.toggle("is-error", Boolean(message) && isError);
        if (timer) clearTimeout(timer);
        if (message) {
            timer = setTimeout(() => {
                toastElement.classList.remove("is-visible", "is-error");
                toastElement.textContent = "";
            }, 4000);
        }
    };

    return {showToast};
};

export const formatSuccessMessage = (res) => res?.data?.message ?? "";

export const formatErrorMessage = (detail, label = "item") => {
    if (!detail) return `Could not save ${label}.`;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
        return detail
            .map((item) => {
                if (typeof item === "string") return item;
                if (item?.msg) return item.msg;
                return "Invalid input.";
            })
            .join(" ");
    }
    return `Could not save ${label}.`;
};

export const getTotalPages = (total, pageSize) =>
    Math.max(1, Math.ceil(total / pageSize));

export const updatePagination = (container, page, total, pageSize) => {
    const totalPages = getTotalPages(total, pageSize);
    const safePage = Math.min(Math.max(page, 1), totalPages);
    container.querySelector("[data-action=prev]").disabled = safePage <= 1;
    container.querySelector("[data-action=next]").disabled =
        safePage >= totalPages;
    container.querySelector(".page-indicator").textContent =
        `Page ${safePage} of ${totalPages} (${total} items)`;
};
