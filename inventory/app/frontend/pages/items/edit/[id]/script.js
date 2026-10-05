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
})();
