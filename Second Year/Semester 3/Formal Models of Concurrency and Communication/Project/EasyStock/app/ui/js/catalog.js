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

const booksBody = document.getElementById("books-body");
const genresBody = document.getElementById("genres-body");
const authorsBody = document.getElementById("authors-body");

const booksGenreFilter = document.getElementById("books-genre-filter");
const authorSelect = document.getElementById("author-select");
const genreSelect = document.getElementById("genre-select");

const booksPagination = document.getElementById("books-pagination");
const genresPagination = document.getElementById("genres-pagination");
const authorsPagination = document.getElementById("authors-pagination");

const PAGE_SIZE = 5;
let bookPage = 1;
let genrePage = 1;
let authorPage = 1;

const authorsById = new Map();
const genresById = new Map();
const authorBookCounts = new Map();
const genreBookCounts = new Map();
const booksWithActiveLoans = new Set();

const formatCatalogError = (detail, label = "book") =>
    formatErrorMessage(detail, label);

const renderBooks = (books) => {
    booksBody.innerHTML = "";

    if (!books.length) {
        booksBody.innerHTML = `<tr><td colspan="5">No books found.</td></tr>`;
        return;
    }

    books.forEach((b) => {
        const hasLoans = booksWithActiveLoans.has(b.id);
        booksBody.insertAdjacentHTML(
            "beforeend",
            `
      <tr>
        <td>${b.isbn}</td>
        <td>${b.title}</td>
        <td>${b.author}</td>
        <td>${b.genre}</td>
        <td>
          <button data-action="edit-book" data-id="${b.id}">Edit</button>
          <button
            data-action="delete-book"
            data-id="${b.id}"
            ${hasLoans ? "disabled title='Book has active loans'" : ""}
          >
            Delete
            </button>
        </td>
      </tr>
      `
        );
    });
};

const renderGenres = (genres) => {
    genresBody.innerHTML = "";

    if (!genres.length) {
        genresBody.innerHTML = `<tr><td colspan="4">No genres found.</td></tr>`;
        return;
    }

    genres.forEach((g) => {
        const bookCount = genreBookCounts.get(g.name) ?? 0;
        const hasBooks = bookCount > 0;

        genresBody.insertAdjacentHTML(
            "beforeend",
            `
      <tr>
        <td>${g.id}</td>
        <td>${g.name}</td>
        <td>${bookCount}</td>
        <td>
          <button data-action="edit-genre" data-id="${g.id}">Edit</button>
          <button
            data-action="delete-genre"
            data-id="${g.id}"
            ${hasBooks ? "disabled title='Genre has books'" : ""}
          >
            Delete
          </button>
        </td>
      </tr>
      `
        );
    });
};

const renderAuthors = (authors) => {
    authorsBody.innerHTML = "";

    if (!authors.length) {
        authorsBody.innerHTML = `<tr><td colspan="4">No authors found.</td></tr>`;
        return;
    }

    authors.forEach((a) => {
        const hasBooks = (authorBookCounts.get(a.id) ?? 0) > 0;

        authorsBody.insertAdjacentHTML(
            "beforeend",
            `
            <tr>
                <td>${a.id}</td>
                <td>${a.name}</td>
                <td>${a.birth_year ?? ""}</td>
                <td>
                    <button data-action="edit-author" data-id="${a.id}">Edit</button>
                    <button
                        data-action="delete-author"
                        data-id="${a.id}"
                        ${hasBooks ? "disabled title='Author has books'" : ""}
                    >
                        Delete
                    </button>
                </td>
            </tr>
            `
        );
    });
};

const loadAuthorOptions = async () => {
    const res = await api("/authors?limit=1000&page=1");
    if (!res.ok) return;

    authorsById.clear();
    authorSelect.innerHTML = `<option value="">Select author</option>`;

    res.data.forEach((a) => {
        authorsById.set(a.id, a);
        authorSelect.insertAdjacentHTML(
            "beforeend",
            `<option value="${a.id}">${a.name}</option>`
        );
    });

    authorSelect.value = "";
};

const loadGenreOptions = async () => {
    const res = await api("/genres?limit=1000&page=1");
    if (!res.ok) return;

    genreSelect.innerHTML = `<option value="">Select genre</option>`;
    if (booksGenreFilter) {
        const currentFilter = booksGenreFilter.value;
        booksGenreFilter.innerHTML = `<option value="">All genres</option>`;
        res.data.forEach((g) => {
            booksGenreFilter.insertAdjacentHTML(
                "beforeend",
                `<option value="${g.name}">${g.name}</option>`
            );
        });
        booksGenreFilter.value = currentFilter;
        if (booksGenreFilter.value !== currentFilter) {
            booksGenreFilter.value = "";
        }
    }

    res.data.forEach((g) => {
        genreSelect.insertAdjacentHTML(
            "beforeend",
            `<option value="${g.id}">${g.name}</option>`
        );
    });

    genreSelect.value = "";
};

