# 資料庫 Schema（初版）

範圍：只涵蓋「耗材」（led/電容/電阻），不含「物品」。目標是系統運行時能同時累積資料供模型優化使用。

**這份文件混合了兩個獨立系統的 schema,分開看**:

- **辨識服務自己的表**(`recognition_entities`/`recognition_instances`/`recognition_samples`):辨識服務要實作、管理的東西,存在辨識服務自己的資料庫裡(SQLite,見 `docs/辨識服務部署方案.md`)
- **消費端範例(庫存 demo app)**(`items`/`inventory`/`stock_transactions`/`stock_transaction_items`):**不是辨識服務的一部分**,是拿庫存這個示範應用來說明「消費端該怎麼接」,實際會是消費端自己的資料庫(這裡假設用 Postgres,因為有較複雜的關聯查詢/交易保護需求)。辨識服務完全不知道這些表存在,唯一的接點是 `items.recognition_entity_id` 這個單向外鍵。

三項硬要求(驅動辨識服務那幾張表的設計):

1. **運作中能優化的能力**:新增/修正參考圖後,辨識準確度要能馬上反映,不用重新訓練、不用重啟服務
2. **運作一段時間後能 fine-tune 模型的能力**:蒐集實際掃描過的圖片+模型當下判斷+人工修正後的結果,累積成可以拿去訓練的資料
3. **辨識能力盡可能跟庫存分離**:辨識模組(認得出這是什麼)跟庫存模組(這個東西有多少)是兩個獨立關注點,只透過一個外鍵薄薄地接起來,不要互相依賴

---

## 辨識服務自己的表

**命名說明**:資料表用 `recognition_` 前綴(避免跟其他系統的表名衝突),但對外的 API 路徑不帶這個前綴(`/entities`、`/instances`、`/samples`,見 `docs/辨識服務API.md`)——前綴是資料庫內部的命名習慣,不是 API 合約的一部分。另外 `recognition_samples.vector` 這個欄位存的是 embedding 向量,但 API 對外一律叫「樣本圖片」(samples),使用者只上傳/管理照片,不會接觸到向量本身,這是刻意不外露的實作細節。

### recognition_entities（概念層 / 同一個東西）

對應「硬要求 1、3」。代表一個「概念上的東西」,例如「LED」——這是使用者真正在乎的層級,不是某個特定拍攝角度/顏色的變體。之前命名成 `recognition_groups`,但這張表代表的不是「一群東西」,是「同一個東西」,改名對齊語意。

| 欄位 | 型態 | 說明 |
|---|---|---|
| id | PK | |
| name | text, unique | 概念層的名稱(例如 `led`) |
| is_deleted | boolean, default false | 軟刪除標記,見下方說明 |
| created_at | timestamp | |

**`name` 唯一約束**:全域唯一,不分是否已軟刪除。原因是 `name` 在這個設計裡不只是顯示用的標籤,還是消費端做字串比對/查找時實際依賴的鍵值,允許重名會讓「哪個才是真正的 led」變成無法判斷的問題。軟刪除的列一樣佔用這個名稱,重新建立同名 entity 前得先處理(重新啟用或改名)舊的那筆——這是軟刪除(見下方)必然的副作用,不是獨立的額外限制。

### recognition_instances（變體 / 具體實例）

一個 `recognition_entities` 底下可以有多個變體(正面/背面、不同顏色、不同角度),各自有自己的特徵池。之前命名成 `recognition_entities`,但這張表代表的其實是「某個東西的其中一個具體樣貌」,改名成 `instances` 對齊語意,連帶讓 `items.recognition_entity_id` 的語意也變對(品項對應到概念層,不是對應到某個特定變體)。

不一定要拆變體——如果不需要區分「比對到哪個變體」,可以讓一個 `recognition_entities` 底下只有一個 `recognition_instances`,把所有參考圖都混進同一個特徵池,靠取最高分比對即可,不強制使用者建立變體概念(見 `docs/影像辨識.md` 顏色變體的討論)。

| 欄位 | 型態 | 說明 |
|---|---|---|
| id | PK | |
| entity_id | FK -> recognition_entities | 屬於哪個概念層的東西 |
| name | text, unique(entity_id, name) | 變體名稱(例如 `led_front`),沒有變體概念時可以直接跟 entity 同名 |
| is_deleted | boolean, default false | 軟刪除標記,見下方說明 |
| created_at | timestamp | |

