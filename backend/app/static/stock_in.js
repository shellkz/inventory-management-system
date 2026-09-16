(function () {
  // Stage 1(修改): 純前端,用假資料模擬 /recognize 的結果,還沒有真的打 API。
  const MOCK_CATALOG = [
    { id: 1, name: "電池" },
    { id: 2, name: "螺絲" },
    { id: 3, name: "瓶蓋" },
  ];

  const scanBtn = document.getElementById("scan-btn");
  const scanInput = document.getElementById("scan-input");
  const canvas = document.getElementById("scan-canvas");
  const ctx = canvas.getContext("2d");
  const listEl = document.getElementById("candidate-list");

  let currentImage = null;
  let candidates = [];

  scanBtn.addEventListener("click", () => scanInput.click());

  scanInput.addEventListener("change", () => {
    const file = scanInput.files[0];
    if (!file) return;

    const img = new Image();
    img.onload = () => {
      currentImage = img;
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      candidates = buildMockCandidates(canvas.width, canvas.height);
      render();
    };
    img.src = URL.createObjectURL(file);
  });

  canvas.addEventListener("click", (e) => {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;

    let hitIndex = -1;
    let hitArea = Infinity;
    candidates.forEach((c, index) => {
      const [x1, y1, x2, y2] = c.predicted_bbox;
      if (x >= x1 && x <= x2 && y >= y1 && y <= y2) {
        const area = (x2 - x1) * (y2 - y1);
        if (area < hitArea) {
          hitArea = area;
          hitIndex = index;
        }
      }
    });

    if (hitIndex !== -1) selectCandidate(hitIndex);
  });

  function buildMockCandidates(w, h) {
    return [
      {
        source: "auto_detected",
        predicted_bbox: [w * 0.08, h * 0.1, w * 0.45, h * 0.42],
        predicted_entity_id: 1,
        predicted_entity_name: "電池",
        final_entity_id: 1,
        status: "ok",
        selected: false,
      },
      {
        source: "auto_detected",
        predicted_bbox: [w * 0.52, h * 0.48, w * 0.92, h * 0.82],
        predicted_entity_id: 2,
        predicted_entity_name: "螺絲",
        final_entity_id: 2,
        status: "ok",
        selected: false,
      },
    ];
  }

  function entityName(id) {
    const entry = MOCK_CATALOG.find((e) => e.id === id);
    return entry ? entry.name : "未知";
  }

  function selectCandidate(index) {
    candidates.forEach((c, i) => {
      c.selected = i === index;
    });
    render();
  }

  function setFinalEntity(index, entityId) {
    candidates[index].final_entity_id = entityId;
    render();
  }

  function toggleBboxStatus(index) {
    const c = candidates[index];
    c.status = c.status === "needs_bbox" ? "ok" : "needs_bbox";
    render();
  }

  function render() {
    drawCanvas();
    renderList();
  }

  function drawCanvas() {
    if (!currentImage) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(currentImage, 0, 0);

    candidates.forEach((c) => {
      const [x1, y1, x2, y2] = c.predicted_bbox;
      ctx.lineWidth = c.selected ? Math.max(4, canvas.width / 150) : Math.max(2, canvas.width / 300);
      ctx.strokeStyle = c.status === "needs_bbox" ? "#d97706" : "#dc2626";
      ctx.setLineDash(c.status === "needs_bbox" ? [10, 6] : []);
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
      ctx.setLineDash([]);

      ctx.fillStyle = ctx.strokeStyle;
      ctx.font = `${Math.max(16, canvas.width / 40)}px sans-serif`;
      ctx.fillText(entityName(c.final_entity_id), x1, y1 > 20 ? y1 - 5 : y1 + 15);
    });
  }

  function renderList() {
    listEl.innerHTML = "";

    candidates.forEach((c, index) => {
      const li = document.createElement("li");
      li.className = "candidate-row" + (c.selected ? " candidate-row--selected" : "");
      li.addEventListener("click", () => selectCandidate(index));

      const select = document.createElement("select");
      MOCK_CATALOG.forEach((entry) => {
        const option = document.createElement("option");
        option.value = entry.id;
        option.textContent = entry.name;
        if (entry.id === c.final_entity_id) option.selected = true;
        select.appendChild(option);
      });
      select.addEventListener("click", (e) => e.stopPropagation());
      select.addEventListener("change", () => setFinalEntity(index, Number(select.value)));

      const bboxLabel = document.createElement("label");
      bboxLabel.className = "candidate-row__checkbox";

      const bboxCheckbox = document.createElement("input");
      bboxCheckbox.type = "checkbox";
      bboxCheckbox.checked = c.status === "needs_bbox";
      bboxCheckbox.addEventListener("click", (e) => e.stopPropagation());
      bboxCheckbox.addEventListener("change", () => toggleBboxStatus(index));

      bboxLabel.appendChild(bboxCheckbox);
      bboxLabel.appendChild(document.createTextNode("框不準"));

      li.appendChild(select);
      li.appendChild(bboxLabel);
      listEl.appendChild(li);

      if (c.selected) li.scrollIntoView({ block: "nearest" });
    });
  }
})();
