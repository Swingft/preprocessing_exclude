import Foundation
import SwiftSyntax
import SwiftParser

// MARK: - Models

struct SymbolInput: Codable {
    // --- Essential Context ---
    var symbol_kind: String
    var access_level: String
    var modifiers: [String]
    var attributes: [String]
    var type_signature: String
    var inherits: [String]
    var conforms: [String]
    var extension_of: String?

    // --- Direct Evidence (High-Value Signals) ---
    var keypath_refs: [String]
    var selector_refs: [String]
    var kvc_kvo_strings: [String]
    var ffi_names: [String]
    var archiving_keys: [String]

    // --- Derived Flags (Low-cost, High-impact Features) ---
    var is_protocol_requirement_impl: Bool
    var is_coredata_nsmanaged: Bool
    var codable_synthesized: Bool
    var is_ffi_entry: Bool
    var is_objc_exposed: Bool
    var is_referenced_by_mirror: Bool
    var is_name_used_in_string_literal: Bool
    var is_used_in_resource_loader: Bool
    var is_used_in_swiftui_binding_modifier: Bool
    var is_accessibility_identifier: Bool
    var is_webkit_message_handler: Bool
    var is_used_as_string_key: Bool
    var is_used_in_url_components: Bool

    // Custom encoding to exclude empty arrays
    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)

        // Always encode essential context
        try container.encode(symbol_kind, forKey: .symbol_kind)
        try container.encode(access_level, forKey: .access_level)
        try container.encode(type_signature, forKey: .type_signature)

        // Conditionally encode arrays and optional strings
        if !modifiers.isEmpty { try container.encode(modifiers, forKey: .modifiers) }
        if !attributes.isEmpty { try container.encode(attributes, forKey: .attributes) }
        if !inherits.isEmpty { try container.encode(inherits, forKey: .inherits) }
        if !conforms.isEmpty { try container.encode(conforms, forKey: .conforms) }
        if let ext = extension_of { try container.encode(ext, forKey: .extension_of) }

        if !keypath_refs.isEmpty { try container.encode(keypath_refs, forKey: .keypath_refs) }
        if !selector_refs.isEmpty { try container.encode(selector_refs, forKey: .selector_refs) }
        if !kvc_kvo_strings.isEmpty { try container.encode(kvc_kvo_strings, forKey: .kvc_kvo_strings) }
        if !ffi_names.isEmpty { try container.encode(ffi_names, forKey: .ffi_names) }
        if !archiving_keys.isEmpty { try container.encode(archiving_keys, forKey: .archiving_keys) }

    // Custom encoding to exclude empty arrays
    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)

        // Always encode essential context
        try container.encode(symbol_kind, forKey: .symbol_kind)
        try container.encode(access_level, forKey: .access_level)
        try container.encode(type_signature, forKey: .type_signature)

        // Conditionally encode arrays and optional strings
        if !modifiers.isEmpty { try container.encode(modifiers, forKey: .modifiers) }
        if !attributes.isEmpty { try container.encode(attributes, forKey: .attributes) }
        if !inherits.isEmpty { try container.encode(inherits, forKey: .inherits) }
        if !conforms.isEmpty { try container.encode(conforms, forKey: .conforms) }
        if let ext = extension_of { try container.encode(ext, forKey: .extension_of) }

        if !keypath_refs.isEmpty { try container.encode(keypath_refs, forKey: .keypath_refs) }
        if !selector_refs.isEmpty { try container.encode(selector_refs, forKey: .selector_refs) }
        if !kvc_kvo_strings.isEmpty { try container.encode(kvc_kvo_strings, forKey: .kvc_kvo_strings) }
        if !ffi_names.isEmpty { try container.encode(ffi_names, forKey: .ffi_names) }
        if !archiving_keys.isEmpty { try container.encode(archiving_keys, forKey: .archiving_keys) }

        // Always encode boolean flags (both true and false are meaningful)
        try container.encode(is_protocol_requirement_impl, forKey: .is_protocol_requirement_impl)
        try container.encode(is_coredata_nsmanaged, forKey: .is_coredata_nsmanaged)
        try container.encode(codable_synthesized, forKey: .codable_synthesized)
        try container.encode(is_ffi_entry, forKey: .is_ffi_entry)
        try container.encode(is_objc_exposed, forKey: .is_objc_exposed)
        try container.encode(is_referenced_by_mirror, forKey: .is_referenced_by_mirror)
        try container.encode(is_name_used_in_string_literal, forKey: .is_name_used_in_string_literal)
        try container.encode(is_used_in_resource_loader, forKey: .is_used_in_resource_loader)
        try container.encode(is_used_in_swiftui_binding_modifier, forKey: .is_used_in_swiftui_binding_modifier)
        try container.encode(is_accessibility_identifier, forKey: .is_accessibility_identifier)
        try container.encode(is_webkit_message_handler, forKey: .is_webkit_message_handler)
        try container.encode(is_used_as_string_key, forKey: .is_used_as_string_key)
        try container.encode(is_used_in_url_components, forKey: .is_used_in_url_components)
    }
    }

    enum CodingKeys: String, CodingKey {
        case symbol_kind, access_level, modifiers, attributes, type_signature, inherits, conforms, extension_of
        case keypath_refs, selector_refs, kvc_kvo_strings, ffi_names, archiving_keys
        case is_protocol_requirement_impl, is_coredata_nsmanaged, codable_synthesized, is_ffi_entry, is_objc_exposed
        case is_referenced_by_mirror, is_name_used_in_string_literal, is_used_in_resource_loader
        case is_used_in_swiftui_binding_modifier, is_accessibility_identifier, is_webkit_message_handler
        case is_used_as_string_key, is_used_in_url_components
    }
}

