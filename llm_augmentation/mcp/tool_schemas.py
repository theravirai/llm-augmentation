"""
Tool Schemas for the 5 Deterministic SootUp Static Analysis Primitives.
Formatted for function calling in LLMs (OpenAI / Anthropic / Gemini / MCP format).
"""

SOOTUP_TOOLS = [
    {
        "name": "sootup_hierarchy",
        "description": "Retrieves superclasses, subclasses (including compiler-generated anonymous inner classes like Gson$1), and implemented interfaces for a given Java class.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_class": {
                    "type": "string",
                    "description": "Fully-qualified Java class name (e.g. 'com.google.gson.TypeAdapter')"
                },
                "target_dir": {
                    "type": "string",
                    "description": "Optional path to target/classes directory"
                }
            },
            "required": ["target_class"]
        }
    },
    {
        "name": "sootup_inspect_method",
        "description": "Disassembles a Java method into Jimple 3-address IR with source line numbers, declaring class, and outer enclosing class.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_class": {
                    "type": "string",
                    "description": "Fully-qualified class name containing the method (e.g. 'com.google.gson.Gson$1')"
                },
                "target_method": {
                    "type": "string",
                    "description": "Method name to disassemble (e.g. 'write')"
                },
                "target_dir": {
                    "type": "string",
                    "description": "Optional path to target/classes directory"
                }
            },
            "required": ["target_class", "target_method"]
        }
    },
    {
        "name": "sootup_find_allocations",
        "description": "Scans Jimple method bodies for JNewExpr to locate object instantiation sites (new TargetClass()). Essential for uncovering factory registration of anonymous inner classes.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_class": {
                    "type": "string",
                    "description": "Fully-qualified class name being instantiated (e.g. 'com.google.gson.Gson$1')"
                },
                "scope_class": {
                    "type": "string",
                    "description": "Optional enclosing class to restrict the bytecode search (e.g. 'com.google.gson.Gson')"
                },
                "target_dir": {
                    "type": "string",
                    "description": "Optional path to target/classes directory"
                }
            },
            "required": ["target_class"]
        }
    },
    {
        "name": "sootup_find_invocations",
        "description": "Scans Jimple method bodies for InvokableStmt to find caller sites of a specific method across classes without needing whole-program call-graph computation.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_class": {
                    "type": "string",
                    "description": "Declaring class of target method (e.g. 'org.apache.druid.java.util.common.JodaUtils')"
                },
                "target_method": {
                    "type": "string",
                    "description": "Method name being called (e.g. 'condenseIntervals')"
                },
                "scope_class": {
                    "type": "string",
                    "description": "Optional class to restrict search"
                },
                "target_dir": {
                    "type": "string",
                    "description": "Optional path to target/classes directory"
                }
            },
            "required": ["target_class", "target_method"]
        }
    },
    {
        "name": "sootup_callgraph",
        "description": "Constructs an interprocedural Call Graph using CHA, RTA, or SPARK starting from an entry point method.",
        "parameters": {
            "type": "object",
            "properties": {
                "algorithm": {
                    "type": "string",
                    "enum": ["cha", "rta", "spark"],
                    "description": "Call graph algorithm to use: 'cha' (fastest), 'rta', or 'spark' (points-to precision)"
                },
                "entry_class": {
                    "type": "string",
                    "description": "Entry point fully-qualified class name"
                },
                "entry_method": {
                    "type": "string",
                    "description": "Entry point method name"
                },
                "return_type": {
                    "type": "string",
                    "description": "Method return type (e.g. 'void' or 'java.lang.String')"
                },
                "param_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of fully-qualified parameter types (e.g. ['java.lang.String'])"
                },
                "target_dir": {
                    "type": "string",
                    "description": "Optional path to target/classes directory"
                }
            },
            "required": ["algorithm", "entry_class", "entry_method", "return_type"]
        }
    }
]
