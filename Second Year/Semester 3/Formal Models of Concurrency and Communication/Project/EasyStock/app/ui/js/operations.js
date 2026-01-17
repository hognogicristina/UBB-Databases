import {
    api,
    createToast,
    formatSuccessMessage,
    formatErrorMessage,
    getTotalPages,
    updatePagination,
} from "./common.js";

const toast = document.getElementById("toast");
const {showToast} = createToast(toast);

const membersBody = document.getElementById("members-body");
const loansBody = document.getElementById("loans-body");
const historyBody = document.getElementById("history-body");
const overdueBody = document.getElementById("overdue-body");

const borrowBookSelect = document.getElementById("borrow-book");
const borrowGenreSelect = document.getElementById("borrow-genre");
const borrowMemberSelect = document.getElementById("borrow-member");
const historyMemberSelect = document.getElementById("history-member");
const borrowSubmitButton = document.querySelector(
    "#borrow-form button[type=submit]"
);

const membersPagination = document.getElementById("members-pagination");
const loansPagination = document.getElementById("loans-pagination");
const historyPagination = document.getElementById("history-pagination");
const overduePagination = document.getElementById("overdue-pagination");

const PAGE_SIZE = 5;
const HISTORY_PAGE_SIZE = 5;

let memberPage = 1;
let loanPage = 1;
let historyPage = 1;
let overduePage = 1;
let currentHistoryMemberId = null;

let overdueLoansData = [];

const membersById = new Map();
const booksById = new Map();
let allBooks = [];


const formatOperationsError = (detail, label = "member") =>
    formatErrorMessage(detail, label);

const formatTime = (v) => (v ? String(v).replace("T", " ") : "");

const updatePaginationIfEmpty = (container) => {
    updatePagination(container, 1, 0, HISTORY_PAGE_SIZE);
};

const setSelectOptions = (select, items, labelFn, placeholder) => {
    select.innerHTML = `<option value="">${placeholder}</option>`;
    select.disabled = !items.length;

    items.forEach((i) =>
        select.insertAdjacentHTML(
            "beforeend",
            `<option value="${i.id}">${labelFn(i)}</option>`
        )
    );

    select.value = "";
};

const updateBorrowButtonState = () => {
    if (!borrowSubmitButton) return;
    const bookId = Number(borrowBookSelect.value);
    const book = booksById.get(bookId);
    const memberId = Number(borrowMemberSelect.value);
    const isBorrowed = Boolean(book?.is_borrowed);
    const hasSelections = Boolean(bookId && memberId);
    borrowSubmitButton.disabled = !hasSelections || Boolean(book && isBorrowed);
    borrowSubmitButton.title = isBorrowed ? "Book is already borrowed." : "";
};


const resetForm = (id) => {
    const form = document.getElementById(id);
    if (!form) return;
    form.reset();
    const idField = form.querySelector("input[name=id]");
    if (idField) idField.value = "";
};


const renderMembers = (items) => {
    membersBody.innerHTML = items.length
        ? ""
        : `<tr><td colspan="5">No members found.</td></tr>`;

    items.forEach((m) =>
        membersBody.insertAdjacentHTML(
            "beforeend",
            `
      <tr>
        <td>${m.id}</td>
        <td>${m.name}</td>
        <td>${m.email}</td>
        <td>${m.active_loans}</td>
        <td>
          <button data-action="edit-member" data-id="${m.id}">Edit</button>
          <button data-action="delete-member" data-id="${m.id}"
            ${m.active_loans > 0 ? "disabled" : ""}>
            Delete
          </button>
        </td>
      </tr>
    `
        )
    );
};

const renderLoans = (items) => {
    loansBody.innerHTML = items.length
        ? ""
        : `<tr><td colspan="5">No active loans.</td></tr>`;

    items.forEach((l) =>
        loansBody.insertAdjacentHTML(
            "beforeend",
            `
      <tr>
        <td>${l.id}</td>
        <td>${l.book_title}</td>
        <td>${l.member_name}</td>
        <td>${formatTime(l.loan_date)}</td>
        <td><button data-action="return" data-loan="${l.id}">Return</button></td>
      </tr>
    `
        )
    );
};

const renderHistory = (items) => {
    historyBody.innerHTML = items.length
        ? ""
        : `<tr><td colspan="4">No history.</td></tr>`;

    items.forEach((r) =>
        historyBody.insertAdjacentHTML(
            "beforeend",
            `
      <tr>
        <td>${r.loan_id}</td>
        <td>${r.book_title}</td>
        <td>${formatTime(r.loan_date)}</td>
        <td>${formatTime(r.return_date)}</td>
      </tr>
    `
        )
    );
};