struct Decision: Codable {
    var exclude: Bool
    var reason: String
    var confidence: Double
}

struct SymbolRecord: Codable {
    var symbol_name: String
    var input: SymbolInput
    var decision: Decision?

    init(symbol_name: String, input: SymbolInput, decision: Decision? = nil) {
        self.symbol_name = symbol_name
        self.input = input
        self.decision = decision
    }
}

struct Decisions: Codable {
    var classes: [SymbolRecord] = []
    var structs: [SymbolRecord] = []
    var enums: [SymbolRecord] = []
    var protocols: [SymbolRecord] = []
    var extensions: [SymbolRecord] = []
    var methods: [SymbolRecord] = []
    var properties: [SymbolRecord] = []
    var variables: [SymbolRecord] = []
    var enumCases: [SymbolRecord] = []
    var initializers: [SymbolRecord] = []
    var deinitializers: [SymbolRecord] = []
    var subscripts: [SymbolRecord] = []

    // Custom encoding to exclude empty arrays
    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)

        if !classes.isEmpty { try container.encode(classes, forKey: .classes) }
        if !structs.isEmpty { try container.encode(structs, forKey: .structs) }
        if !enums.isEmpty { try container.encode(enums, forKey: .enums) }
        if !protocols.isEmpty { try container.encode(protocols, forKey: .protocols) }
        if !extensions.isEmpty { try container.encode(extensions, forKey: .extensions) }
        if !methods.isEmpty { try container.encode(methods, forKey: .methods) }
        if !properties.isEmpty { try container.encode(properties, forKey: .properties) }
        if !variables.isEmpty { try container.encode(variables, forKey: .variables) }
        if !enumCases.isEmpty { try container.encode(enumCases, forKey: .enumCases) }
        if !initializers.isEmpty { try container.encode(initializers, forKey: .initializers) }
        if !deinitializers.isEmpty { try container.encode(deinitializers, forKey: .deinitializers) }
        if !subscripts.isEmpty { try container.encode(subscripts, forKey: .subscripts) }
    }

    enum CodingKeys: String, CodingKey {
        case classes, structs, enums, protocols, extensions, methods, properties, variables, enumCases, initializers, deinitializers, subscripts
    }
}

struct Meta: Codable {
    var tool: String
    var model: String
    var prompt_context: String

    init(tool: String, model: String, prompt_context: String) {
        self.tool = tool
        self.model = model
        self.prompt_context = prompt_context
    }
}

struct OutputJSON: Codable {
    var meta: Meta
    var decisions: Decisions

    init(meta: Meta, decisions: Decisions) {
        self.meta = meta
        self.decisions = decisions
    }
}

// MARK: - Utilities

func accessLevel(from modifiers: DeclModifierListSyntax?) -> String {
    guard let mods = modifiers else { return "internal" }
    for m in mods {
        let name = m.name.text.lowercased()
        if ["public", "open", "internal", "fileprivate", "private"].contains(name) {
            return name
        }
    }
    return "internal"
}

func collectModifiers(_ modifiers: DeclModifierListSyntax?) -> [String] {
    guard let mods = modifiers else { return [] }
    return mods.map { $0.name.text }
}

func collectAttributes(_ attrs: AttributeListSyntax?) -> [String] {
    guard let attrs = attrs else { return [] }
    return attrs.compactMap { attr in
        if let a = attr.as(AttributeSyntax.self) {
            return "@\(a.attributeName.trimmedDescription)"
        }
        return nil
    }
}

func inheritsFrom(_ clause: InheritanceClauseSyntax?) -> [String] {
    guard let clause = clause else { return [] }
    return clause.inheritedTypes.map { $0.type.trimmedDescription }
}

func funcTypeSignature(_ decl: FunctionDeclSyntax) -> String {
    decl.signature.trimmedDescription
}

func varTypeSignature(_ decl: VariableDeclSyntax) -> String {
    if let binding = decl.bindings.first, let typeAnno = binding.typeAnnotation {
        return typeAnno.type.trimmedDescription
    }
    return ""
}

func propertyNames(_ decl: VariableDeclSyntax) -> [String] {
    decl.bindings.compactMap {
        $0.pattern.as(IdentifierPatternSyntax.self)?.identifier.text
    }
}

func functionName(_ decl: FunctionDeclSyntax) -> String { decl.name.text }

func initializerSignature(_ decl: InitializerDeclSyntax) -> String {
    decl.signature.trimmedDescription
}

func deinitializerSignature(_ decl: DeinitializerDeclSyntax) -> String { "deinit" }

func subscriptSignature(_ decl: SubscriptDeclSyntax) -> String {
    (decl.genericParameterClause?.trimmedDescription ?? "") + decl.parameterClause.trimmedDescription + decl.returnClause.trimmedDescription
}


// MARK: - Project-wide Context & Pre-scanner

