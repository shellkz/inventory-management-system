(function () {
  document.querySelectorAll(".delete-item-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const itemId = btn.dataset.itemId;
      const itemName = btn.dataset.itemName;

      if (!confirm(`確定要刪除「${itemName}」嗎？`)) {
        return;
      }

      const resp = await fetch(`/items/${itemId}`, { method: "DELETE" });

      if (!resp.ok) {
        const data = await resp.json();
        alert(`刪除失敗: ${data.message || resp.status}`);
        return;
      }

      location.reload();
    });
  });
})();