**`name` 唯一約束(複合)**:只在同一個 `entity_id` 底下唯一,不是全域唯一——不同 entity 底下出現同名 instance(例如兩個不同 entity 都有一個叫 `front` 的變體)是合理情境,不該互相衝突。跟 `recognition_entities.name` 一樣,重名的實際問題是「同一個 entity 底下沒辦法分辨兩個同名變體指的是哪一個」,而不是美觀問題。

**`is_deleted` 軟刪除**:`recognition_entities`/`recognition_instances` 都有這個標記,`DELETE` 不會真的移除那一列,只把 `is_deleted` 設成 `true`,id 永久保留、不重用。原因是 `items.recognition_entity_id` 這種跨系統參照沒有真正的資料庫外鍵保護(見上方「消費端範例」章節),真的刪除會讓消費端手上的 id 變成查無此 id、又查不到任何線索;軟刪除之後,`GET /entities/{id}` 一樣回 `200`,只是 `is_deleted: true`,消費端至少查得到「這個東西曾經存在、現在被刪了」,而不是一個無法解釋的 `404`(這才是軟刪除唯一實際解決的問題——**消費端主動查詢時能不能查到解釋**,不是「消費端會不會主動去查」,後者沒有解法,要嘛消費端自己排程檢查、要嘛之後另外做 webhook 通知)。

刪除 entity 會連帶把底下所有 instances 的 `is_deleted` 也設成 `true`(軟刪除版本的 cascade)。`recognize()` 比對時排除 `is_deleted = true` 的 entity/instance,不會再被匹配到。`recognition_samples` 不套用軟刪除,直接物理刪除即可——樣本圖片是頻繁增減的葉節點,沒有外部系統會參照到單一 sample 的 id,不需要留存這個追溯能力。

### recognition_samples（特徵池)

對應「硬要求 1」。存的是**一批向量**,不是單一平均後的 prototype——單一平均向量在類別內有視覺變化時(例如同一種 LED 有多種顏色)會失真,平均後的向量會偏向某個變體、對其他變體泛化差(見 `docs/影像辨識.md` 的討論)。改成存一整池向量,`recognize()` 比對時可以跟池裡每個向量都算相似度、取最高分,不受單一平均值拖累。拆不拆 `recognition_instances` 對比對準確度沒有影響(數學上,對多個 pool 分別取最高分再取全域最高分,等價於對合併後的單一 pool 取最高分),差別只在於能不能額外得知「比對到哪個變體」。

新增一筆到這張表,馬上就會反映在下一次辨識請求上(只要 catalog 快取機制有對應更新,見下方「運作中優化」小節)——不需要重新訓練、不需要重啟服務,滿足硬要求 1。

| 欄位 | 型態 | 說明 |
|---|---|---|
| id | PK | |
| instance_id | FK -> recognition_instances | |
| vector | 見下方存法 | embedding 向量,對應 `final_bbox` 裁切出來的區域算出來的 |
| predicted_bbox | nullable | 建立當下 FastSAM 自動偵測(挑面積最大的候選框)的原始結果,寫入後不再變動;找不到候選框時為 null(fallback 用整張圖) |
| final_bbox | nullable | 目前實際生效、拿去算 `vector` 的區域,建立時等於 `predicted_bbox`,可以被 `PATCH /samples/{id}` 修正 |
| image_path | text | 這個向量是從哪張圖算出來的,方便之後回溯/重算/汰換品質不好的樣本;存的是相對檔名,實體檔案放在服務內部固定路徑 `/app/data/samples/`(見下方「圖片實體檔案存放」)。**存的是完整原圖,不是裁切後的結果**——`final_bbox` 被修正時才有東西可以重新裁切 |
| created_at | timestamp | |

**vector 欄位存法**:辨識服務用 SQLite(見 `docs/辨識服務部署方案.md`),沒有 pgvector 這種原生向量型態,存成 JSON 編碼的浮點數陣列或 BLOB,由應用層自己序列化/反序列化。這個專案的資料規模(幾十到幾千筆向量)不需要索引優化,brute-force 用 numpy 算 cosine similarity 就夠快,不差 pgvector 那個索引能力。