final class ProjectContext {
    var mirrorRefTypes = Set<String>()
    var stringConversionRefs = Set<String>()
    var resourceLoaderKeys = Set<String>()
    var swiftuiBindingModifierRefs = Set<String>()
    var accessibilityIdentifiers = Set<String>()
    var webkitMessageHandlers = Set<String>()
    var genericStringKeys = Set<String>()
    var urlComponentKeys = Set<String>()
    var archivingKeys = Set<String>()
}

final class PreScannerVisitor: SyntaxVisitor {
    let context: ProjectContext

    init(context: ProjectContext) {
        self.context = context
        super.init(viewMode: .sourceAccurate)
    }

    private func extractStringValue(from node: StringLiteralExprSyntax) -> String? {
        if let segment = node.segments.first, case .stringSegment(let stringSegment) = segment {
            return stringSegment.content.text
        }
        return nil
    }

    override func visit(_ node: FunctionCallExprSyntax) -> SyntaxVisitorContinueKind {
        if let memberAccess = node.calledExpression.as(MemberAccessExprSyntax.self) {
            let funcName = memberAccess.declName.baseName.text
            if ["onChange", "task"].contains(funcName) {
                if let arg = node.arguments.first?.expression.as(DeclReferenceExprSyntax.self) {
                    context.swiftuiBindingModifierRefs.insert(arg.baseName.text)
                }
            } else if funcName == "add" {
                 if let nameArg = node.arguments.first(where: { $0.label?.text == "name" }),
                    let nameValue = nameArg.expression.as(StringLiteralExprSyntax.self).flatMap(extractStringValue) {
                     context.webkitMessageHandlers.insert(nameValue)
                 }
            } else if funcName == "set" {
                if let forKeyArg = node.arguments.first(where: { $0.label?.text == "forKey" }),
                   let key = forKeyArg.expression.as(StringLiteralExprSyntax.self).flatMap(extractStringValue) {
                    context.genericStringKeys.insert(key)
                }
            } else if funcName == "encode" {
                if let forKeyArg = node.arguments.first(where: { $0.label?.text == "forKey" }),
                   let key = forKeyArg.expression.as(StringLiteralExprSyntax.self).flatMap(extractStringValue) {
                    context.archivingKeys.insert(key)
                }
            }
        }

        guard let calledExpr = node.calledExpression.as(DeclReferenceExprSyntax.self) else {
            return .visitChildren
        }

        let funcName = calledExpr.baseName.text

        if let firstArg = node.arguments.first,
           let firstArgLabel = firstArg.label?.text,
           let firstArgExpr = firstArg.expression.as(StringLiteralExprSyntax.self).flatMap(extractStringValue) {
            switch funcName {
            case "UIImage", "UIColor", "NSImage", "NSColor":
                if firstArgLabel == "named" { context.resourceLoaderKeys.insert(firstArgExpr) }
            case "UIFont":
                if firstArgLabel == "name" { context.resourceLoaderKeys.insert(firstArgExpr) }
            case "NSLocalizedString":
                context.resourceLoaderKeys.insert(firstArgExpr)
            case _ where funcName.hasSuffix("logEvent"):
                context.genericStringKeys.insert(firstArgExpr)
            default:
                break
            }
        }

        switch funcName {
        case "Mirror":
            if let arg = node.arguments.first?.expression.as(FunctionCallExprSyntax.self),
               let typeRef = arg.calledExpression.as(DeclReferenceExprSyntax.self) {
                context.mirrorRefTypes.insert(typeRef.baseName.text)
            }
        case "NSClassFromString":
            if let key = node.arguments.first?.expression.as(StringLiteralExprSyntax.self).flatMap(extractStringValue) {
                let typeName = key.split(separator: ".").last.map(String.init) ?? key
                context.stringConversionRefs.insert(typeName)
            }
        case "String":
             if let argLabel = node.arguments.first?.label?.text, argLabel == "describing",
                let memberAccess = node.arguments.first?.expression.as(MemberAccessExprSyntax.self),
                memberAccess.declName.baseName.text == "self",
                let typeName = memberAccess.base?.as(DeclReferenceExprSyntax.self)?.baseName.text {
                context.stringConversionRefs.insert(typeName)
            }
        default:
            break
        }
        return .visitChildren
    }

    // Fixed: Use SequenceExprSyntax to detect assignment patterns
    override func visit(_ node: SequenceExprSyntax) -> SyntaxVisitorContinueKind {
        // Assignment patterns in Swift are represented as SequenceExpr with AssignmentExpr
        let elements = Array(node.elements)
        if elements.count >= 3 {
            // Pattern: leftOperand operator rightOperand
            let leftExpr = elements[0]
            let operatorExpr = elements[1]
            let rightExpr = elements[2]

            if let _ = operatorExpr.as(AssignmentExprSyntax.self),
               let memberAccess = leftExpr.as(MemberAccessExprSyntax.self),
               memberAccess.declName.baseName.text == "accessibilityIdentifier",
               let stringLiteral = rightExpr.as(StringLiteralExprSyntax.self),
               let value = extractStringValue(from: stringLiteral) {
                context.accessibilityIdentifiers.insert(value)
            }
        }
        return .visitChildren
    }
}