const renderOverduePage = () => {
    const start = (overduePage - 1) * HISTORY_PAGE_SIZE;
    const slice = overdueLoansData.slice(start, start + HISTORY_PAGE_SIZE);
    overdueBody.innerHTML = slice.length
        ? ""
        : `<tr><td colspan="4">No overdue loans.</td></tr>`;

    slice.forEach((o) =>
        overdueBody.insertAdjacentHTML(
            "beforeend",
            `
      <tr>
        <td>${o.book_title}</td>
        <td>${o.member_name}</td>
        <td>${formatTime(o.loan_date)}</td>
        <td>${o.days_overdue}</td>
      </tr>
    `
        )
    );

    updatePagination(
        overduePagination,
        overduePage,
        overdueLoansData.length,
        HISTORY_PAGE_SIZE
    );
};


const loadBooksOptions = async () => {
    const r = await api("/books?limit=1000&page=1");
    if (!r.ok) return;

    booksById.clear();
    allBooks = r.data ?? [];
    allBooks.forEach((b) => booksById.set(b.id, b));
    setSelectOptions(borrowBookSelect, [], (b) => b.title, "Select book");
    updateBorrowButtonState();
};

const loadMembersOptions = async () => {
    const r = await api("/members?limit=1000&page=1");
    if (!r.ok) return;

    setSelectOptions(borrowMemberSelect, r.data, (m) => m.name, "Select member");
    setSelectOptions(historyMemberSelect, r.data, (m) => m.name, "Select member");
    borrowGenreSelect.disabled = true;
    borrowGenreSelect.value = "";
    refreshBorrowBooks();
    updateBorrowButtonState();
};

const loadGenreOptions = async () => {
    const r = await api("/genres?limit=1000&page=1");
    if (!r.ok) return;

    borrowGenreSelect.innerHTML = `<option value="">Select genre</option>`;
    r.data.forEach((g) => {
        borrowGenreSelect.insertAdjacentHTML(
            "beforeend",
            `<option value="${g.name}">${g.name}</option>`
        );
    });
    borrowGenreSelect.disabled = true;
    updateBorrowButtonState();
};

const refreshBorrowBooks = () => {
    const selectedGenre = borrowGenreSelect.value;
    const filteredBooks = selectedGenre
        ? allBooks.filter(
            (b) =>
                b.genre &&
                b.genre.trim().toLowerCase() === selectedGenre.trim().toLowerCase()
        )
        : [];

    setSelectOptions(
        borrowBookSelect,
        filteredBooks,
        (b) => b.title,
        "Select book"
    );
    borrowBookSelect.disabled = !selectedGenre;
    updateBorrowButtonState();
};

const loadMembersPage = async () => {
    const [members, loans] = await Promise.all([
        api(`/members?limit=${PAGE_SIZE}&page=${memberPage}`),
        api("/reports/members-with-loans"),
    ]);

    if (!members.ok) return members;

    const loanMap = new Map(
        (loans.ok ? loans.data : []).map((m) => [m.member_id, m.active_loans])
    );

    membersById.clear();
    members.data.forEach((m) => {
        m.active_loans = loanMap.get(m.id) ?? 0;
        membersById.set(m.id, m);
    });

    const total = members.total ?? 0;
    const totalPages = getTotalPages(total, PAGE_SIZE);
    if (memberPage > totalPages) {
        memberPage = totalPages;
        return loadMembersPage();
    }

    renderMembers(members.data);
    updatePagination(membersPagination, memberPage, total, PAGE_SIZE);

    return members;
};

const loadLoansPage = async () => {
    const r = await api(`/loans/active?limit=${PAGE_SIZE}&page=${loanPage}`);
    if (!r.ok) return r;

    const total = r.total ?? 0;
    const totalPages = getTotalPages(total, PAGE_SIZE);
    if (loanPage > totalPages) {
        loanPage = totalPages;
        return loadLoansPage();
    }

    renderLoans(r.data);
    updatePagination(loansPagination, loanPage, total, PAGE_SIZE);
    return r;
};

const loadHistoryPage = async () => {
    if (!currentHistoryMemberId) {
        historyBody.innerHTML = `<tr><td colspan="4">Select a member.</td></tr>`;
        historyPage = 1;
        updatePaginationIfEmpty(historyPagination);
        return;
    }

    const r = await api(
        `/members/${currentHistoryMemberId}/history?limit=${HISTORY_PAGE_SIZE}&page=${historyPage}`
    );
    if (!r.ok) return r;

    const total = r.total ?? 0;
    const totalPages = getTotalPages(total, HISTORY_PAGE_SIZE);
    if (historyPage > totalPages) {
        historyPage = totalPages;
        return loadHistoryPage();
    }

    renderHistory(r.data);
    updatePagination(historyPagination, historyPage, total, HISTORY_PAGE_SIZE);
};

const loadOverdueLoans = async () => {
    const r = await api("/reports/overdue-loans");
    if (!r.ok) return;

    overdueLoansData = r.data;
    overduePage = 1;
    renderOverduePage();
};

const reloadMembers = async () => {
    await loadMembersPage();
};

