const API_BASE = "https://booktalk-functions.azurewebsites.net/api";

const form = document.getElementById("feedback-form");
const titleInput = document.getElementById("title");
const authorInput = document.getElementById("author");
const feedbackInput = document.getElementById("feedback");
const feedbackList = document.getElementById("feedback-list");

let feedbackData = [];
let editMode = false;
let editId = null;

async function loadFeedback() {
  try {
    const res = await fetch(`${API_BASE}/getentries`);
    if (!res.ok) throw new Error("Failed to fetch entries");
    feedbackData = await res.json();
    renderFeedback();
  } catch (err) {
    feedbackList.innerHTML = "<p style='color:red;'>Could not load feedback. Please try again later.</p>";
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const title = titleInput.value.trim();
  const author = authorInput.value.trim();
  const feedback = feedbackInput.value.trim();

  if (!title || !author || !feedback) return;

  try {
    if (editMode) {
      await fetch(`${API_BASE}/updateentry`, {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({rowKey: editId, title, author, feedback}),
      });
      editMode = false;
      editId = null;
    } else {
      await fetch(`${API_BASE}/addentry`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({title, author, feedback}),
      });
    }

    form.reset();
    currentPage = 1;
    try {
      await loadFeedback();
    } catch (err) {
      alert("Something went wrong while refreshing the list.");
    }
  } catch (err) {
    alert("Failed to save entry.");
  }
});

let currentPage = 1;
const entriesPerPage = 5;

function renderFeedback() {
  feedbackList.innerHTML = "";

  if (feedbackData.length === 0) {
    feedbackList.innerHTML = "<p>No feedback yet. Be the first!</p>";
    return;
  }

  const start = (currentPage - 1) * entriesPerPage;
  const end = start + entriesPerPage;
  const pageEntries = feedbackData.slice(start, end);

  pageEntries.forEach((entry) => {
    const div = document.createElement("div");
    div.className = "entry";

    div.innerHTML = `
      <div class="entry-header">
        <div class="entry-title-author">
          <strong>${entry.title}</strong> by ${entry.author}
        </div>
        <div class="entry-timestamp">
          <small>
            ${entry.updatedAt ? `Updated: ${new Date(entry.updatedAt).toLocaleString()}` : `Created: ${new Date(entry.createdAt).toLocaleString()}`}
          </small>
        </div>
      </div>
      <p class="entry-text">${entry.feedback}</p>
      <div class="entry-actions">
        <button class="edit-btn" data-id="${entry.rowKey}">✏️ Edit</button>
        <button class="delete-btn" data-id="${entry.rowKey}">🗑️ Delete</button>
      </div>
    `;

    feedbackList.appendChild(div);
  });

  const totalPages = Math.ceil(feedbackData.length / entriesPerPage);
  if (totalPages > 1) {
    const pagination = document.createElement("div");
    pagination.className = "pagination";

    for (let i = 1; i <= totalPages; i++) {
      const btn = document.createElement("button");
      btn.textContent = i;
      btn.disabled = i === currentPage;
      btn.addEventListener("click", () => {
        currentPage = i;
        renderFeedback();
      });
      pagination.appendChild(btn);
    }

    feedbackList.appendChild(pagination);
  }

  document.querySelectorAll(".edit-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const id = e.target.dataset.id;
      const entry = feedbackData.find((item) => item.rowKey === id);
      titleInput.value = entry.title;
      authorInput.value = entry.author;
      feedbackInput.value = entry.feedback;
      editMode = true;
      editId = id;
      window.scrollTo({top: 0, behavior: "smooth"});
    });
  });

  document.querySelectorAll(".delete-btn").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const id = e.target.dataset.id;
      if (!confirm("Delete this feedback?")) return;
      try {
        await fetch(`${API_BASE}/deleteentry?rowKey=${id}`, {method: "DELETE"});
        currentPage = 1;
        await loadFeedback();
      } catch (err) {
        alert("Failed to delete entry.");
      }
    });
  });
}

loadFeedback();