private func scanBodySignals(_ syntax: Syntax) -> (keypaths:[String], selectors:[String], kvc:[String]) {
    class BodyVisitor: SyntaxVisitor {
        var keypaths: [String] = []
        var kvc: [String] = []

        override func visit(_ node: FunctionCallExprSyntax) -> SyntaxVisitorContinueKind {
            let nameText = (node.calledExpression.trimmedDescription).lowercased()
            let kvcLikely = nameText.contains("valueforkey") || nameText.contains("setvalue") ||
                            nameText.contains("addobserver") || nameText.contains("removeobserver")
            if kvcLikely {
                for arg in node.arguments {
                    if let segment = arg.expression.as(StringLiteralExprSyntax.self)?.segments.first, case .stringSegment(let stringSegment) = segment {
                        kvc.append(stringSegment.content.text)
                    }
                }
            }
            return .visitChildren
        }

        override func visit(_ node: KeyPathExprSyntax) -> SyntaxVisitorContinueKind {
            keypaths.append(node.trimmedDescription)
            return .visitChildren
        }
    }

    let v = BodyVisitor(viewMode: .sourceAccurate)
    v.walk(syntax)

    var selectorTexts: [String] = []
    let text = syntax.trimmedDescription
    if let regex = try? NSRegularExpression(pattern: #"#selector\(([^)]+)\)"#) {
        let ns = text as NSString
        let matches = regex.matches(in: text, range: NSRange(location: 0, length: ns.length))
        for m in matches {
            if m.numberOfRanges > 1 {
                let selectorName = ns.substring(with: m.range(at: 1))
                selectorTexts.append(selectorName)
            }
        }
    }

    func uniq(_ a:[String]) -> [String] { Array(Set(a)).sorted() }
    return (uniq(v.keypaths), uniq(selectorTexts), uniq(v.kvc))
}

// MARK: - Main Visitor
final class SymbolCollector: SyntaxVisitor {
    private var typeStack: [String] = []
    var decisions = Decisions()
    private let projectContext: ProjectContext

    init(projectContext: ProjectContext) {
        self.projectContext = projectContext
        super.init(viewMode: .sourceAccurate)
    }

    private func baseAttributesFlags(_ attrs: [String], modifiers: [String]) -> (isObjcExposed: Bool, isCoreData: Bool, isFfi: Bool, ffiNames: [String]) {
        let set = Set(attrs.map { $0.lowercased() })
        let dyn = modifiers.map { $0.lowercased() }.contains("dynamic")
        let isObjc = set.contains("@objc") || set.contains("@objcmembers") || dyn
        let isCoreData = set.contains("@nsmanaged")
        let ffi = set.contains("@_cdecl") || set.contains("@_silgen_name")

        var ffiNames: [String] = []
        for a in attrs {
            if a.lowercased().starts(with: "@_cdecl("), let open = a.firstIndex(of: "("), let close = a.lastIndex(of: ")") {
                let inner = String(a[a.index(after: open)..<close]).replacingOccurrences(of: "\"", with: "")
                ffiNames.append(inner)
            }
        }
        return (isObjc, isCoreData, ffi, ffiNames)
    }

    private func checkIsProtocolRequirement(symbol_name: String, conforms: [String]) -> Bool {
        return false
    }

    private func getArchivingKeys(node: Syntax) -> [String] {
        let visitor = ArchivingKeyVisitor(viewMode: .sourceAccurate)
        visitor.walk(node)
        return Array(visitor.keys)
    }

    private func currentExtensionType() -> String? {
        if let firstType = typeStack.first, firstType == "extension" {
            return typeStack.count > 1 ? typeStack[1] : nil
        }
        return nil
    }

    // Use specific visit methods for each node type
    override func visit(_ node: ClassDeclSyntax) -> SyntaxVisitorContinueKind {
        typeStack.append(node.name.text)

        let name = node.name.text
        let attrs = collectAttributes(node.attributes)
        let mods = collectModifiers(node.modifiers)
        let access = accessLevel(from: node.modifiers)
        let inherits = inheritsFrom(node.inheritanceClause)

        let (keyPaths, selectors, kvc) = scanBodySignals(Syntax(node))
        let (isObjc, isCoreData, isFfi, ffiNames) = baseAttributesFlags(attrs, modifiers: mods)

        let input = SymbolInput(
            symbol_kind: "class", access_level: access, modifiers: mods, attributes: attrs,
            type_signature: "", inherits: inherits, conforms: inherits, extension_of: currentExtensionType(),
            keypath_refs: keyPaths, selector_refs: selectors, kvc_kvo_strings: kvc, ffi_names: ffiNames,
            archiving_keys: getArchivingKeys(node: Syntax(node)),
            is_protocol_requirement_impl: false, is_coredata_nsmanaged: isCoreData, codable_synthesized: false,
            is_ffi_entry: isFfi, is_objc_exposed: isObjc, is_referenced_by_mirror: projectContext.mirrorRefTypes.contains(name),
            is_name_used_in_string_literal: projectContext.stringConversionRefs.contains(name),
            is_used_in_resource_loader: false, is_used_in_swiftui_binding_modifier: false,
            is_accessibility_identifier: false, is_webkit_message_handler: false,
            is_used_as_string_key: false, is_used_in_url_components: false
        )

        decisions.classes.append(SymbolRecord(symbol_name: name, input: input))
        return .visitChildren
    }

    // Handle class declaration exit
    override func visitPost(_ node: ClassDeclSyntax) {
        if !typeStack.isEmpty {
            typeStack.removeLast()
        }
    }

