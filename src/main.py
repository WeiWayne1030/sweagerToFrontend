import json
import os
import re
import html

# Define file paths
INPUT_FILE = os.path.join("input", "swagger.json")
OUTPUT_DIR = "output"
API_FILE_PATH = os.path.join(OUTPUT_DIR, "api.ts")
MODELS_DIR = os.path.join(OUTPUT_DIR, "model")
CONFIGURATION_FILE_PATH = os.path.join(OUTPUT_DIR, "configuration.ts")
VARIABLES_FILE_PATH = os.path.join(OUTPUT_DIR, "variables.ts")


def sanitize_filename(name: str) -> str:
    """Return a safe filename (no path separators, only [A-Za-z0-9_])."""
    # remove path separators and non-alnum -> replace with underscore
    safe = re.sub(r'[^0-9A-Za-z_]', '_', name)
    # avoid leading digits causing some tools issues
    if re.match(r'^\d', safe):
        safe = '_' + safe
    return safe

def safe_description(text: str) -> str:
    """Basic sanitization for description/comment to avoid embedding control chars."""
    if not text:
        return text
    # escape HTML/control chars and strip non-printables
    escaped = html.escape(str(text))
    escaped = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', escaped)
    return escaped

def openapi_type_to_ts_type(prop):
    """Converts OpenAPI data types to TypeScript types."""
    openapi_type = prop.get("type")
    
    if openapi_type == "integer":
        return "number"
    elif openapi_type == "string":
        return "string"
    elif openapi_type == "boolean":
        return "boolean"
    elif openapi_type == "object":
        return "object"
    elif openapi_type == "array":
        items = prop.get("items", {})
        item_ref = items.get("$ref")
        if item_ref:
            item_type = item_ref.split("/")[-1]
            return f"{item_type}[]"
        else:
            inner_type = openapi_type_to_ts_type(items)
            if inner_type.endswith("[]"):
                return inner_type
            return f"{inner_type}[]"
    elif "$ref" in prop:
        return prop["$ref"].split("/")[-1]
    elif "allOf" in prop:
        all_of = prop.get("allOf", [])
        if all_of and "$ref" in all_of[0]:
            return all_of[0]["$ref"].split("/")[-1]
    
    return "any"

def generate_operation_id(method, path):
    """Generates a camelCase operationId with method suffix."""
    path_cleaned = path.strip('/')
    path_cleaned = re.sub(r"\{(\w+)\}", r"By\1", path_cleaned)
    parts = re.split(r"[/_-]", path_cleaned)
    
    camel_case_parts = []
    for part in parts:
        if part:
            camel_case_parts.append(part.capitalize())
    
    path_name = "".join(camel_case_parts)
    if path_name:
        path_name = path_name[0].lower() + path_name[1:]
    
    method_suffix = method.capitalize()
    return f"{path_name}{method_suffix}"

def header_name_to_param_name(header_name):
    """Convert HTTP header name to camelCase parameter name."""
    parts = header_name.split('-')
    if not parts:
        return header_name.lower()
    
    result = parts[0].lower()
    for part in parts[1:]:
        if part:
            result += part.capitalize()
    return result

def _generate_destructured_params(path_params, header_params, query_params, request_body_type):
    """Generate destructured parameter interface and function signature."""
    
    interface_props = []
    
    # Add all parameters to the interface
    if request_body_type:
        interface_props.append(f"    body?: {request_body_type};")
    
    for header_name, header_type, required in header_params:
        param_name = header_name_to_param_name(header_name)
        optional = "" if required else "?"
        interface_props.append(f"    {param_name}{optional}: {header_type};")
    
    for param_name, param_type, required in query_params:
        optional = "" if required else "?"
        interface_props.append(f"    {param_name}{optional}: {param_type};")
    
    for param_name, param_type, required in path_params:
        optional = "" if required else "?"
        interface_props.append(f"    {param_name}{optional}: {param_type};")
    
    interface_props.append(f"    observe?: 'body' | 'response' | 'events';")
    interface_props.append(f"    reportProgress?: boolean;")
    
    interface_str = "{\n" + "\n".join(interface_props) + "\n  }"
    
    return interface_str