**`predicted_bbox`/`final_bbox` 存在的原因**:建樣本時如果把整張參考圖直接丟給 DINOv2,背景(常見是拍攝用的桌面)會稀釋掉物件本身的視覺特徵,構圖類似的不同物件容易在 embedding 空間裡意外地相近(實測案例:硬幣被誤判成瓶蓋,見 `docs/影像辨識.md` 第 6 節)。所以建立樣本時會先跑 FastSAM 抓候選框、挑面積最大的當作物件本體、裁切後才算 embedding。但這個自動偵測不保證每次都對(低對比度物件可能被 FastSAM 整個框錯,同樣見 `docs/影像辨識.md` 案例),所以留 `predicted_bbox` 記錄原始猜測、`final_bbox` 讓使用者事後修正,兩者的落差之後也是 FastSAM fine-tune 的訓練訊號——跟 `recognition_predictions` 的 `predicted_instance_id`/`final_instance_id` 是同一種「模型先猜、人工修正」的命名慣例,但代表的錯誤來源不同(那邊是物件之間的 containment 合併,這邊是物件跟背景的分割不足),兩者是獨立的欄位、不共用同一張表,見 `docs/影像辨識.md` 的討論。

**圖片實體檔案存放**:`recognition_samples.image_path`(參考樣本圖)跟 `recognition_predictions.image_path`(掃描圖,見下方)兩個欄位名一致(都只是「這筆紀錄對應的圖片檔案在哪」,不需要 `source_` 前綴消歧義),但**實體檔案分開存放**,不放同一個資料夾:

```
/app/data/samples/   # recognition_samples 參考圖,不自動清除
/app/data/scans/      # recognition_predictions 掃描圖,見下方清除規則
```

分開放的原因是兩者的清除規則完全不同(見下方),分資料夾之後清除程式只要掃 `scans/`,不用在同一個資料夾裡靠邏輯篩選哪些能刪、哪些不能刪。都是服務容器內部的固定路徑,不開環境變數讓使用者自訂——跟模型路徑不同,這裡沒有「內容會變」的自訂需求,唯一要解決的是「重啟 container 資料還在」,第三方開發者在自己的 `docker-compose.yml` 掛 volume 到這兩個固定路徑即可(見 `docs/辨識服務部署方案.md`)。

**掃描圖清除規則**(`recognition_predictions` 專用,`recognition_samples` 的參考圖不自動清除):

- 清除對象只限 `annotation_status = confirmed` 的紀錄。`pending_review` 的紀錄沒有向量備份,圖片是唯一的標註依據,不管多舊、超過多少張都不會被自動刪除——這是唯一「正在使用中,不能刪」的情況
- 觸發條件是**張數**,不是磁碟容量比例:超過 `recognition_config.max_retained_scan_images`(見下方)時,從 `confirmed` 的紀錄裡挑最舊的刪到剩下上限張數為止。不用容量比例的原因是那需要讀取宿主機磁碟使用量,耦合到每個第三方部署不同的檔案系統環境;用固定張數換算大致的磁碟用量已經夠準(單張圖片有 20MB 上限)
- 不做「淘汰表現不好的」這種更複雜的規則:`confirmed` 的掃描圖不管新舊,資訊要嘛已經在 `recognition_samples` 的向量裡,要嘛已經匯出訓練過,剩餘價值差不多,沒有強理由建立額外的統計/追蹤機制去判斷「表現好壞」
- 只刪圖片檔案本體,`recognition_predictions` 的資料列本身不刪(`image_path` 會變成死連結,但 `predicted_*`/`final_*` 等欄位還在,訓練資料匯出統計不受影響)

### recognition_predictions（預測紀錄,兼未來 fine-tune 資料池)

對應「硬要求 2」。辨識服務自己的預測+人工修正紀錄,不綁定任何消費端的業務邏輯(沒有 `transaction_id`、沒有 `operator_id` 這類業務欄位)——任何消費端呼叫 `/predict` 就自動獲得追蹤能力,不用各自重做一套。

`image_path` 本身就是這次掃描的分組鍵,不用另外存 session id:只要圖片儲存機制保證每次存檔都是新路徑(時間戳/UUID 檔名,不覆蓋舊檔),同一個 `image_path` 底下的多筆紀錄自然就代表「同一次 `/predict` 呼叫的所有候選框」,查詢「這張圖是否全部確認完」直接 `WHERE image_path = X` 即可。

| 欄位 | 型態 | 說明 |
|---|---|---|
| id | PK | |
| image_path | text | 這次掃描的圖片參照;實體檔案存在服務內部固定路徑 `/app/data/scans/`(見上方「圖片實體檔案存放」與清除規則),這裡存的是相對檔名 |
| predicted_instance_id | FK -> recognition_instances, nullable | 模型當下判斷的變體(全域最高分對應的身份,不管有沒有過 `score_threshold`;只有特徵池完全沒有樣本時才是 null) |
| predicted_score | float, nullable | |
| predicted_bbox | nullable | |
| final_instance_id | FK -> recognition_instances, nullable | 人工確認/修正後的答案,未確認前為 null |
| final_bbox | nullable | |
| annotation_status | enum | pending_review / confirmed |
| created_at | timestamp | |

