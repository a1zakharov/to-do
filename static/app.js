document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#task-form");
  const titleInput = document.querySelector("#task-title");
  const taskList = document.querySelector("#task-list");
  const emptyMessage = document.querySelector("#empty-message");
  const errorMessage = document.querySelector("#error-message");
  const filterButtons = document.querySelectorAll("[data-filter]");

  let tasks = [];
  let currentFilter = "all";

  function showError(message) {
    errorMessage.textContent = message;
    errorMessage.hidden = !message;
  }

  async function api(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: options.body ? { "Content-Type": "application/json" } : {},
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || "Не удалось выполнить запрос");
    }

    return response.status === 204 ? null : response.json();
  }

  function visibleTasks() {
    if (currentFilter === "active") return tasks.filter((task) => !task.completed);
    if (currentFilter === "completed") return tasks.filter((task) => task.completed);
    return tasks;
  }

  function render() {
    taskList.replaceChildren();
    const filteredTasks = visibleTasks();
    emptyMessage.hidden = filteredTasks.length > 0;
    emptyMessage.textContent = tasks.length === 0 ? "Задач пока нет" : "Нет задач в этом разделе";

    for (const task of filteredTasks) {
      const item = document.createElement("li");
      item.className = `task-item${task.completed ? " completed" : ""}`;

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = task.completed;
      checkbox.setAttribute("aria-label", `Изменить статус: ${task.title}`);
      checkbox.addEventListener("change", () => toggleTask(task));

      const title = document.createElement("span");
      title.className = "task-title";
      title.textContent = task.title;

      const actions = document.createElement("div");
      actions.className = "task-actions";

      const editButton = document.createElement("button");
      editButton.type = "button";
      editButton.textContent = "Изменить";
      editButton.addEventListener("click", () => editTask(task));

      const deleteButton = document.createElement("button");
      deleteButton.type = "button";
      deleteButton.className = "delete-button";
      deleteButton.textContent = "Удалить";
      deleteButton.addEventListener("click", () => deleteTask(task));

      actions.append(editButton, deleteButton);
      item.append(checkbox, title, actions);
      taskList.append(item);
    }
  }

  async function loadTasks() {
    try {
      tasks = await api("/api/tasks");
      showError("");
      render();
    } catch (error) {
      showError(error.message);
    }
  }

  async function toggleTask(task) {
    try {
      const updated = await api(`/api/tasks/${task.id}`, {
        method: "PUT",
        body: JSON.stringify({ completed: !task.completed }),
      });
      tasks = tasks.map((item) => item.id === updated.id ? updated : item);
      showError("");
      render();
    } catch (error) {
      showError(error.message);
      render();
    }
  }

  async function editTask(task) {
    const newTitle = window.prompt("Измените текст задачи", task.title);
    if (newTitle === null) return;
    if (!newTitle.trim()) {
      showError("Текст задачи не может быть пустым");
      return;
    }

    try {
      const updated = await api(`/api/tasks/${task.id}`, {
        method: "PUT",
        body: JSON.stringify({ title: newTitle }),
      });
      tasks = tasks.map((item) => item.id === updated.id ? updated : item);
      showError("");
      render();
    } catch (error) {
      showError(error.message);
    }
  }

  async function deleteTask(task) {
    if (!window.confirm(`Удалить задачу «${task.title}»?`)) return;

    try {
      await api(`/api/tasks/${task.id}`, { method: "DELETE" });
      tasks = tasks.filter((item) => item.id !== task.id);
      showError("");
      render();
    } catch (error) {
      showError(error.message);
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const title = titleInput.value.trim();
    if (!title) {
      showError("Введите текст задачи");
      return;
    }

    try {
      const task = await api("/api/tasks", {
        method: "POST",
        body: JSON.stringify({ title }),
      });
      tasks.unshift(task);
      titleInput.value = "";
      showError("");
      render();
      titleInput.focus();
    } catch (error) {
      showError(error.message);
    }
  });

  filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
      currentFilter = button.dataset.filter;
      filterButtons.forEach((item) => item.classList.toggle("active", item === button));
      render();
    });
  });

  loadTasks();
});