def generate_models_separate(swagger_data):
    """Generates separate .ts files for each model in the model directory."""
    if not swagger_data.get("components", {}).get("schemas"):
        return

    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)

    schemas = swagger_data["components"]["schemas"]
    
    for schema_name, schema_def in schemas.items():
        # collect referenced models for imports
        referenced = set()

        # scan properties for $ref or array items $ref or allOf
        properties = schema_def.get("properties", {}) or {}
        for prop_def in properties.values():
            # direct $ref
            if isinstance(prop_def, dict):
                if "$ref" in prop_def:
                    ref_name = prop_def["$ref"].split("/")[-1]
                    if ref_name != schema_name:
                        referenced.add(ref_name)
                # array of refs
                if prop_def.get("type") == "array":
                    items = prop_def.get("items", {}) or {}
                    if "$ref" in items:
                        ref_name = items["$ref"].split("/")[-1]
                        if ref_name != schema_name:
                            referenced.add(ref_name)
                # allOf/oneOf anyOf
                for comb in ("allOf", "oneOf", "anyOf"):
                    for item in prop_def.get(comb, []) if isinstance(prop_def.get(comb, []), list) else []:
                        if isinstance(item, dict) and "$ref" in item:
                            ref_name = item["$ref"].split("/")[-1]
                            if ref_name != schema_name:
                                referenced.add(ref_name)

        # build file content with imports
        content = '''/**
            * Swagger to Frontend - Auto Generated Model
            * Do not edit the file manually.
            */

            /* tslint:disable:no-unused-variable member-ordering */

        '''
        # add imports for referenced models (use sanitized filenames)
        if referenced:
            for ref in sorted(referenced):
                safe_ref = sanitize_filename(ref)
                content += f"import {{ {ref} }} from './{safe_ref}';\n"
            content += "\n"

        # interface definition
        content += f"export interface {schema_name} {{\n"
        
        if properties:
            for prop_name, prop_def in properties.items():
                ts_type = openapi_type_to_ts_type(prop_def)
                is_required = prop_name in schema_def.get("required", [])
                optional_mark = "" if is_required else "?"
                description = safe_description(prop_def.get("description", ""))
                
                if description:
                    content += f"    /**\n     * {description}\n     */\n"
                
                content += f"    {prop_name}{optional_mark}: {ts_type};\n"
        
        content += "}\n"

        safe_name = sanitize_filename(schema_name)
        file_path = os.path.join(MODELS_DIR, f"{safe_name}.ts")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"Generated: {file_path}")

    print(f"Successfully generated {len(schemas)} model files in {MODELS_DIR}")