**現在只需要做到「追蹤」**(把每次 `/predict` 的原始輸出存下來),標註 UI、匯出訓練集、上雲端訓練這幾步都是**建在這張表上面的功能**,不需要為了它們現在就改 schema:
- 標註 UI:查 `WHERE annotation_status = 'pending_review'`,人工看完後 `PATCH final_instance_id`/`final_bbox`、改成 `confirmed`
- 匯出訓練集:篩 `annotation_status = 'confirmed'` 的紀錄,用 `image_path` 分組、判斷整張圖是否都確認完(邏輯跟消費端 `stock_transaction_items` 的匯出規則一致,見下方)
- 上雲端訓練:匯出完之後的部署/維運流程,不是資料庫要管的事

### recognition_config（執行期可調參數)

對應「硬要求 1」的延伸:不只樣本池,直接影響辨識行為的參數(例如判定門檻)也要能不重啟服務就調整,交給運行中的 `PATCH /config`(見 `docs/辨識服務API.md`)動態改。永遠只有一列——這些參數是服務程式碼自己定義、看得懂的固定小清單,不是使用者可以任意新增的動態鍵值,所以用**每個參數一個型別化欄位**,不用 key-value 表:資料庫直接保證型別正確、可以加 `CHECK` 約束(例如 `score_threshold` 限制在 0~1 之間),不需要應用層另外維護一份 key -> 型別的對照表。新增可調參數 = 加一個欄位(一次 migration),跟其他表的演進方式一致。

| 欄位 | 型態 | 說明 |
|---|---|---|
| score_threshold | float, default 0.6 | `/recognize` 用來算每個候選框 `meets_threshold` 的建議門檻(判斷責任交給呼叫端,見 `docs/辨識服務API.md`),對應 `recognize.py` 現有的 `SCORE_THRESHOLD` 常數 |
| crop_padding_ratio | float, default 0.1 | 裁切候選框時往外多留的比例,對應 `recognize.py` 現有的 `CROP_PADDING_RATIO` 常數 |
| max_retained_scan_images | int, default 10000 | `/app/data/scans/` 底下 `confirmed` 掃描圖的保留張數上限,超過從最舊的開始刪,見上方「掃描圖清除規則」 |
| updated_at | timestamp | |

---

## 消費端範例(庫存 demo app,不是辨識服務的一部分)

### items（品項主檔）

固定幾筆，代表目前系統認識的耗材種類。

| 欄位 | 型態 | 說明 |
|---|---|---|
| id | PK | |
| name | text | |
| category | text | led / capacitor / resistor |
| min_stock | int | 低庫存提醒門檻 |
| recognition_entity_id | FK -> 辨識服務的 recognition_entities.id, nullable | 對應到辨識服務的哪個概念層東西(不是變體);可以是 null(這個品項還沒建立辨識能力,純手動記帳)。這是**跨系統的參照**,不是同一個資料庫裡的 FK(辨識服務用自己的 SQLite,這裡存的是它的 id 值,不能建實際的資料庫外鍵約束) |
| created_at | timestamp | |

### inventory（庫存現況）

跟 `items` 現為 1:1，獨立成表是因為未來可能擴充成多地點/多櫃位（PK 會變成 `(item_id, location_id)`），且能避免管理員編輯品項資料時的表單連帶覆蓋 `quantity`（見下方「設計決策」）。

| 欄位 | 型態 | 說明 |
|---|---|---|
| item_id | PK / FK -> items | |
| quantity | int | 現有數量 |
| updated_at | timestamp | |

### stock_transactions（出入庫事件）

一次掃描/一個 session 一筆，是明細（`stock_transaction_items`）的 header。

| 欄位 | 型態 | 說明 |
|---|---|---|
| id | PK | |
| type | enum | in / out |
| operator_id | text | |
| image_path | text | 掃描圖片 |
| created_at | timestamp | |

### stock_transaction_items（出入庫明細，兼訓練資料池）

對應「硬要求 2」。一次出入庫對應多筆（每個被辨識/新增的物件各一筆）。同時作為出入庫記帳依據與待標註訓練資料，不另開表，避免同一份 image/class 資訊存兩份導致不同步。

