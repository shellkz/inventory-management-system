# IDE型別提示設置

實際執行都在Docker容器裡，本機不用裝依賴也能跑起來。但本機沒裝的話，IDE不會有型別提示/自動完成。

## 1. 安裝

1. 確定在inventory-management-system目錄內，執行:
```bash
cd inventory
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
cd ..
```

2. 有負責視覺辨識的人，才執行(不是的人，後面都不用看了)：
```bash
cd vision-service
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
cd ..
```

## 2. 設定Python Interpreter(以VSCode為例)
裝完依賴後，IDE要分別指向`inventory/.venv`跟`vision-service/.venv`這兩個直譯器，每個repo各自設定，不是整個資料夾共用一個。

1. VSCode裡開啟`inventory-management-system`資料夾後，File → Add Folder to Workspace，把`inventory`跟`vision-service`兩個資料夾分別加進來
2. 點左側檔案總管裡`inventory`這個資料夾底下任一個檔案，確保焦點在這個資料夾上
3. 按`Ctrl+Shift+P`開啟命令選單，輸入:
   ```
   > Preferences: Open Folder Settings (JSON)
   ```
   選取後會開啟(或建立)`inventory/.vscode/settings.json`
4. 寫入:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe"
}
```
5. 點左側檔案總管裡`vision-service`這個資料夾底下任一個檔案，確保焦點在這個資料夾上
6. 按`Ctrl+Shift+P`開啟命令選單，輸入:
   ```
   > Preferences: Open Folder Settings (JSON)
   ```
   選取後會開啟(或建立)`vision-service/.vscode/settings.json`
7. 寫入:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe"
}
```
8. 完成後，編輯哪邊的檔案，VSCode就套用那邊的設定