    override func visit(_ node: StructDeclSyntax) -> SyntaxVisitorContinueKind {
        typeStack.append(node.name.text)

        let name = node.name.text
        let attrs = collectAttributes(node.attributes)
        let mods = collectModifiers(node.modifiers)
        let access = accessLevel(from: node.modifiers)
        let inherits = inheritsFrom(node.inheritanceClause)

        let (keyPaths, selectors, kvc) = scanBodySignals(Syntax(node))
        let (isObjc, isCoreData, isFfi, ffiNames) = baseAttributesFlags(attrs, modifiers: mods)

        let input = SymbolInput(
            symbol_kind: "struct", access_level: access, modifiers: mods, attributes: attrs,
            type_signature: "", inherits: inherits, conforms: [], extension_of: currentExtensionType(),
            keypath_refs: keyPaths, selector_refs: selectors, kvc_kvo_strings: kvc, ffi_names: ffiNames,
            archiving_keys: getArchivingKeys(node: Syntax(node)),
            is_protocol_requirement_impl: false, is_coredata_nsmanaged: isCoreData, codable_synthesized: false,
            is_ffi_entry: isFfi, is_objc_exposed: isObjc, is_referenced_by_mirror: projectContext.mirrorRefTypes.contains(name),
            is_name_used_in_string_literal: projectContext.stringConversionRefs.contains(name),
            is_used_in_resource_loader: false, is_used_in_swiftui_binding_modifier: false,
            is_accessibility_identifier: false, is_webkit_message_handler: false,
            is_used_as_string_key: false, is_used_in_url_components: false
        )

        decisions.structs.append(SymbolRecord(symbol_name: name, input: input))
        return .visitChildren
    }

    override func visitPost(_ node: StructDeclSyntax) {
        if !typeStack.isEmpty {
            typeStack.removeLast()
        }
    }

    override func visit(_ node: EnumDeclSyntax) -> SyntaxVisitorContinueKind {
        typeStack.append(node.name.text)

        let name = node.name.text
        let attrs = collectAttributes(node.attributes)
        let mods = collectModifiers(node.modifiers)
        let access = accessLevel(from: node.modifiers)
        let inherits = inheritsFrom(node.inheritanceClause)

        let (keyPaths, selectors, kvc) = scanBodySignals(Syntax(node))
        let (isObjc, isCoreData, isFfi, ffiNames) = baseAttributesFlags(attrs, modifiers: mods)

        let input = SymbolInput(
            symbol_kind: "enum", access_level: access, modifiers: mods, attributes: attrs,
            type_signature: "", inherits: inherits, conforms: [], extension_of: currentExtensionType(),
            keypath_refs: keyPaths, selector_refs: selectors, kvc_kvo_strings: kvc, ffi_names: ffiNames,
            archiving_keys: getArchivingKeys(node: Syntax(node)),
            is_protocol_requirement_impl: false, is_coredata_nsmanaged: isCoreData, codable_synthesized: false,
            is_ffi_entry: isFfi, is_objc_exposed: isObjc, is_referenced_by_mirror: projectContext.mirrorRefTypes.contains(name),
            is_name_used_in_string_literal: projectContext.stringConversionRefs.contains(name),
            is_used_in_resource_loader: false, is_used_in_swiftui_binding_modifier: false,
            is_accessibility_identifier: false, is_webkit_message_handler: false,
            is_used_as_string_key: false, is_used_in_url_components: false
        )

        decisions.enums.append(SymbolRecord(symbol_name: name, input: input))
        return .visitChildren
    }

    override func visitPost(_ node: EnumDeclSyntax) {
        if !typeStack.isEmpty {
            typeStack.removeLast()
        }
    }

    override func visit(_ node: ProtocolDeclSyntax) -> SyntaxVisitorContinueKind {
        typeStack.append(node.name.text)

        let name = node.name.text
        let attrs = collectAttributes(node.attributes)
        let mods = collectModifiers(node.modifiers)
        let access = accessLevel(from: node.modifiers)
        let inherits = inheritsFrom(node.inheritanceClause)

        let (keyPaths, selectors, kvc) = scanBodySignals(Syntax(node))
        let (isObjc, isCoreData, isFfi, ffiNames) = baseAttributesFlags(attrs, modifiers: mods)

        let input = SymbolInput(
            symbol_kind: "protocol", access_level: access, modifiers: mods, attributes: attrs,
            type_signature: "", inherits: inherits, conforms: [], extension_of: currentExtensionType(),
            keypath_refs: keyPaths, selector_refs: selectors, kvc_kvo_strings: kvc, ffi_names: ffiNames,
            archiving_keys: getArchivingKeys(node: Syntax(node)),
            is_protocol_requirement_impl: false, is_coredata_nsmanaged: isCoreData, codable_synthesized: false,
            is_ffi_entry: isFfi, is_objc_exposed: isObjc, is_referenced_by_mirror: projectContext.mirrorRefTypes.contains(name),
            is_name_used_in_string_literal: projectContext.stringConversionRefs.contains(name),
            is_used_in_resource_loader: false, is_used_in_swiftui_binding_modifier: false,
            is_accessibility_identifier: false, is_webkit_message_handler: false,
            is_used_as_string_key: false, is_used_in_url_components: false
        )

        decisions.protocols.append(SymbolRecord(symbol_name: name, input: input))
        return .visitChildren
    }

    override func visitPost(_ node: ProtocolDeclSyntax) {
        if !typeStack.isEmpty {
            typeStack.removeLast()
        }
    }

