(function () {
  const scanBtn = document.getElementById("scan-btn");
  const scanInput = document.getElementById("scan-input");
  const addBtn = document.getElementById("add-btn");
  const canvas = document.getElementById("scan-canvas");
  const ctx = canvas.getContext("2d");
  const listEl = document.getElementById("candidate-list");
  const rejectedSection = document.getElementById("rejected-section");
  const rejectedListEl = document.getElementById("rejected-list");
  const submitBtn = document.getElementById("submit-btn");
  const submitError = document.getElementById("submit-error");
  const recognizeError = document.getElementById("recognize-error");

  const POINT_HIT_RADIUS_RATIO = 40; // 半徑 = canvas.width / 40

  let currentImage = null;
  let candidates = [];
  let addMode = false;
  let catalog = [];

  const catalogPromise = loadCatalog();

  async function loadCatalog() {
    const resp = await fetch("/items", { headers: { Accept: "application/json" } });
    catalog = await resp.json();
  }

  addBtn.addEventListener("click", () => {
    addMode = !addMode;
    addBtn.classList.toggle("btn-primary", addMode);
    addBtn.classList.toggle("btn-secondary", !addMode);
    addBtn.textContent = addMode ? "點擊畫面放置" : "新增物件";
  });

  scanBtn.addEventListener("click", () => scanInput.click());

  scanInput.addEventListener("change", () => {
    const file = scanInput.files[0];
    if (!file) return;

    const img = new Image();
    img.onload = async () => {
      currentImage = img;
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      recognizeError.hidden = true;

      try {
        await catalogPromise;
        candidates = await runRecognize(file);
      } catch (e) {
        recognizeError.textContent = `辨識失敗: ${e.message}`;
        recognizeError.hidden = false;
        return;
      }

      addBtn.hidden = false;
      submitBtn.hidden = false;
      render();
    };
    img.src = URL.createObjectURL(file);
  });

  async function runRecognize(file) {
    const formData = new FormData();
    formData.append("image", file);

    const resp = await fetch("/recognize", { method: "POST", body: formData });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.message || `HTTP ${resp.status}`);

    return data.result.map((r) => ({
      source: "auto_detected",
      predicted_bbox: r.bbox,
      predicted_item_id: r.item_id,
      final_item_id: r.item_id,
      status: "ok",
      selected: false,
      prediction_id: r.prediction_id,
      predicted_instance_id: r.instance_id,
      final_instance_id: r.instance_id,
    }));
  }

  canvas.addEventListener("click", (e) => {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;

    if (addMode) {
      addCandidateAtPoint(x, y);
      addMode = false;
      addBtn.classList.remove("btn-primary");
      addBtn.classList.add("btn-secondary");
      addBtn.textContent = "新增物件";
      return;
    }

    let hitIndex = -1;
    let hitArea = Infinity;
    candidates.forEach((c, index) => {
      if (c.status === "rejected") return;

      if (c.predicted_bbox) {
        const [x1, y1, x2, y2] = c.predicted_bbox;
        if (x >= x1 && x <= x2 && y >= y1 && y <= y2) {
          const area = (x2 - x1) * (y2 - y1);
          if (area < hitArea) {
            hitArea = area;
            hitIndex = index;
          }
        }
      } else if (c.predicted_point) {
        const [px, py] = c.predicted_point;
        const half = canvas.width / POINT_HIT_RADIUS_RATIO;
        if (Math.abs(x - px) <= half && Math.abs(y - py) <= half && 0 < hitArea) {
          hitArea = 0; // 點永遠比任何框小,優先命中
          hitIndex = index;
        }
      }
    });

    if (hitIndex !== -1) selectCandidate(hitIndex);
  });

  function addCandidateAtPoint(x, y) {
    candidates.push({
      source: "manual_add",
      predicted_bbox: null,
      predicted_point: [x, y],
      predicted_item_id: null,
      final_item_id: null,
      status: "ok",
      selected: false,
      prediction_id: null,
      predicted_instance_id: null,
      final_instance_id: null,
    });
    candidates.forEach((c, i) => {
      c.selected = i === candidates.length - 1;
    });
    render();
  }

  function itemName(id) {
    const entry = catalog.find((e) => e.id === id);
    return entry ? entry.name : "未知";
  }

  function selectCandidate(index) {
    candidates.forEach((c, i) => {
      c.selected = i === index;
    });
    render();
  }

  function setFinalItem(index, itemId) {
    const c = candidates[index];
    c.final_item_id = itemId;

    // 換類別時,instance也要跟著換:換回原本模型猜的item就恢復原本猜的instance,
    // 換成別的item就先預設選它底下第一個instance(通常也只有一個),多個的話UI會讓人再調整。
    if (itemId === c.predicted_item_id) {
      c.final_instance_id = c.predicted_instance_id;
    } else {
      const entry = catalog.find((e) => e.id === itemId);
      c.final_instance_id = entry && entry.instances.length > 0 ? entry.instances[0].id : null;
    }
    render();
  }

  function setFinalInstance(index, instanceId) {
    candidates[index].final_instance_id = instanceId;
    render();
  }

  function toggleBboxStatus(index) {
    const c = candidates[index];
    c.status = c.status === "needs_bbox" ? "ok" : "needs_bbox";
    render();
  }

  function rejectCandidate(index) {
    const c = candidates[index];
    // 記住刪除前的選擇,復原時還原用
    c.final_item_id_before_reject = c.final_item_id;
    c.final_instance_id_before_reject = c.final_instance_id;
    c.final_item_id = null;
    c.final_instance_id = null;
    c.status = "rejected";
    c.selected = false;
    render();
  }

  function restoreCandidate(index) {
    const c = candidates[index];
    c.final_item_id = c.final_item_id_before_reject ?? c.predicted_item_id;
    c.final_instance_id = c.final_instance_id_before_reject ?? c.predicted_instance_id;
    c.status = "ok";
    render();
  }

  function render() {
    drawCanvas();
    renderList();
    renderRejectedList();
  }

  function drawCanvas() {
    if (!currentImage) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(currentImage, 0, 0);

    candidates.forEach((c) => {
      if (c.status === "rejected") return;

      const color = c.status === "needs_bbox" ? "#d97706" : "#dc2626";
      ctx.fillStyle = color;
      ctx.strokeStyle = color;
      ctx.font = `${Math.max(16, canvas.width / 40)}px sans-serif`;

      if (c.predicted_bbox) {
        const [x1, y1, x2, y2] = c.predicted_bbox;
        ctx.lineWidth = c.selected ? Math.max(4, canvas.width / 150) : Math.max(2, canvas.width / 300);
        ctx.setLineDash(c.status === "needs_bbox" ? [10, 6] : []);
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
        ctx.setLineDash([]);
        ctx.fillText(itemName(c.final_item_id), x1, y1 > 20 ? y1 - 5 : y1 + 15);
      } else if (c.predicted_point) {
        const [px, py] = c.predicted_point;
        const half = canvas.width / POINT_HIT_RADIUS_RATIO;
        ctx.lineWidth = c.selected ? Math.max(4, canvas.width / 150) : Math.max(2, canvas.width / 300);
        ctx.strokeRect(px - half, py - half, half * 2, half * 2);
        ctx.fillText(itemName(c.final_item_id), px + half + 4, py);
      }
    });
  }

  function renderList() {
    listEl.innerHTML = "";

    candidates.forEach((c, index) => {
      if (c.status === "rejected") return;

      const li = document.createElement("li");
      li.className = "candidate-row" + (c.selected ? " candidate-row--selected" : "");
      li.addEventListener("click", () => selectCandidate(index));

      const select = document.createElement("select");
      if (c.final_item_id === null) {
        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "請選擇類別";
        placeholder.selected = true;
        select.appendChild(placeholder);
      }
      catalog.forEach((entry) => {
        const option = document.createElement("option");
        option.value = entry.id;
        option.textContent = entry.name;
        if (entry.id === c.final_item_id) option.selected = true;
        select.appendChild(option);
      });
      select.addEventListener("click", (e) => e.stopPropagation());
      select.addEventListener("change", () => {
        setFinalItem(index, select.value === "" ? null : Number(select.value));
      });

      li.appendChild(select);

      // 只有選到的item底下instance不只一個時,才需要讓人工選,大多數item只有一個instance,
      // 直接用預設值就好,不用讓使用者多做無意義的選擇。
      const currentEntry = catalog.find((e) => e.id === c.final_item_id);
      if (currentEntry && currentEntry.instances.length > 1) {
        const instanceSelect = document.createElement("select");
        currentEntry.instances.forEach((instance) => {
          const option = document.createElement("option");
          option.value = instance.id;
          option.textContent = instance.name;
          if (instance.id === c.final_instance_id) option.selected = true;
          instanceSelect.appendChild(option);
        });
        instanceSelect.addEventListener("click", (e) => e.stopPropagation());
        instanceSelect.addEventListener("change", () => {
          setFinalInstance(index, Number(instanceSelect.value));
        });
        li.appendChild(instanceSelect);
      }

      // 手動新增的物件沒有 predicted_bbox,「框不準」這個概念對它沒有意義。
      if (c.predicted_bbox) {
        const bboxLabel = document.createElement("label");
        bboxLabel.className = "candidate-row__checkbox";

        const bboxCheckbox = document.createElement("input");
        bboxCheckbox.type = "checkbox";
        bboxCheckbox.checked = c.status === "needs_bbox";
        bboxCheckbox.addEventListener("click", (e) => e.stopPropagation());
        bboxCheckbox.addEventListener("change", () => toggleBboxStatus(index));

        bboxLabel.appendChild(bboxCheckbox);
        bboxLabel.appendChild(document.createTextNode("框不準"));
        li.appendChild(bboxLabel);
      }

      const rejectBtn = document.createElement("button");
      rejectBtn.type = "button";
      rejectBtn.className = "btn btn-secondary btn-small";
      rejectBtn.textContent = "刪除";
      rejectBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        rejectCandidate(index);
      });
      li.appendChild(rejectBtn);

      listEl.appendChild(li);

      if (c.selected) li.scrollIntoView({ block: "nearest" });
    });
  }

  function renderRejectedList() {
    rejectedListEl.innerHTML = "";
    const rejected = candidates
      .map((c, index) => ({ c, index }))
      .filter(({ c }) => c.status === "rejected");

    rejectedSection.hidden = rejected.length === 0;

    rejected.forEach(({ c, index }) => {
      const li = document.createElement("li");
      li.className = "candidate-row";

      const name = document.createElement("span");
      name.textContent = c.source === "manual_add" ? "手動新增的物件" : itemName(c.predicted_item_id);

      const restoreBtn = document.createElement("button");
      restoreBtn.type = "button";
      restoreBtn.className = "btn btn-secondary btn-small";
      restoreBtn.textContent = "復原";
      restoreBtn.addEventListener("click", () => restoreCandidate(index));

      li.appendChild(name);
      li.appendChild(restoreBtn);
      rejectedListEl.appendChild(li);
    });
  }

  function buildSubmissionPayload() {
    const items = candidates
      // 手動新增又被刪除的項目,從沒真的存在過,不送出。
      .filter((c) => !(c.status === "rejected" && c.source === "manual_add"))
      .map((c) => {
        let annotationStatus;
        let finalBbox = null;

        if (c.status === "needs_bbox") {
          annotationStatus = "needs_bbox";
        } else if (c.status === "rejected") {
          annotationStatus = "confirmed"; // 確認為誤判(false positive),final_item_id 為 null
        } else {
          annotationStatus = "confirmed";
          finalBbox = c.predicted_bbox; // 接受目前的框當作最終結果
        }

        return {
          source: c.source,
          predicted_class: c.predicted_item_id === null ? null : itemName(c.predicted_item_id),
          predicted_bbox: c.predicted_bbox,
          final_item_id: c.final_item_id,
          final_bbox: finalBbox,
          annotation_status: annotationStatus,
          prediction_id: c.prediction_id,
          final_instance_id: c.status === "rejected" ? null : c.final_instance_id,
        };
      });

    return { items };
  }

  submitBtn.addEventListener("click", async () => {
    submitError.hidden = true;
    submitBtn.disabled = true;

    try {
      const resp = await fetch("/stock-in", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildSubmissionPayload()),
      });

      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.error || `HTTP ${resp.status}`);
      }

      window.location.href = "/items";
    } catch (e) {
      submitError.textContent = `提交失敗: ${e.message}`;
      submitError.hidden = false;
      submitBtn.disabled = false;
    }
  });
})();