const loadGenreBookCounts = async () => {
    const res = await api("/books?limit=1000&page=1");
    if (!res.ok) return;

    genreBookCounts.clear();
    res.data.forEach((b) => {
        if (!b.genre) return;
        genreBookCounts.set(b.genre, (genreBookCounts.get(b.genre) ?? 0) + 1);
    });
};

const loadAuthorBookCounts = async () => {
    const res = await api("/books?limit=1000&page=1");
    if (!res.ok) return;

    authorBookCounts.clear();
    res.data.forEach((b) => {
        if (!b.author_id) return;

        authorBookCounts.set(
            b.author_id,
            (authorBookCounts.get(b.author_id) ?? 0) + 1
        );
    });
};

const loadBooksWithActiveLoans = async () => {
    const res = await api("/loans/active?limit=1000&page=1");
    if (!res.ok) return;

    booksWithActiveLoans.clear();
    res.data.forEach((loan) => {
        booksWithActiveLoans.add(loan.book_id);
    });
};

const loadBooksPage = async () => {
    await loadBooksWithActiveLoans();
    const genreQuery = booksGenreFilter?.value
        ? `&genre=${encodeURIComponent(booksGenreFilter.value)}`
        : "";
    const res = await api(
        `/books?limit=${PAGE_SIZE}&page=${bookPage}${genreQuery}`
    );
    if (!res.ok) return res;

    const total = res.total ?? 0;
    const totalPages = getTotalPages(total, PAGE_SIZE);
    if (bookPage > totalPages) {
        bookPage = totalPages;
        return loadBooksPage();
    }

    renderBooks(res.data);
    updatePagination(booksPagination, bookPage, total, PAGE_SIZE);
    return res;
};

const loadGenresPage = async () => {
    await loadGenreBookCounts();
    const res = await api(`/genres?limit=${PAGE_SIZE}&page=${genrePage}`);
    if (!res.ok) return res;

    const total = res.total ?? 0;
    const totalPages = getTotalPages(total, PAGE_SIZE);
    if (genrePage > totalPages) {
        genrePage = totalPages;
        return loadGenresPage();
    }

    genresById.clear();
    res.data.forEach((g) => genresById.set(g.id, g));
    renderGenres(res.data);
    updatePagination(genresPagination, genrePage, total, PAGE_SIZE);
    return res;
};

const loadAuthorsPage = async () => {
    await loadAuthorBookCounts();
    const res = await api(`/authors?limit=${PAGE_SIZE}&page=${authorPage}`);
    if (!res.ok) return res;

    const total = res.total ?? 0;
    const totalPages = getTotalPages(total, PAGE_SIZE);
    if (authorPage > totalPages) {
        authorPage = totalPages;
        return loadAuthorsPage();
    }

    renderAuthors(res.data);
    updatePagination(authorsPagination, authorPage, total, PAGE_SIZE);
    return res;
};

const reloadBooks = async () => {
    await loadBooksPage();
};

const reloadGenres = async () => {
    await loadGenreOptions();
    await loadGenresPage();
};

const reloadAuthors = async () => {
    await loadAuthorOptions();
    await loadAuthorsPage();
};

const resetForm = (id) => {
    const form = document.getElementById(id);
    if (!form) return;
    form.reset();
    const idField = form.querySelector("input[name=id]");
    if (idField) idField.value = "";
    if (id === "book-form" && authorSelect?.options.length) {
        authorSelect.selectedIndex = 0;
        genreSelect.selectedIndex = 0;
    }
};

const fillBookForm = (b) => {
    const f = document.getElementById("book-form");
    f.id.value = b.id;
    f.title.value = b.title;
    f.isbn.value = b.isbn;
    if (b.genre_id) {
        genreSelect.value = b.genre_id;
    } else {
        const genre = [...genresById.values()].find((g) => g.name === b.genre);
        genreSelect.value = genre?.id ?? "";
    }
    if (b.author_id) {
        authorSelect.value = b.author_id;
        return;
    }
    const author = [...authorsById.values()].find((a) => a.name === b.author);
    authorSelect.value = author?.id ?? "";
};

const fillGenreForm = (g) => {
    const f = document.getElementById("genre-form");
    f.id.value = g.id;
    f.name.value = g.name;
};

const fillAuthorForm = (a) => {
    const f = document.getElementById("author-form");
    f.id.value = a.id;
    f.name.value = a.name;
    f.birth_year.value = a.birth_year ?? "";
};

const saveBook = async (e) => {
    e.preventDefault();
    const f = e.target;

    const payload = {
        title: f.title.value.trim(),
        isbn: f.isbn.value.trim(),
        genre_id: Number(genreSelect.value),
        author_id: Number(authorSelect.value),
    };

    const id = f.id.value;
    const res = await api(id ? `/books/${id}` : "/books", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(payload),
    });

    if (res.ok) {
        resetForm("book-form");
        const message = formatSuccessMessage(res);
        showToast(message, false);
        await reloadBooks();
        await reloadGenres();
        await reloadAuthors();
    } else {
        const message = formatCatalogError(res.data?.detail);
        showToast(message, true);
    }
};