def generate_api(swagger_data):
    """Generates an api.ts file with Angular HttpClient service using destructuring."""
    
    content = '''/**
        * Swagger to Frontend - API Service
        * No description provided (generated by Swagger Codegen)
        *
        * NOTE: This class is auto generated by the swagger code generator program.
        * Do not edit the class manually.
        */

        /* tslint:disable:no-unused-variable member-ordering */

        import { Inject, Injectable, Optional }                      from '@angular/core';
        import { HttpClient, HttpHeaders, HttpParams,
                HttpResponse, HttpEvent }                           from '@angular/common/http';

        import { Observable }                                        from 'rxjs';

    '''

    # Import all models
    if swagger_data.get("components", {}).get("schemas"):
        for schema_name in swagger_data["components"]["schemas"].keys():
            safe_name = sanitize_filename(schema_name)
            content += f"import {{ {schema_name} }}                                    from './model/{safe_name}';\n"

    content += '''
        import { BASE_PATH, COLLECTION_FORMATS }                     from './variables';
        import { Configuration }                                     from './configuration';

        @Injectable()
        export class ApiService {

            protected basePath = '/';
            public defaultHeaders = new HttpHeaders();
            public configuration = new Configuration();

            constructor(protected httpClient: HttpClient, @Optional()@Inject(BASE_PATH) basePath: string, @Optional() configuration: Configuration) {
                if (basePath) {
                    this.basePath = basePath;
                }
                if (configuration) {
                    this.configuration = configuration;
                    this.basePath = basePath || configuration.basePath || this.basePath;
                }
            }

            /**
            * @param consumes string[] mime-types
            * @return true: consumes contains 'multipart/form-data', false: otherwise
            */
            private canConsumeForm(consumes: string[]): boolean {
                const form = 'multipart/form-data';
                for (const consume of consumes) {
                    if (form === consume) {
                        return true;
                    }
                }
                return false;
            }

    '''

    # Generate methods for each endpoint
    for path, path_item in swagger_data.get("paths", {}).items():
        for method, operation in path_item.items():
            if method in ['parameters', 'servers', 'summary']:
                continue

            op_id = operation.get("operationId")
            if not op_id:
                op_id = generate_operation_id(method, path)

            summary = operation.get("summary", "")
            description = operation.get("description", "")
            
            path_params = []
            header_params = []
            query_params = []
            
            for p in operation.get("parameters", []):
                p_name = p["name"]
                p_type = openapi_type_to_ts_type(p.get("schema", {}))
                p_required = p.get("required", False)
                
                if p.get("in") == "path":
                    path_params.append((p_name, p_type, p_required))
                elif p.get("in") == "header":
                    header_params.append((p_name, p_type, p_required))
                elif p.get("in") == "query":
                    query_params.append((p_name, p_type, p_required))

            # Handle request body
            request_body_type = None
            if operation.get("requestBody"):
                request_body_schema = operation.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
                request_body_type = openapi_type_to_ts_type(request_body_schema)

            # Infer return type
            success_response = operation.get("responses", {}).get("200") or operation.get("responses", {}).get("201")
            return_type = "any"
            if success_response and "content" in success_response:
                response_schema = success_response.get("content", {}).get("application/json", {}).get("schema", {})
                return_type = openapi_type_to_ts_type(response_schema)

            # Generate destructured parameter interface
            destructured_params = _generate_destructured_params(path_params, header_params, query_params, request_body_type)
            
            content += f"    /**\n"
            if summary:
                content += f"     * {summary}\n"
            if description:
                content += f"     * {description}\n"
            content += f"     */\n"

            # Function signature with destructuring
            content += f"    public {op_id}(params: {destructured_params}): Observable<{return_type}> {{\n"
            
            # Extract parameters from destructured object
            content += "        const {\n"
            if request_body_type:
                content += "            body,\n"
            for header_name, _, _ in header_params:
                param_name = header_name_to_param_name(header_name)
                content += f"            {param_name},\n"
            for param_name, _, _ in query_params:
                content += f"            {param_name},\n"
            for param_name, _, _ in path_params:
                content += f"            {param_name},\n"
            content += "            observe = 'body',\n"
            content += "            reportProgress = false\n"
            content += "        } = params;\n\n"
            

            content += "        let headers = this.defaultHeaders;\n"
            
            # Add header parameters
            for header_name, header_type, _ in header_params:
                param_name = header_name_to_param_name(header_name)
                content += f"        if ({param_name} !== undefined && {param_name} !== null) {{\n"
                content += f"            headers = headers.set('{header_name}', String({param_name}));\n"
                content += f"        }}\n"

            # Add authentication
            content += "\n        // authentication (Bearer) required\n"
            content += "        if (this.configuration.apiKeys && this.configuration.apiKeys[\"Authorization\"]) {\n"
            content += "            headers = headers.set('Authorization', this.configuration.apiKeys[\"Authorization\"]);\n"
            content += "        }\n"

            # Add accept header logic
            content += "\n        // to determine the Accept header\n"
            content += "        let httpHeaderAccepts: string[] = [\n"
            content += "            'text/plain',\n"
            content += "            'application/json',\n"
            content += "            'text/json'\n"
            content += "        ];\n"
            content += "        const httpHeaderAcceptSelected: string | undefined = this.configuration.selectHeaderAccept(httpHeaderAccepts);\n"
            content += "        if (httpHeaderAcceptSelected != undefined) {\n"
            content += "            headers = headers.set('Accept', httpHeaderAcceptSelected);\n"
            content += "        }\n"

            # Add content-type header logic
            content += "\n        // to determine the Content-Type header\n"
            content += "        const consumes: string[] = [\n"
            if request_body_type:
                content += "            'application/json',\n"
                content += "            'text/json',\n"
                content += "            'application/_*+json'\n"
            content += "        ];\n"
            content += "        const httpContentTypeSelected: string | undefined = this.configuration.selectHeaderContentType(consumes);\n"
            content += "        if (httpContentTypeSelected != undefined) {\n"
            content += "            headers = headers.set('Content-Type', httpContentTypeSelected);\n"
            content += "        }\n"

            # Build URL with path parameters
            url_path = path
            for param_name, _, _ in path_params:
                url_path = url_path.replace(f"{{{param_name}}}", f"${{{param_name}}}")

            content += f"\n        return this.httpClient.request<{return_type}>('{method.lower()}',`${{this.basePath}}{url_path}`,"

            # Build request options object
            content += "\n            {\n"
            
            if request_body_type:
                content += "                body: body,\n"
            
            content += "                withCredentials: this.configuration.withCredentials,\n"
            content += "                headers: headers,\n"
            content += "                observe: observe as any,\n"
            content += "                reportProgress: reportProgress\n"
            content += "            }\n"
            content += "        );\n"
            content += "    }\n\n"

    content += "\n}\n"

    with open(API_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Successfully generated {API_FILE_PATH}")

def main():
    """Main function to run the generator."""
    print("Starting Angular TypeScript code generation with destructuring...")
    
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file not found at {INPUT_FILE}")
        return

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        swagger_data = json.load(f)

    generate_models_separate(swagger_data)
    generate_api(swagger_data)
    
    print("✅ Code generation finished successfully!")
    print(f"📁 Models generated in: {MODELS_DIR}")
    print(f"📄 API service generated: {API_FILE_PATH}")

if __name__ == "__main__":
    main()