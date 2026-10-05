(function () {
  const saveBtn = document.getElementById("save-btn");
  const minStockInput = document.getElementById("min_stock");

  saveBtn.addEventListener("click", async () => {
    const itemId = saveBtn.dataset.itemId;

    const resp = await fetch(`/items/edit/${itemId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ min_stock: Number(minStockInput.value) }),
    });

    if (!resp.ok) {
      const data = await resp.json();
      alert(`儲存失敗: ${data.message || resp.status}`);
      return;
    }

    alert("已儲存");
  });

  async function loadSamples() {
    const container = document.getElementById("samples");
    const itemId = container.dataset.itemId;

    const resp = await fetch(`/items/edit/${itemId}/samples`);
    const samples = await resp.json();

    container.innerHTML = "";
    for (const sample of samples) {
      const row = document.createElement("div");
      row.className = "sample-item";

      const photo = document.createElement("div");
      photo.className = "sample-photo";

      const img = document.createElement("img");
      img.src = `/items/edit/${itemId}/samples/${sample.id}/image`;

      const box = document.createElement("div");
      box.className = "sample-bbox";
      img.addEventListener("load", () => {
        const [x1, y1, x2, y2] = sample.bbox;
        const w = img.naturalWidth;
        const h = img.naturalHeight;
        box.style.left = `${(x1 / w) * 100}%`;
        box.style.top = `${(y1 / h) * 100}%`;
        box.style.width = `${((x2 - x1) / w) * 100}%`;
        box.style.height = `${((y2 - y1) / h) * 100}%`;
      });

      photo.appendChild(img);
      photo.appendChild(box);

      const deleteBtn = document.createElement("button");
      deleteBtn.type = "button";
      deleteBtn.className = "btn btn-secondary";
      deleteBtn.textContent = "刪除";
      deleteBtn.addEventListener("click", () => deleteSample(itemId, sample.id));

      row.appendChild(photo);
      row.appendChild(deleteBtn);
      container.appendChild(row);
    }
  }

  async function deleteSample(itemId, sampleId) {
    const resp = await fetch(`/items/edit/${itemId}/samples/${sampleId}`, {
      method: "DELETE",
    });

    if (!resp.ok) {
      const data = await resp.json();
      alert(`刪除樣本失敗: ${data.message || resp.status}`);
      return;
    }

    loadSamples();
  }

  loadSamples();

  const addSampleBtn = document.getElementById("add-sample-btn");
  const sampleCameraInput = document.getElementById("sample-camera-input");

  addSampleBtn.addEventListener("click", () => sampleCameraInput.click());

  sampleCameraInput.addEventListener("change", async () => {
    const file = sampleCameraInput.files[0];
    if (!file) return;

    const itemId = document.getElementById("samples").dataset.itemId;

    const formData = new FormData();
    formData.append("image", file);

    const resp = await fetch(`/items/edit/${itemId}/samples`, {
      method: "POST",
      body: formData,
    });

    if (!resp.ok) {
      const data = await resp.json();
      alert(`新增樣本失敗: ${data.message || resp.status}`);
      return;
    }

    location.reload();
  });
})();
