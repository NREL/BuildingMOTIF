## Quick guide — how to add or modify the AFDD rules JSON

---

## 1 — AF-specific parameters
These fields are specific to PI System Asset Framework analyses. Keep them accurate; PI AF will use them to create analyses.

- **aftype** (string) — type of AF object; typically **"analysis"** for detection rules.  
- **aftimerule** (string) — AF time rule/plugin name (e.g., **"Periodic"**).  
- **frequency** (number) — run interval in seconds (e.g., **900** = 15 minutes).  
- **output** (string) — the analysis expression/config string that will be used by PI AF. This expression language and the exact operator/function support are PI-specific; **refer to the PI System Asset Framework manuals** for supported syntax, functions (MEAN, SQRT, MINIMUM, etc.), and boolean/comparison semantics.

---

## 2 — Definitions block — declaring inputs (detailed)
The definitions object names variables that your output expression will reference. Treat this as the mapping layer between semantic variable names (used in your rules) and how those variables are discovered in an asset’s PI AF model.

Key concepts

- Variable name: the key in definitions (e.g., Supply_Air_temperature_Sensor). Use this exact name in the output string.  
- Direct mapping: map a variable to a single expected point:
  - Example: "Mixed_Air_temperature_Sensor": {"hasPoint": "Mixed_Air_Temperature_Sensor"}
  - Behavior: the engine will look for a point on the AF element with that point name.

- Choice (fallback chain): provide multiple ways to resolve the same semantic variable. The engine will try each option in order until it finds a match. Use this when systems name points differently or when a value may exist in several forms.
  - Example:
    ```json
    "Supply_Air_temperature_Sensor": {
      "choice": [
        {"hasPoint": "Supply_Air_Temperature_Sensor"},
        {"hasPoint": "Zone_Air_Temperature_Sensor"}
      ]
    }
    ```
  - Explanation: first attempt to find a point named Supply_Air_Temperature_Sensor. If not found, try Zone_Air_Temperature_Sensor. The first successful match is used.

- Nested choice / hasPart (navigating structure): describe hierarchical relationships (component -> point). Use this to locate points that belong to a component under the element.
  - Example:
    ```json
    "VFD_Fan_Speed": {
      "choice": [
        {"hasPoint": "Fan_Speed_Command"},
        {"hasPart": {"Supply_Fan": {"hasPoint": "Speed_Command"}}}
      ]
    }
    ```
  - Explanation: first try a direct point named Fan_Speed_Command on the element. If absent, look for a child part named Supply_Fan and then a point named Speed_Command on that part.

- Mixed shapes and aliases:
  - Plain alias: "Minimum_OA_Fraction": "Minimum_OA_Fraction" — used when a variable is resolved elsewhere (e.g., provided by a dependency or a global constant).
  - Complex nesting: any depth of {"hasPart": {...}} can be used to precisely navigate an AF model hierarchy if your matcher supports it.

Best practices for definitions
- Keep variable names consistent and descriptive; they become the API in the output string.  
- Prefer choice blocks when equipment naming is inconsistent across sites. Order choices from most specific (preferred) to least.  
- When possible, test resolution against a sample AF element to confirm the matcher finds the intended point.  
- Use aliases only when you are certain the aliased name will be available at rule execution time (e.g., exported from another rule listed in dependencies).

---

## 3 — Output string — PI AF specifics
- This field contains the PI AF analysis expression/config used to compute values and the final boolean fault decision. Because syntax and supported functions/operators are PI-specific, consult the PI System Asset Framework documentation for exact rules (function names, comparison operators, how to represent True/False, precedence, etc.).  
- Typical constructs you will see:
  - Assignments: A = MEAN(SomeVar);
  - Functions: MEAN(), SQRT(), MINIMUM(), ABS(), etc.
  - Comparisons and thresholds: >=, <=, >>, << (but verify exact semantics in PI docs).
  - Conditional boolean expression: IF (...) THEN True ELSE False
  - Semicolon-separated statements when defining multiple intermediate variables.

Example pattern:
```
Var_A = MEAN(Sensor_A); Var_B = MEAN(Sensor_B); Threshold = 3.0; IF Var_A >> (Var_B + Threshold) THEN True ELSE False
```

---

## 4 — Dependencies
- Use the dependencies array to list other rule IDs whose outputs your rule requires (e.g., rules that compute averages or derived variables). PI AF importer/runner should ensure dependencies run first or that their outputs are available.  
- Example:
```json
"dependencies": ["G36VAV_SAT_POINTS","G36VAV_VFD_POINTS"]
```
- If a dependency provides a variable (e.g., Supply_Air_Temperature_Average), reference that exact variable name in your output. If dependency names differ, either alias them in definitions or align names.

---

## 5 — Naming conventions and validation checklist
- Use consistent variable naming and casing; names in definitions must match names used in output exactly.  
- Ensure every variable referenced in the output is either:
  - Declared in definitions, or
  - Provided by a dependency listed in dependencies, or
  - A known global constant supported by your runtime.  
- Validate JSON structure with a linter before saving.  
- Keep frequency reasonable for the rule’s dynamics (e.g., fast-changing signals -> shorter frequency).

---

## 6 — Examples

1) CO2 high rule (new):
```json
"Custom_CO2_High": {
  "name": "Custom — Zone CO2 high",
  "aftype": "analysis",
  "aftimerule": "Periodic",
  "frequency": 300,
  "applicability": ["VAV", "Zone"],
  "definitions": {
    "CO2_Sensor": {
      "choice": [
        {"hasPoint": "CO2_Sensor"},
        {"hasPoint": "Zone_CO2_Sensor"}
      ]
    }
  },
  "output": "CO2_Avg = MEAN(CO2_Sensor); CO2_Threshold = 1000; IF CO2_Avg >> CO2_Threshold THEN True ELSE False"
}
```

2) Cold spot depending on SAT average:
```json
"Custom_Cold_Spot": {
  "name": "Custom — Zone cold spot relative to SAT",
  "aftype": "analysis",
  "aftimerule": "Periodic",
  "frequency": 600,
  "applicability": ["VAV"],
  "dependencies": ["G36VAV_SAT_POINTS"],
  "definitions": {
    "Zone_Temp": {"hasPoint": "Zone_Air_Temperature_Sensor"},
    "Supply_Air_Temperature_Average": "Supply_Air_Temperature_Average"
  },
  "output": "Zone_Temp_Avg = MEAN(Zone_Temp); IF Zone_Temp_Avg << (Supply_Air_Temperature_Average - 2.0) THEN True ELSE False"
}
```