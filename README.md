# Swagger to Frontend Code Generator

讀取 `input/swagger.json`（OpenAPI 3），產生 Angular 用的 API client 與 model，
輸出版型與 swagger-codegen（`typescript-angular`）一致。

## 環境需求

- Python 3.8 以上（作者環境為 3.14）。
- 不需要安裝任何第三方套件（只用到標準函式庫 `json`、`os`、`re`、`shutil`），不需要 `pip install`、虛擬環境或 `requirements.txt`。

安裝步驟（Windows）：

1. 到 https://www.python.org/downloads/ 下載並安裝 Python，安裝時勾選 **Add python.exe to PATH**。
2. 開新的終端機，確認安裝成功：
    ```bash
    python --version
    ```
   若找不到 `python`，可改用 `py --version`，並以 `py src/main.py` 執行。

## 使用方式

1. 把 `swagger.json` 放到 `input/`。
2. 執行：
    ```bash
    python src/main.py
    ```
3. 產出會在 `output/<swagger 的 title>/`（每次執行會清掉該資料夾再重新生成）：

    ```
    output/commencement.api/
      api/<tag>.service.ts   每個 swagger tag 一個 service，另有 api/api.ts
      model/<name>.ts        每個 schema 一個檔案，另有 model/models.ts
      api.module.ts, index.ts
      configuration.ts, encoder.ts, variables.ts, ...
    ```

## 注意事項

- 不需要手動修改 `swagger.json`（陣列的 request / response 會直接輸出成 `Array<T>`）。
- 固定不變的檔案（`configuration.ts`、`encoder.ts`、`variables.ts`）放在 `src/templates/`，要調整請改這裡。
- 如果怕可能有些環境拿到的swagger.json會有model或是api遺失,可以直接拿你做的api和他gen出來的model擷取使用。

調整歷程請見 [HISTORY.md](HISTORY.md)。