    override func visit(_ node: ExtensionDeclSyntax) -> SyntaxVisitorContinueKind {
        typeStack.append("extension")
        typeStack.append(node.extendedType.trimmedDescription)

        let typeName = node.extendedType.trimmedDescription
        let attrs = collectAttributes(node.attributes)
        let mods = collectModifiers(node.modifiers)
        let access = accessLevel(from: node.modifiers)

        let (keyPaths, selectors, kvc) = scanBodySignals(Syntax(node))
        let (isObjc, isCoreData, isFfi, ffiNames) = baseAttributesFlags(attrs, modifiers: mods)

        let input = SymbolInput(
            symbol_kind: "extension", access_level: access, modifiers: mods, attributes: attrs,
            type_signature: typeName, inherits: [], conforms: [], extension_of: nil,
            keypath_refs: keyPaths, selector_refs: selectors, kvc_kvo_strings: kvc, ffi_names: ffiNames,
            archiving_keys: getArchivingKeys(node: Syntax(node)),
            is_protocol_requirement_impl: false, is_coredata_nsmanaged: isCoreData, codable_synthesized: false,
            is_ffi_entry: isFfi, is_objc_exposed: isObjc, is_referenced_by_mirror: false,
            is_name_used_in_string_literal: false,
            is_used_in_resource_loader: false, is_used_in_swiftui_binding_modifier: false,
            is_accessibility_identifier: false, is_webkit_message_handler: false,
            is_used_as_string_key: false, is_used_in_url_components: false
        )

        decisions.extensions.append(SymbolRecord(symbol_name: typeName, input: input))
        return .visitChildren
    }

    override func visitPost(_ node: ExtensionDeclSyntax) {
        if typeStack.count >= 2 {
            typeStack.removeLast()
            typeStack.removeLast()
        }
    }

    override func visit(_ node: FunctionDeclSyntax) -> SyntaxVisitorContinueKind {
        let name = functionName(node)
        let modifiers = collectModifiers(node.modifiers)
        let attrs = collectAttributes(node.attributes)
        let (isObjc, _, isFfi, ffiNames) = baseAttributesFlags(attrs, modifiers: modifiers)
        let bodySyntax: Syntax = node.body.map { Syntax($0) } ?? Syntax(node)
        let (kps, sels, kvc) = scanBodySignals(bodySyntax)

        let input = SymbolInput(
            symbol_kind: "method", access_level: accessLevel(from: node.modifiers), modifiers: modifiers, attributes: attrs,
            type_signature: funcTypeSignature(node), inherits: [], conforms: [], extension_of: currentExtensionType(),
            keypath_refs: kps, selector_refs: sels, kvc_kvo_strings: kvc, ffi_names: ffiNames, archiving_keys: [],
            is_protocol_requirement_impl: checkIsProtocolRequirement(symbol_name: name, conforms: []),
            is_coredata_nsmanaged: false, codable_synthesized: false, is_ffi_entry: isFfi, is_objc_exposed: isObjc,
            is_referenced_by_mirror: false, is_name_used_in_string_literal: false,
            is_used_in_resource_loader: projectContext.resourceLoaderKeys.contains(name),
            is_used_in_swiftui_binding_modifier: false, is_accessibility_identifier: false,
            is_webkit_message_handler: projectContext.webkitMessageHandlers.contains(name),
            is_used_as_string_key: projectContext.genericStringKeys.contains(name),
            is_used_in_url_components: projectContext.urlComponentKeys.contains(name)
        )
        decisions.methods.append(SymbolRecord(symbol_name: name, input: input))
        return .skipChildren
    }

    override func visit(_ node: VariableDeclSyntax) -> SyntaxVisitorContinueKind {
        let modifiers = collectModifiers(node.modifiers)
        let attrs = collectAttributes(node.attributes)
        let (isObjc, isCoreData, isFfi, ffiNames) = baseAttributesFlags(attrs, modifiers: modifiers)

        let (kps, sels, kvc) = node.bindings.first?.accessorBlock.map { scanBodySignals(Syntax($0)) } ?? ([], [], [])
        let isGlobal = typeStack.isEmpty
        let kind = isGlobal ? "variable" : "property"

        for name in propertyNames(node) {
            let input = SymbolInput(
                symbol_kind: kind, access_level: accessLevel(from: node.modifiers), modifiers: modifiers, attributes: attrs,
                type_signature: varTypeSignature(node), inherits: [], conforms: [], extension_of: currentExtensionType(),
                keypath_refs: kps, selector_refs: sels, kvc_kvo_strings: kvc, ffi_names: ffiNames,
                archiving_keys: projectContext.archivingKeys.contains(name) ? [name] : [],
                is_protocol_requirement_impl: checkIsProtocolRequirement(symbol_name: name, conforms: []),
                is_coredata_nsmanaged: isCoreData, codable_synthesized: false, is_ffi_entry: isFfi, is_objc_exposed: isObjc,
                is_referenced_by_mirror: false, is_name_used_in_string_literal: false,
                is_used_in_resource_loader: projectContext.resourceLoaderKeys.contains(name),
                is_used_in_swiftui_binding_modifier: projectContext.swiftuiBindingModifierRefs.contains(name),
                is_accessibility_identifier: projectContext.accessibilityIdentifiers.contains(name),
                is_webkit_message_handler: false,
                is_used_as_string_key: projectContext.genericStringKeys.contains(name),
                is_used_in_url_components: projectContext.urlComponentKeys.contains(name)
            )
            if isGlobal {
                decisions.variables.append(SymbolRecord(symbol_name: name, input: input))
            } else {
                decisions.properties.append(SymbolRecord(symbol_name: name, input: input))
            }
        }
        return .skipChildren
    }

