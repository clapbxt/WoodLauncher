const form = document.querySelector("#publish-form");
const statusLine = document.querySelector("#publish-status");
const submitButton = document.querySelector("#publish-submit");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusLine.textContent = "";
  statusLine.className = "form-status";
  const data = new FormData(form);
  const token = String(data.get("admin_token") || "").trim();
  const file = data.get("lua_file");

  if (!token) {
    statusLine.textContent = "Paste the MOD_ADMIN_TOKEN value configured in your Netlify site.";
    statusLine.classList.add("error");
    return;
  }
  if (!(file instanceof File) || !file.name.toLowerCase().endsWith(".lua")) {
    statusLine.textContent = "Choose a .lua file.";
    statusLine.classList.add("error");
    return;
  }
  if (file.size === 0 || file.size > 1024 * 1024) {
    statusLine.textContent = "The Lua file must be between 1 byte and 1 MiB.";
    statusLine.classList.add("error");
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = "Publishing...";
  try {
    const response = await fetch("/api/mods", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        id: data.get("id"),
        name: data.get("name"),
        author: data.get("author"),
        version: data.get("version"),
        summary: data.get("summary"),
        description: data.get("description"),
        game_version: data.get("game_version"),
        tags: String(data.get("tags")).split(",").map((tag) => tag.trim()).filter(Boolean),
        changelog: data.get("changelog") || "",
        code: await file.text(),
      }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(result.error || `Publish failed with HTTP ${response.status}.`);
    }
    statusLine.textContent = `${result.mod.name} ${result.mod.version} is now published in the official collection.`;
    statusLine.classList.add("success");
    form.reset();
  } catch (error) {
    statusLine.textContent = error instanceof Error ? error.message : "Publishing failed.";
    statusLine.classList.add("error");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Publish mod";
  }
});
