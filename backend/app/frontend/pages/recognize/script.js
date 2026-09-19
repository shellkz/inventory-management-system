(function () {
  const scanBtn = document.getElementById("scan-btn");
  const scanInput = document.getElementById("scan-input");
  const canvas = document.getElementById("scan-canvas");
  const ctx = canvas.getContext("2d");
  const resultList = document.getElementById("scan-result");

  scanBtn.addEventListener("click", () => scanInput.click());

  scanInput.addEventListener("change", () => {
    const file = scanInput.files[0];
    if (!file) return;

    const img = new Image();
    img.onload = () => {
      // 保留原始解析度,不縮小 canvas 內部尺寸,靠 CSS + 瀏覽器原生縮放看細節。
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      ctx.drawImage(img, 0, 0);
      recognize(file);
    };
    img.src = URL.createObjectURL(file);
  });

  async function recognize(file) {
    const formData = new FormData();
    formData.append("image", file);

    const resp = await fetch("/recognize", { method: "POST", body: formData });
    const data = await resp.json();
    drawResults(data.result);
  }

  function drawResults(results) {
    resultList.innerHTML = "";

    ctx.lineWidth = Math.max(2, canvas.width / 300);
    ctx.strokeStyle = "red";
    ctx.fillStyle = "red";
    ctx.font = `${Math.max(16, canvas.width / 40)}px sans-serif`;

    results.forEach((r) => {
      const [x1, y1, x2, y2] = r.bbox;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

      const label = r.meets_threshold ? `${r.entity_name} (${r.score.toFixed(2)})` : "未知";
      ctx.fillText(label, x1, y1 > 20 ? y1 - 5 : y1 + 15);

      const li = document.createElement("li");
      li.textContent = `${label} — bbox: [${r.bbox.map((n) => Math.round(n)).join(", ")}]`;
      resultList.appendChild(li);
    });
  }
})();