    override func visit(_ node: InitializerDeclSyntax) -> SyntaxVisitorContinueKind {
        let modifiers = collectModifiers(node.modifiers)
        let attrs = collectAttributes(node.attributes)
        let (isObjc, _, isFfi, ffiNames) = baseAttributesFlags(attrs, modifiers: modifiers)
        let bodySyntax: Syntax = node.body.map { Syntax($0) } ?? Syntax(node)
        let (kps, sels, kvc) = scanBodySignals(bodySyntax)

        let signature = initializerSignature(node)
        let input = SymbolInput(
            symbol_kind: "initializer", access_level: accessLevel(from: node.modifiers), modifiers: modifiers, attributes: attrs,
            type_signature: signature, inherits: [], conforms: [], extension_of: currentExtensionType(),
            keypath_refs: kps, selector_refs: sels, kvc_kvo_strings: kvc, ffi_names: ffiNames, archiving_keys: [],
            is_protocol_requirement_impl: false, is_coredata_nsmanaged: false, codable_synthesized: false,
            is_ffi_entry: isFfi, is_objc_exposed: isObjc, is_referenced_by_mirror: false,
            is_name_used_in_string_literal: false, is_used_in_resource_loader: false,
            is_used_in_swiftui_binding_modifier: false, is_accessibility_identifier: false,
            is_webkit_message_handler: false, is_used_as_string_key: false, is_used_in_url_components: false
        )
        decisions.initializers.append(SymbolRecord(symbol_name: "init\(signature)", input: input))
        return .skipChildren
    }

    override func visit(_ node: DeinitializerDeclSyntax) -> SyntaxVisitorContinueKind {
        let modifiers = collectModifiers(node.modifiers)
        let attrs = collectAttributes(node.attributes)
        let bodySyntax: Syntax = node.body.map { Syntax($0) } ?? Syntax(node)
        let (kps, sels, kvc) = scanBodySignals(bodySyntax)

        let input = SymbolInput(
            symbol_kind: "deinitializer", access_level: accessLevel(from: node.modifiers), modifiers: modifiers, attributes: attrs,
            type_signature: deinitializerSignature(node), inherits: [], conforms: [], extension_of: currentExtensionType(),
            keypath_refs: kps, selector_refs: sels, kvc_kvo_strings: kvc, ffi_names: [], archiving_keys: [],
            is_protocol_requirement_impl: false, is_coredata_nsmanaged: false, codable_synthesized: false,
            is_ffi_entry: false, is_objc_exposed: false, is_referenced_by_mirror: false,
            is_name_used_in_string_literal: false, is_used_in_resource_loader: false,
            is_used_in_swiftui_binding_modifier: false, is_accessibility_identifier: false,
            is_webkit_message_handler: false, is_used_as_string_key: false, is_used_in_url_components: false
        )
        decisions.deinitializers.append(SymbolRecord(symbol_name: "deinit", input: input))
        return .skipChildren
    }

    override func visit(_ node: SubscriptDeclSyntax) -> SyntaxVisitorContinueKind {
        let modifiers = collectModifiers(node.modifiers)
        let attrs = collectAttributes(node.attributes)
        let (isObjc, _, _, ffiNames) = baseAttributesFlags(attrs, modifiers: modifiers)
        let bodySyntax: Syntax = node.accessorBlock.map { Syntax($0) } ?? Syntax(node)
        let (kps, sels, kvc) = scanBodySignals(bodySyntax)

        let signature = subscriptSignature(node)
        let input = SymbolInput(
            symbol_kind: "subscript", access_level: accessLevel(from: node.modifiers), modifiers: modifiers, attributes: attrs,
            type_signature: signature, inherits: [], conforms: [], extension_of: currentExtensionType(),
            keypath_refs: kps, selector_refs: sels, kvc_kvo_strings: kvc, ffi_names: ffiNames, archiving_keys: [],
            is_protocol_requirement_impl: false, is_coredata_nsmanaged: false, codable_synthesized: false,
            is_ffi_entry: false, is_objc_exposed: isObjc, is_referenced_by_mirror: false,
            is_name_used_in_string_literal: false, is_used_in_resource_loader: false,
            is_used_in_swiftui_binding_modifier: false, is_accessibility_identifier: false,
            is_webkit_message_handler: false, is_used_as_string_key: false, is_used_in_url_components: false
        )
        decisions.subscripts.append(SymbolRecord(symbol_name: "subscript\(signature)", input: input))
        return .skipChildren
    }

