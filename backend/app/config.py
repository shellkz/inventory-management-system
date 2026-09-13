"""服務設定值:環境變數集中在這裡讀取,其他模組不直接碰 os.environ。

DATABASE_URL 不開環境變數,固定是容器內的已知路徑——這個值必須跟 docker-compose.yml
的 volume mount 目的地(/app/data)對應,不是「每個部署會不一樣」的設定,開放給使用者填
只會製造填錯導致資料沒被持久化、卻不會有任何錯誤提示的風險。使用者要調整的是 volume
mount 左邊(host 資料夾),不是這個路徑,跟 vision-service 的 SAMPLES_DIR/SCANS_DIR 同一種處理方式。
"""
import os

DATABASE_URL = "sqlite:///./data/inventory.db"

VISION_SERVICE_URL = os.environ["VISION_SERVICE_URL"]
VISION_API_KEY = os.environ["VISION_API_KEY"]
