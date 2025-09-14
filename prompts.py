# prompts.py

# 1. [Sufficient Positive] 제외가 확실한 '충분한 증거 조합'을 포함하는 코드 생성
GENERATE_SUFFICIENT_POSITIVE_CODE_PROMPT = """
You are an expert senior iOS developer building a production-grade app. Your task is to write a comprehensive, realistic Swift code file that demonstrates real-world usage of an obfuscation-unsafe pattern.

**Target Pattern:** "{pattern_description}"

**Required Evidence (ALL must be present):** {evidence_list}

**Requirements for Realistic Complexity:**
- Include at least 2-3 classes, structs, or extensions
- Add realistic property declarations, method implementations, and business logic
- Include realistic imports and framework usage (UIKit, Foundation, etc.)
- Use proper iOS app architecture patterns (MVVM, Delegate patterns, etc.)
- Add error handling, completion handlers, or async/await where appropriate
- Include realistic method names, property names, and class hierarchy
- Make it feel like actual production code from a real iOS app

**Domain Context:** Choose from one of these realistic scenarios:
- A user authentication system with biometric/keychain integration
- A media player with AVFoundation integration
- A networking layer with custom serialization
- A CoreData model with custom transformations
- A custom UI component library
- A background sync system with push notifications
- An analytics/logging framework
- A payment processing module

The generated identifiers MUST be candidates for obfuscation exclusion due to the evidence combination.
Your response must be ONLY the raw Swift code (minimum 50 lines), without comments or markdown blocks.
"""

# 2. [Insufficient Positive] 제외하기엔 '불충분한 증거'만 포함된 '함정' 코드 생성
GENERATE_INSUFFICIENT_POSITIVE_CODE_PROMPT = """
You are an expert senior iOS developer building a production-grade app. Your task is to write comprehensive, realistic Swift code that APPEARS related to a sensitive pattern but is actually SAFE to obfuscate.

**Pattern Context (but AVOID making it truly unsafe):** "{pattern_description}"

**Weak Evidence to Include (but avoid stronger evidence):** {evidence_list}

**Requirements for Realistic Complexity:**
- Include at least 2-3 classes, structs, or extensions with realistic business logic
- Add proper iOS framework integration (UIKit, Foundation, SwiftUI)
- Use modern Swift patterns (async/await, Combine, property wrappers)
- Include realistic error handling and edge cases
- Add delegate patterns, completion handlers, and proper separation of concerns
- Make it production-quality code that developers would actually write

**Domain Context:** Choose from realistic iOS app scenarios:
- User interface management without runtime string dependencies
- Data processing with type-safe APIs
- Modern networking with Codable and structured responses
- Business logic with pure functions and value types
- State management with observable patterns
- File I/O with structured data formats

CRITICAL: The code should look sophisticated and related to the pattern, but must NOT contain sufficient evidence for exclusion. All identifiers should be safe to obfuscate.

Your response must be ONLY the raw Swift code (minimum 50 lines), without comments or markdown blocks.
"""

# 3. [Combined Positive] 두 개의 다른 패턴을 '조합'한 복잡한 코드 생성
GENERATE_COMBINED_CODE_PROMPT = """
You are an expert senior iOS developer building a complex, enterprise-grade iOS application. Your task is to write a comprehensive Swift code file that naturally combines TWO distinct obfuscation-unsafe patterns in a realistic scenario.

**Pattern 1:** "{pattern1_description}"
**Required Evidence 1:** {pattern1_evidence}

**Pattern 2:** "{pattern2_description}"
**Required Evidence 2:** {pattern2_evidence}

**Requirements for Enterprise-Level Complexity:**
- Create a cohesive system that naturally requires BOTH patterns
- Include 4-6 related classes/structs with proper separation of concerns
- Add realistic dependency injection, protocol conformance, and architecture patterns
- Include proper error handling, logging, and edge case management
- Use modern iOS frameworks appropriately (SwiftUI, Combine, async/await)
- Add realistic data models, view controllers, and business logic layers
- Include proper lifecycle management and memory handling

**Suggested Complex Scenarios:**
- A media streaming app with CoreData persistence AND JavaScript bridge communication
- A social app with Objective-C runtime features AND public API framework
- An enterprise app with foreign function interface AND SwiftUI state management  
- A financial app with serialization contracts AND system framework overrides
- A productivity app with accessibility features AND keypath-based data binding

The final code should feel like a real production module where both patterns naturally coexist and serve the business requirements.

Your response must be ONLY the raw Swift code (minimum 80 lines), without comments or markdown blocks.
"""