    override func visit(_ node: EnumCaseDeclSyntax) -> SyntaxVisitorContinueKind {
        for elem in node.elements {
            let name = elem.name.text
            var rawValue = name
            if let segment = elem.rawValue?.value.as(StringLiteralExprSyntax.self)?.segments.first, case .stringSegment(let stringSegment) = segment {
                rawValue = stringSegment.content.text
            }

            let input = SymbolInput(
                symbol_kind: "enumCase", access_level: "internal", modifiers: [], attributes: collectAttributes(node.attributes),
                type_signature: elem.parameterClause?.trimmedDescription ?? "", inherits: [], conforms: [], extension_of: nil,
                keypath_refs: [], selector_refs: [], kvc_kvo_strings: [], ffi_names: [], archiving_keys: [],
                is_protocol_requirement_impl: false, is_coredata_nsmanaged: false, codable_synthesized: false,
                is_ffi_entry: false, is_objc_exposed: false, is_referenced_by_mirror: false,
                is_name_used_in_string_literal: projectContext.stringConversionRefs.contains(name),
                is_used_in_resource_loader: projectContext.resourceLoaderKeys.contains(rawValue),
                is_used_in_swiftui_binding_modifier: false, is_accessibility_identifier: false,
                is_webkit_message_handler: false,
                is_used_as_string_key: projectContext.genericStringKeys.contains(rawValue),
                is_used_in_url_components: false
            )
            decisions.enumCases.append(SymbolRecord(symbol_name: name, input: input))
        }
        return .skipChildren
    }
}

// A specific visitor to find archiving keys inside an NSCoding implementation
class ArchivingKeyVisitor: SyntaxVisitor {
    var keys = Set<String>()
    override func visit(_ node: FunctionCallExprSyntax) -> SyntaxVisitorContinueKind {
        if let calledExpr = node.calledExpression.as(MemberAccessExprSyntax.self),
           calledExpr.declName.baseName.text == "encode" {
            if let forKeyArg = node.arguments.first(where: { $0.label?.text == "forKey" }),
               let segment = forKeyArg.expression.as(StringLiteralExprSyntax.self)?.segments.first, case .stringSegment(let stringSegment) = segment {
                keys.insert(stringSegment.content.text)
            }
        }
        return .visitChildren
    }
}

// MARK: - Runner

func swiftFiles(under path: String) -> [String] {
    var results: [String] = []
    let fm = FileManager.default
    var isDir: ObjCBool = false
    guard fm.fileExists(atPath: path, isDirectory: &isDir) else { return [] }
    if !isDir.boolValue {
        if path.hasSuffix(".swift") { return [path] } else { return [] }
    }
    let enumerator = fm.enumerator(atPath: path)
    while let item = enumerator?.nextObject() as? String {
        if item.hasSuffix(".swift") {
            results.append((path as NSString).appendingPathComponent(item))
        }
    }
    return results
}

func buildOutputJSON(for paths: [String]) -> OutputJSON {
    let projectContext = ProjectContext()
    print("Pass 1: Pre-scanning files to build context...")

    for (index, p) in paths.enumerated() {
        if (index > 0 && index % 100 == 0) || index == paths.count - 1 {
            print("  Scanning file \(index + 1)/\(paths.count)...")
        }
        guard let source = try? String(contentsOfFile: p, encoding: .utf8) else { continue }

        let tree = Parser.parse(source: source)
        let preScanner = PreScannerVisitor(context: projectContext)
        preScanner.walk(tree)
    }

    print("Pass 2: Collecting symbols with context...")
    var merged = Decisions()

    for (index, p) in paths.enumerated() {
        if (index > 0 && index % 100 == 0) || index == paths.count - 1 {
            print("  Collecting from file \(index + 1)/\(paths.count)...")
        }
        guard let source = try? String(contentsOfFile: p, encoding: .utf8) else { continue }

        let tree = Parser.parse(source: source)
        let collector = SymbolCollector(projectContext: projectContext)
        collector.walk(tree)

        merged.classes.append(contentsOf: collector.decisions.classes)
        merged.structs.append(contentsOf: collector.decisions.structs)
        merged.enums.append(contentsOf: collector.decisions.enums)
        merged.protocols.append(contentsOf: collector.decisions.protocols)
        merged.extensions.append(contentsOf: collector.decisions.extensions)
        merged.methods.append(contentsOf: collector.decisions.methods)
        merged.properties.append(contentsOf: collector.decisions.properties)
        merged.variables.append(contentsOf: collector.decisions.variables)
        merged.enumCases.append(contentsOf: collector.decisions.enumCases)
        merged.initializers.append(contentsOf: collector.decisions.initializers)
        merged.deinitializers.append(contentsOf: collector.decisions.deinitializers)
        merged.subscripts.append(contentsOf: collector.decisions.subscripts)
    }

    let meta = Meta(
        tool: "obfuscation_exclude_assistant",
        model: "gemini-pro",
        prompt_context: "This JSON contains symbol information extracted from Swift source code for obfuscation exclusion analysis."
    )

    // Fixed: Only use the two parameters that OutputJSON accepts
    return OutputJSON(
        meta: meta,
        decisions: merged
    )
}

// MARK: - Main

if CommandLine.arguments.count < 2 {
    fputs("Usage: \(CommandLine.arguments[0]) <path-to-swift-files>\n", stderr)
    exit(1)
}

let inputPaths = Array(CommandLine.arguments.dropFirst()).flatMap { swiftFiles(under: $0) }
if inputPaths.isEmpty {
    print("No Swift files found.")
    exit(0)
}

print("Found \(inputPaths.count) Swift files to analyze.")
let out = buildOutputJSON(for: inputPaths)

let encoder = JSONEncoder()
encoder.outputFormatting = .prettyPrinted
let data = try! encoder.encode(out)
print(String(data: data, encoding: .utf8)!)