const reloadLoans = async () => {
    await loadLoansPage();
    await loadOverdueLoans();
    await loadBooksOptions();
    refreshBorrowBooks();
    await loadHistoryPage();
};


const saveMember = async (e) => {
    e.preventDefault();
    const f = e.target;

    const payload = {name: f.name.value.trim(), email: f.email.value.trim()};
    const id = f.id.value;

    const r = await api(id ? `/members/${id}` : "/members", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(payload),
    });

    if (r.ok) {
        resetForm("member-form");
        const message = formatSuccessMessage(r);
        showToast(message, false);
        await loadMembersOptions();
        await reloadMembers();
    } else {
        const message = formatOperationsError(r.data?.detail, "member");
        showToast(message, true);
    }
};

const borrowBook = async (e) => {
    e.preventDefault();
    const f = e.target;

    const bookId = Number(f.book_id.value);
    const memberId = Number(f.member_id.value);
    const book = booksById.get(bookId);
    if (!book || !memberId) {
        showToast("Please select a member, genre, and book.", true);
        return;
    }

    const r = await api("/loans/borrow", {
        method: "POST",
        body: JSON.stringify({book_id: book.id, member_id: memberId}),
    });

    if (r.ok) {
        const message = formatSuccessMessage(r);
        showToast(message, false);
        await reloadLoans();
        await loadMembersOptions();
        await reloadMembers();
        await reloadBooks();
    } else {
        const message = formatOperationsError(r.data?.detail, "borrow");
        showToast(message, true);
    }
};

const returnBook = async (id) => {
    if (!window.confirm("Return this book?")) return;
    const r = await api(`/loans/${id}/return`, {method: "POST"});
    if (r.ok) {
        const message = formatSuccessMessage(r);
        showToast(message, false);
        await reloadLoans();
        await reloadMembers();
        await reloadBooks();
    } else {
        const message = formatOperationsError(r.data?.detail, "return");
        showToast(message, true);
    }
};


membersBody.addEventListener("click", async (e) => {
    const b = e.target.closest("button");
    if (!b) return;

    const id = Number(b.dataset.id);

    if (b.dataset.action === "edit-member") {
        const m = membersById.get(id);
        const f = document.getElementById("member-form");
        f.id.value = m.id;
        f.name.value = m.name;
        f.email.value = m.email;
    }

    if (b.dataset.action === "delete-member") {
        if (!window.confirm("Delete this member?")) return;
        const r = await api(`/members/${id}`, {method: "DELETE"});
        if (r.ok) {
            resetForm("member-form");
            const message = formatSuccessMessage(r);
            showToast(message, false);
            await reloadMembers();
            await loadMembersOptions();
        } else {
            const message = formatOperationsError(r.data?.detail, "member");
            showToast(message, true);
        }
    }
});

loansBody.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-action=return]");
    if (b) returnBook(Number(b.dataset.loan));
});

historyPagination.addEventListener("click", async (e) => {
    const b = e.target.closest("button");
    if (!b) return;

    if (b.dataset.action === "prev" && historyPage > 1) historyPage--;
    if (b.dataset.action === "next") historyPage++;

    await loadHistoryPage();
});

overduePagination.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;

    if (b.dataset.action === "prev" && overduePage > 1) overduePage--;
    if (b.dataset.action === "next") overduePage++;

    renderOverduePage();
});

membersPagination.addEventListener("click", async (e) => {
    const b = e.target.closest("button");
    if (!b) return;

    if (b.dataset.action === "prev" && memberPage > 1) memberPage--;
    if (b.dataset.action === "next") memberPage++;

    await loadMembersPage();
});

loansPagination.addEventListener("click", async (e) => {
    const b = e.target.closest("button");
    if (!b) return;

    if (b.dataset.action === "prev" && loanPage > 1) loanPage--;
    if (b.dataset.action === "next") loanPage++;

    await loadLoansPage();
});

document.getElementById("member-form").addEventListener("submit", saveMember);
document.getElementById("reset-member").addEventListener("click", () => {
    resetForm("member-form");
    showToast("", false);
});
document.getElementById("borrow-form").addEventListener("submit", borrowBook);
borrowMemberSelect.addEventListener("change", () => {
    const hasMember = Boolean(borrowMemberSelect.value);
    borrowGenreSelect.disabled = !hasMember;
    borrowGenreSelect.value = "";
    refreshBorrowBooks();
});
borrowGenreSelect.addEventListener("change", refreshBorrowBooks);
borrowBookSelect.addEventListener("change", updateBorrowButtonState);
document.getElementById("history-form").addEventListener("submit", (e) => {
    e.preventDefault();
    currentHistoryMemberId = e.target.member_id.value;
    historyPage = 1;
    loadHistoryPage();
});

(async () => {
    await loadBooksOptions();
    await loadGenreOptions();
    await loadMembersOptions();
    await loadMembersPage();
    await loadLoansPage();
    await loadOverdueLoans();
    await loadHistoryPage();
})();