| 欄位 | 型態 | 說明 |
|---|---|---|
| id | PK | |
| transaction_id | FK -> stock_transactions | |
| final_item_id | FK -> items, nullable | 最終確認品項，未確認前為 null |
| final_bbox | nullable | 標註後台確認/修正後的框，未確認前為 null |
| predicted_class | text, nullable | 辨識服務回傳的類別字串(對應辨識服務 `recognition_entities.name`,但不做 FK,見下方),manual_add 時為 null |
| predicted_class_score | float, nullable | DINOv2 跟 catalog 比對出來的分類相似度分數(原 `predicted_confidence`,改名以跟下一欄區分) |
| predicted_objectness_conf | float, nullable | FastSAM 對這個候選框「這裡有東西」的信心分數,跟分類分數是兩件不同的事,新架構下兩者都存,不能只存一個 |
| predicted_bbox | nullable | 模型原始輸出框，manual_add 時為 null |
| source | enum | auto_detected / manual_add / manual_correct |
| annotation_status | enum | pending_review / needs_bbox / confirmed |
| created_at | timestamp | |

## 設計決策備忘

- **items / inventory 分表**：管理員編輯品項（低頻）跟出入庫更新數量（高頻）若合表，管理員表單若整列送出會有覆蓋剛更新之 `quantity` 的 race condition 風險；分表從架構上排除此風險，並讓未來多地點擴充不需破壞性 migration。

- **辨識服務跟庫存是兩個獨立資料庫,不是同一個系統**：辨識服務(`recognition_entities`/`recognition_instances`/`recognition_samples`)完全不知道 `items`/`inventory` 存在,只有 `items` 單向存一個辨識服務的 id 值。辨識服務可以獨立運作(先建檔、先測試辨識效果),不需要庫存模組存在才有意義;反過來,庫存品項也可以先不具備辨識能力(`recognition_entity_id` 為 null,純手動記帳)。因為是跨系統參照,不是資料庫層級的外鍵約束,一致性要靠應用層自己維護(例如辨識服務要刪除一個還有消費端在引用的 entity 時,該有明確的錯誤處理,不能靜默刪除)。

- **recognition_entities/recognition_instances 拆兩層**：見上方兩張表的說明。拆分不影響比對準確度,只影響能不能取得「比對到哪個變體」這個額外資訊。不需要變體概念時,一個 entity 底下放一個 instance 即可,不強迫使用者建立階層。

- **特徵池(`recognition_samples`)而不是單一 prototype 欄位**：見上方該表說明。額外的好處是可以個別刪除/汰換品質不好的樣本(單筆 `DELETE`),不用像陣列型態那樣整包讀寫。

- **`recognition_predictions` 跟消費端 `stock_transaction_items` 不是重複資料**：兩者都有 `predicted_*`/`final_*` 欄位,看起來像重複,但回答的是不同問題——`stock_transaction_items.final_item_id` 回答「這是我庫存裡的哪個品項」(業務層答案),`recognition_predictions.final_instance_id` 回答「這是視覺上的哪個變體,修正後拿去 fine-tune 用」(辨識層答案)。消費端 UI 上一次人工修正動作,預期會同時寫兩邊:寫自己的 `stock_transaction_items`(業務記帳)+ 呼叫辨識服務的 API 寫 `recognition_predictions`(辨識層追蹤),不是同一份資料存兩次,是兩個系統各自記錄自己在乎的答案。

- **predicted_\* 與 final_item_id/final_bbox 分開存**：`predicted_class`/`predicted_bbox` 是模型當下的原始輸出，寫入後不可變，用來保留「模型原本說了什麼」；`final_item_id`/`final_bbox` 是人工確認後的最終答案。兩者差異即為訓練訊號，可對應「沒找到／找錯位置／分錯類」三種錯誤類型，外加新架構下才會出現的第四種：
  - `predicted_class == final_item_id 對應名稱`：辨識正確
  - `predicted_class` 有值、與最終 `final_item_id` 不同：分錯類
  - `predicted_class` 為 null、`source=manual_add`：沒找到
  - `predicted_bbox` 涵蓋範圍明顯大於單一物件、對應到多個 `final_item_id`：候選框合併(FastSAM 的 containment 去重把緊貼物件誤判成同一個,見 `docs/影像辨識.md` 的已知限制)——這是 segmentation-based 候選生成特有的錯誤模式,YOLO 的固定 anchor/grid 機制不太會有這種問題,是新架構才需要留意的第四類

