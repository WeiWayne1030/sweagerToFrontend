# Swagger to Frontend Code Generator

讀取 `input/swagger.json`（OpenAPI 3），產生 Angular 用的 API client 與 model，
輸出版型與 swagger-codegen（`typescript-angular`）一致。

## 使用方式

1. 把 `swagger.json` 放到 `input/`。
2. 執行：
    ```bash
    python src/main.py
    ```
3. 產出會在 `output/<swagger 的 title>/`（每次執行會清掉該資料夾再重新生成）：

    ```
    output/Chailease.Core.Commencement.API/
      api/<tag>.service.ts   每個 swagger tag 一個 service，另有 api/api.ts
      model/<name>.ts        每個 schema 一個檔案，另有 model/models.ts
      api.module.ts, index.ts
      configuration.ts, encoder.ts, variables.ts, ...
    ```

## 注意事項

- 不需要手動修改 `swagger.json`（陣列的 request / response 會直接輸出成 `Array<T>`）。
- 固定不變的檔案（`configuration.ts`、`encoder.ts`、`variables.ts`）放在 `src/templates/`，要調整請改這裡。

調整歷程請見 [HISTORY.md](HISTORY.md)。
