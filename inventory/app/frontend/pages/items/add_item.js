(function () {
  const photos = [];

  const photoList = document.getElementById("photo-list");
  const addBtn = document.getElementById("add-photo-btn");
  const cameraInput = document.getElementById("camera-input");
  const imagesInput = document.getElementById("images-input");

  addBtn.addEventListener("click", () => cameraInput.click());

  cameraInput.addEventListener("change", () => {
    for (const file of cameraInput.files) {
      photos.push(file);
    }
    cameraInput.value = "";
    render();
  });

  function removePhoto(index) {
    photos.splice(index, 1);
    render();
  }

  // 讓 photos 陣列的內容同步回一個真正的 <input type="file" multiple>,
  // 之後表單提交(htmx)才能正確送出這些檔案。
  function syncInput() {
    const dt = new DataTransfer();
    for (const file of photos) {
      dt.items.add(file);
    }
    imagesInput.files = dt.files;
  }

  function render() {
    photoList.innerHTML = "";
    photos.forEach((file, index) => {
      const url = URL.createObjectURL(file);

      const item = document.createElement("div");
      item.className = "photo-item";

      const img = document.createElement("img");
      img.src = url;
      img.width = 120;

      const meta = document.createElement("div");
      meta.className = "photo-meta";
      meta.textContent = `${file.name} (${file.size} bytes, ${file.type})`;

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "btn btn-secondary btn-small";
      removeBtn.textContent = "移除";
      removeBtn.addEventListener("click", () => removePhoto(index));

      item.appendChild(img);
      item.appendChild(meta);
      item.appendChild(removeBtn);
      photoList.appendChild(item);
    });

    syncInput();
  }
})();