const saveGenre = async (e) => {
    e.preventDefault();
    const f = e.target;

    const payload = {
        name: f.name.value.trim(),
    };

    const id = f.id.value;
    const res = await api(id ? `/genres/${id}` : "/genres", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(payload),
    });

    if (res.ok) {
        resetForm("genre-form");
        const message = formatSuccessMessage(res);
        showToast(message, false);
        await reloadGenres();
        await reloadBooks();
    } else {
        const message = formatCatalogError(res.data?.detail, "genre");
        showToast(message, true);
    }
};

const saveAuthor = async (e) => {
    e.preventDefault();
    const f = e.target;

    const payload = {
        name: f.name.value.trim(),
        birth_year: f.birth_year.value ? Number(f.birth_year.value) : null,
    };

    const id = f.id.value;
    const res = await api(id ? `/authors/${id}` : "/authors", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(payload),
    });

    if (res.ok) {
        resetForm("author-form");
        const message = formatSuccessMessage(res);
        showToast(message, false);
        await reloadAuthors();
        await reloadBooks();
    } else {
        const message = formatCatalogError(res.data?.detail, "author");
        showToast(message, true);
    }
};

booksBody.addEventListener("click", async (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;

    const id = btn.dataset.id;

    if (btn.dataset.action === "edit-book") {
        const res = await api(`/books/${id}`);
        if (res.ok) fillBookForm(res.data);
    }

    if (btn.dataset.action === "delete-book") {
        if (!window.confirm("Delete this book?")) return;
        const res = await api(`/books/${id}`, {method: "DELETE"});
        if (res.ok) {
            resetForm("book-form");
            const message = formatSuccessMessage(res);
            showToast(message, false);
            await reloadGenres();
            await reloadBooks();
            await reloadAuthors();
        } else {
            const message = formatCatalogError(res.data?.detail);
            showToast(message, true);
        }

    }
});

genresBody.addEventListener("click", async (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;

    const id = Number(btn.dataset.id);

    if (btn.dataset.action === "edit-genre") {
        const genre = genresById.get(id);
        if (genre) fillGenreForm(genre);
    }

    if (btn.dataset.action === "delete-genre") {
        if (!window.confirm("Delete this genre?")) return;
        const res = await api(`/genres/${id}`, {method: "DELETE"});
        if (res.ok) {
            resetForm("genre-form");
            const message = formatSuccessMessage(res);
            showToast(message, false);
            await reloadGenres();
            await reloadBooks();
        } else {
            const message = formatCatalogError(res.data?.detail, "genre");
            showToast(message, true);
        }
    }
});

authorsBody.addEventListener("click", async (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;

    const id = Number(btn.dataset.id);

    if (btn.dataset.action === "edit-author") {
        fillAuthorForm(authorsById.get(id));
    }

    if (btn.dataset.action === "delete-author") {
        if (!window.confirm("Delete this author?")) return;
        const res = await api(`/authors/${id}`, {method: "DELETE"});
        if (res.ok) {
            resetForm("author-form");
            const message = formatSuccessMessage(res);
            showToast(message, false);
            await reloadAuthors();
            await reloadBooks();
        } else {
            const message = formatCatalogError(res.data?.detail, "author");
            showToast(message, true);
        }
    }
});

booksPagination.addEventListener("click", async (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;

    if (btn.dataset.action === "prev" && bookPage > 1) bookPage--;
    if (btn.dataset.action === "next") bookPage++;

    await loadBooksPage();
});

if (booksGenreFilter) {
    booksGenreFilter.addEventListener("change", async () => {
        bookPage = 1;
        await loadBooksPage();
    });
}

genresPagination.addEventListener("click", async (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;

    if (btn.dataset.action === "prev" && genrePage > 1) genrePage--;
    if (btn.dataset.action === "next") genrePage++;

    await loadGenresPage();
});

authorsPagination.addEventListener("click", async (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;

    if (btn.dataset.action === "prev" && authorPage > 1) authorPage--;
    if (btn.dataset.action === "next") authorPage++;

    await loadAuthorsPage();
});

document.getElementById("book-form").addEventListener("submit", saveBook);
document.getElementById("genre-form").addEventListener("submit", saveGenre);
document.getElementById("author-form").addEventListener("submit", saveAuthor);
document.getElementById("reset-book").addEventListener("click", () => {
    resetForm("book-form");
    showToast("", false);
});
document.getElementById("reset-genre").addEventListener("click", () => {
    resetForm("genre-form");
    showToast("", false);
});
document.getElementById("reset-author").addEventListener("click", () => {
    resetForm("author-form");
    showToast("", false);
});

(async () => {
    await loadAuthorOptions();
    await loadGenreOptions();
    await loadGenresPage();
    await loadAuthorsPage();
    await loadBooksPage();
})();
