# Swagger to Frontend Code Generator

This project takes a `swagger.json` file as input and generates frontend-specific code, such as API clients and data models.

## How to Use

1.  Place your `swagger.json` file in the `input/` directory.
2.  Run the generation script:
    ```bash
    python src/main.py
    ```
3.  The generated files will be available in the `output/` directory.

4. 有些json裡面會在放一層array, 會導致多了[] (ex: CommencementCaseViewModel[]) => 記得sweager.json裡面要刪掉才不會出現

"responses": {
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "type": "array", => 如果是要給model,這行必須刪掉
          "items": {
            "$ref": "#/components/schemas/CommencementCaseViewModel"
          }
        }
      }
    }
  }
}

5. api改成解構賦值的形式, 方便在製作API的時候會因為順序問題報錯

6. 這個程式沒有分類, 所以需要可能先在NOTEPAD++去做比較或是清楚知道只要新增自己加上的API的情況下擷取使用, model會放在output/model裡自己去找出需要匯入匯出的model