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
      container.appendChild(renderSampleRow(itemId, sample));
    }
  }

  function renderSampleRow(itemId, sample) {
    const row = document.createElement("div");
    row.className = "sample-item";

    const photo = document.createElement("div");
    photo.className = "sample-photo";

    const img = document.createElement("img");
    img.src = `/items/edit/${itemId}/samples/${sample.id}/image`;

    const box = document.createElement("div");
    box.className = "sample-bbox";
    img.addEventListener("load", () => drawBox(box, sample.bbox, img.naturalWidth, img.naturalHeight));

    photo.appendChild(img);
    photo.appendChild(box);

    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "btn btn-secondary";
    editBtn.textContent = "修改";

    const cancelBtn = document.createElement("button");
    cancelBtn.type = "button";
    cancelBtn.className = "btn btn-secondary";
    cancelBtn.textContent = "取消";
    cancelBtn.hidden = true;

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "btn btn-secondary";
    deleteBtn.textContent = "刪除";
    deleteBtn.addEventListener("click", () => deleteSample(itemId, sample.id));

    let points = [];
    let previewBox = null;

    function exitEditMode() {
      photo.classList.remove("sample-photo--editing");
      photo.removeEventListener("click", handlePhotoClick);
      points = [];
      if (previewBox) {
        previewBox.remove();
        previewBox = null;
      }
      editBtn.textContent = "修改";
      cancelBtn.hidden = true;
      deleteBtn.hidden = false;
    }

    function handlePhotoClick(event) {
      const rect = img.getBoundingClientRect();
      const scaleX = img.naturalWidth / rect.width;
      const scaleY = img.naturalHeight / rect.height;
      points.push([(event.clientX - rect.left) * scaleX, (event.clientY - rect.top) * scaleY]);

      if (points.length === 1) {
        previewBox = document.createElement("div");
        previewBox.className = "sample-bbox sample-bbox--preview";
        photo.appendChild(previewBox);
        return;
      }

      const [[px1, py1], [px2, py2]] = points;
      const bbox = [Math.min(px1, px2), Math.min(py1, py2), Math.max(px1, px2), Math.max(py1, py2)];
      drawBox(previewBox, bbox, img.naturalWidth, img.naturalHeight);
      previewBox.dataset.bbox = JSON.stringify(bbox);
      points = [];
    }

    editBtn.addEventListener("click", () => {
      if (editBtn.textContent === "修改") {
        photo.classList.add("sample-photo--editing");
        photo.addEventListener("click", handlePhotoClick);
        editBtn.textContent = "確認";
        cancelBtn.hidden = false;
        deleteBtn.hidden = true;
        return;
      }

      if (!previewBox || !previewBox.dataset.bbox) {
        alert("請先在圖片上點兩個點選取範圍");
        return;
      }
      confirmEdit(itemId, sample.id, JSON.parse(previewBox.dataset.bbox));
    });

    cancelBtn.addEventListener("click", exitEditMode);

    row.appendChild(photo);
    row.appendChild(editBtn);
    row.appendChild(cancelBtn);
    row.appendChild(deleteBtn);
    return row;
  }

  function drawBox(box, bbox, naturalWidth, naturalHeight) {
    const [x1, y1, x2, y2] = bbox;
    box.style.left = `${(x1 / naturalWidth) * 100}%`;
    box.style.top = `${(y1 / naturalHeight) * 100}%`;
    box.style.width = `${((x2 - x1) / naturalWidth) * 100}%`;
    box.style.height = `${((y2 - y1) / naturalHeight) * 100}%`;
  }

  async function confirmEdit(itemId, sampleId, bbox) {
    const resp = await fetch(`/items/edit/${itemId}/samples/${sampleId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bbox }),
    });

    if (!resp.ok) {
      const data = await resp.json();
      alert(`修改樣本失敗: ${data.message || resp.status}`);
      return;
    }

    loadSamples();
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