# 4. [Negative] 제외 근거가 전혀 없는 '안전한 대체' 코드 생성
GENERATE_NEGATIVE_CODE_PROMPT = """
You are an expert senior iOS developer focused on writing modern, safe, and maintainable Swift code. Your task is to write production-quality Swift code that provides similar functionality to a risky pattern, but using safe, modern approaches.

**Risky Pattern to Avoid:** "{pattern_description}"

**Requirements for Safe, Modern Implementation:**
- Use type-safe Swift APIs instead of string-based runtime mechanisms
- Prefer closures, delegates, and protocol-oriented design over reflection
- Use structured data types and strong typing instead of stringly-typed APIs
- Implement proper Swift concurrency (async/await, actors) where appropriate
- Use SwiftUI's declarative patterns instead of runtime UI manipulation
- Prefer compile-time safety over runtime flexibility

**Safe Alternatives to Implement:**
- Replace #selector with closure-based callbacks
- Use structured configuration instead of runtime string keys  
- Implement type-safe networking with Codable instead of dynamic parsing
- Use SwiftUI @State/@Binding instead of KVO/dynamic properties
- Replace runtime class instantiation with dependency injection
- Use compile-time protocol conformance instead of runtime checks

**Code Quality Requirements:**
- Include 3-4 classes/structs with realistic business logic
- Add proper error handling and validation
- Include unit test-friendly architecture with protocol abstractions
- Use modern Swift language features (property wrappers, result builders, etc.)
- Add realistic data flow and state management

The result should be robust, maintainable code that accomplishes similar goals but with compile-time safety.

Your response must be ONLY the raw Swift code (minimum 60 lines), without comments or markdown blocks.
"""

# 5. [Labeling] - AST 분석 및 라벨링 프롬프트
GENERATE_LABEL_PROMPT = """
You are an expert Swift code auditor specializing in obfuscation safety.
Analyze the provided Swift code and its corresponding AST symbol information to identify all identifiers that MUST be excluded from obfuscation.

**Critical Analysis Rule: Sufficiency of Evidence**
- An identifier should only be excluded if the evidence is **sufficient** to cause a runtime failure or break a contract if the name is changed.
- Do not exclude an identifier just because one piece of weak evidence exists. You must evaluate if the **combination of evidence** creates a high risk.
- **Example of Insufficient Evidence:** A class that only `inherits: 'NSObject'` but has no other Objective-C attributes is likely safe.
- **Example of Sufficient Evidence:** A class that `inherits: 'NSObject'` AND has a property with `modifiers: ['@objc', 'dynamic']` must be excluded.

**Swift Source Code:**
```swift
{swift_code}
```
AST Symbol Information (JSON):
```json
{symbol_info_json}
```

Based on your analysis and the Sufficiency of Evidence rule, provide a JSON response with two keys: "reasoning" and "exclusions".

reasoning (Chain of Thought):
Provide a step-by-step explanation for your decisions. For each potential candidate, first state the evidence from the AST info. Then, explicitly state whether this evidence is sufficient for exclusion and why. If the evidence is insufficient, explain why it's safe to obfuscate.

exclusions:
An array of objects for identifiers where the evidence was sufficient for exclusion. Each object must contain:

identifier: The name of the symbol to exclude.

reason_category: The L1 reason for exclusion.

matched_pattern: The L2 technical pattern.

evidence: The list of specific AST data points that collectively justify the decision.

If no identifiers have sufficient evidence for exclusion, the "exclusions" array should be empty [].

Example Output 1 (Sufficient Evidence Found):
```json
{{
  "reasoning": "Step 1: The 'user' property has the evidence `modifiers: ['@objc', 'dynamic']` and its class `UserContainer` inherits from `NSObject`. Step 2: This combination of evidence is sufficient because it strongly indicates the property is used for KVO, which relies on the string name. Step 3: Therefore, it matches the 'objc_runtime_interaction' pattern and must be excluded.",
  "exclusions": [
    {{
      "identifier": "user",
      "reason_category": "runtime_name_based_resolution",
      "matched_pattern": "objc_runtime_interaction",
      "evidence": ["is_objc_exposed: true", "inherits: contains 'NSObject'"]
    }}
  ]
}}
```
Example Output 2 (Insufficient Evidence Found):
```json
{{
  "reasoning": "Step 1: The `DataManager` class inherits from `NSObject`. Step 2: However, there is no other evidence like '@objc' attributes, dynamic modifiers, or selector references. Step 3: The evidence `inherits: 'NSObject'` alone is insufficient for exclusion as there's no indication of runtime name usage. The class and its members are safe to obfuscate.",
  "exclusions": []
}}
```
Your response must be ONLY the JSON object.
"""