- **predicted_class 不做成 FK**：辨識服務的 `recognition_entities` 是運作中可以隨時新增/修改的表,不是綁死在某個訓練好的模型檔案裡。但更根本的原因是**這是兩個獨立資料庫**,物理上無法建立跨資料庫的 FK 約束;就算 `predicted_class` 拿的是辨識服務快取(`model_holder`)裡當下的字串,也可能跟資料庫最新狀態有時間差。保持鬆散字串，分析/查詢時可以用字串對辨識服務的 `recognition_entities.name` 做 join，不需要靠 FK 約束。

- **不用 `transactions.source_items`/`refined_items` 陣列存**：`final_item_id`/`annotation_status` 等欄位會被頻繁當作查詢/更新條件（如標註後台列出所有 `pending_review` 項目、單筆更新 `final_bbox`），陣列型態無法對元素建索引，且單筆更新需整包讀寫，多人同時標註同一張圖的不同物件會有覆蓋風險。分表後這些操作都是單純的 `WHERE`/`UPDATE`，天然無此問題。

- **不需要為原始 Kaggle 訓練集補 record**：那是系統上線前的離線資料，跟 `stock_transaction_items` 累積的「上線後蒐集的新樣本」性質不同，混在一起會難以區分資料來源。若要追蹤模型版本沿革，可另開簡單的 `model_versions` 表（`id, file_name, trained_at, note`），非本次 schema 必要項目。

## 運作中優化(硬要求 1):特徵池更新路徑

新增/修正一筆 `recognition_samples`,不需要整張圖的其他物件都 `confirmed`,單筆 `confirmed` 就能用。因為 `recognition_predictions` 現在是辨識服務自己的表,這步驟不用再跨系統跟消費端要資料,辨識服務自己查自己的表就好:

```sql
-- 辨識服務自己查: 哪些預測已經被確認, 可以拿去更新特徵池
SELECT image_path, final_bbox, final_instance_id
FROM recognition_predictions
WHERE annotation_status = 'confirmed'
  AND final_instance_id IS NOT NULL
```

辨識服務拿到 `final_bbox` 對應的裁切圖(從 `image_path` 讀),重算一次 embedding,寫進 `recognition_samples`。這步驟本身很輕量,但要讓辨識「馬上反映」,辨識服務內部的 catalog 快取(目前是開機時讀一次、不會變的記憶體快取)需要跟著改成可以在 runtime 被更新的結構——這是辨識服務內部的實作問題,留給實作階段決定,不是 schema 要解的事。

消費端提交修正時(例如庫存的標註後台),一次人工確認動作預期會觸發兩個寫入:消費端自己的 `stock_transaction_items.final_item_id`(業務記帳)+ 呼叫辨識服務的 API 寫 `recognition_predictions.final_instance_id`(辨識層追蹤,見上方表格說明)。

## 未來可能的模型 fine-tune(硬要求 2):訓練資料匯出規則

FastSAM 底層是 `ultralytics`(YOLOv8-seg 架構),要 fine-tune 它用的還是 YOLO 風格的 class-index + bbox/mask 標註格式,所以這條路徑保留原本的匯出邏輯,不是 DINOv2 在用的(DINOv2 走上面「運作中優化」那條輕量路徑,不需要整圖確認)。這條路徑現在是**辨識服務自己就能完成**的事(資料源是自己的 `recognition_predictions`,不用跟消費端要),消費端不用參與這一步,只有實際執行 fine-tune、把訓練完的權重換上去,才需要辨識服務維護者手動操作。

匯出可訓練資料時，篩選單位是 **`image_path`(一張圖)而非單筆預測**：同一個 `image_path` 底下所有 `recognition_predictions` 都必須是 `annotation_status = confirmed`，整張圖才可用；只要有任一筆未確認，整張圖都不能匯出。原因：物件偵測訓練若使用部分標註的圖片，未標註區域會被視為背景（負樣本），等同教模型「這裡沒有物件」，比不使用這張圖更有害。這個限制對 FastSAM(或任何物件偵測器)fine-tune 依然成立,不是 YOLO 專屬的過時規則。

```sql
-- 可訓練的圖片：同一個 image_path 底下所有預測皆已 confirmed
SELECT image_path
FROM recognition_predictions
GROUP BY image_path
HAVING COUNT(*) = COUNT(*) FILTER (WHERE annotation_status = 'confirmed');
```

匯出時 `final_instance_id` → YOLO class index 的對應需在匯出腳本中固定（例如依 `recognition_instances.id` 排序產生 `data.yaml` 的 `names`），確保每次匯出順序一致。
