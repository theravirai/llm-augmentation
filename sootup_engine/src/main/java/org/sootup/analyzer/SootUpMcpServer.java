package org.sootup.analyzer;

import com.google.gson.*;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Model Context Protocol (MCP) Server implementing JSON-RPC 2.0 over standard I/O.
 * Exposes the 5 SootUp bytecode analysis primitives as standard tools to LLM agents.
 */
public class SootUpMcpServer {

    private static final Gson gson = new Gson();
    private static final Map<String, SootUpAnalyzer> analyzerCache = new ConcurrentHashMap<>();
    private static String defaultTargetDir = "";

    public static void main(String[] args) {
        if (args.length > 0) {
            defaultTargetDir = args[0];
            System.err.println("[SootUp-MCP] Default target directory set to: " + defaultTargetDir);
        }

        System.err.println("[SootUp-MCP] Server initialized and listening on STDIN...");

        try (BufferedReader reader = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty()) continue;

                try {
                    JsonObject request = JsonParser.parseString(line).getAsJsonObject();
                    JsonObject response = handleRequest(request);
                    if (response != null) {
                        System.out.println(gson.toJson(response));
                        System.out.flush();
                    }
                } catch (Exception e) {
                    System.err.println("[SootUp-MCP] Error processing message: " + e.getMessage());
                    e.printStackTrace(System.err);
                }
            }
        } catch (Exception e) {
            System.err.println("[SootUp-MCP] Server loop error: " + e.getMessage());
        }
    }

    private static JsonObject handleRequest(JsonObject request) {
        String jsonrpc = request.has("jsonrpc") ? request.get("jsonrpc").getAsString() : "2.0";
        JsonElement idElement = request.get("id");
        String method = request.has("method") ? request.get("method").getAsString() : "";

        // Notifications have no id and need no response
        if (method.equals("notifications/initialized") || method.equals("initialized")) {
            return null;
        }

        JsonObject response = new JsonObject();
        response.addProperty("jsonrpc", jsonrpc);
        if (idElement != null) {
            response.add("id", idElement);
        }

        switch (method) {
            case "initialize":
                response.add("result", handleInitialize(request.getAsJsonObject("params")));
                return response;

            case "tools/list":
                response.add("result", handleToolsList());
                return response;

            case "tools/call":
                JsonObject params = request.has("params") ? request.getAsJsonObject("params") : new JsonObject();
                response.add("result", handleToolCall(params));
                return response;

            case "ping":
                response.add("result", new JsonObject());
                return response;

            default:
                JsonObject error = new JsonObject();
                error.addProperty("code", -32601);
                error.addProperty("message", "Method not found: " + method);
                response.add("error", error);
                return response;
        }
    }

    private static JsonObject handleInitialize(JsonObject params) {
        if (params != null && params.has("initializationOptions")) {
            JsonObject initOptions = params.getAsJsonObject("initializationOptions");
            if (initOptions.has("target_dir")) {
                defaultTargetDir = initOptions.get("target_dir").getAsString();
                System.err.println("[SootUp-MCP] Target directory set via init: " + defaultTargetDir);
            }
        }

        JsonObject result = new JsonObject();
        result.addProperty("protocolVersion", "2024-11-05");

        JsonObject capabilities = new JsonObject();
        capabilities.add("tools", new JsonObject());
        result.add("capabilities", capabilities);

        JsonObject serverInfo = new JsonObject();
        serverInfo.addProperty("name", "sootup-mcp-server");
        serverInfo.addProperty("version", "1.0.0");
        result.add("serverInfo", serverInfo);

        return result;
    }

    private static JsonObject handleToolsList() {
        JsonObject result = new JsonObject();
        JsonArray tools = new JsonArray();

        // 1. sootup_hierarchy
        tools.add(createTool(
                "sootup_hierarchy",
                "Retrieves transitive superclasses, direct/indirect subclasses (including anonymous inner classes), and implemented interfaces for a target Java class.",
                new String[]{"target_class"},
                new ParamDef("target_class", "string", "Fully-qualified class name (e.g. com.google.gson.TypeAdapter)"),
                new ParamDef("target_dir", "string", "Path to compiled bytecode target/classes (defaults to workspace classes)")
        ));

        // 2. sootup_inspect_method
        tools.add(createTool(
                "sootup_inspect_method",
                "Disassembles a Java method into Jimple 3-address IR with source line numbers, declaring class, and outer enclosing class.",
                new String[]{"target_class", "target_method"},
                new ParamDef("target_class", "string", "Fully-qualified class name (e.g. com.google.gson.Gson$1)"),
                new ParamDef("target_method", "string", "Method name to disassemble (e.g. write)"),
                new ParamDef("target_dir", "string", "Path to compiled bytecode directory")
        ));

        // 3. sootup_find_allocations
        tools.add(createTool(
                "sootup_find_allocations",
                "Scans Jimple method bodies for JNewExpr to locate instantiation sites of a target class. Pinpoints factory instantiation sites.",
                new String[]{"target_class"},
                new ParamDef("target_class", "string", "Fully-qualified class name being instantiated (e.g. com.google.gson.Gson$1)"),
                new ParamDef("scope_class", "string", "Optional scope class to restrict scan (e.g. com.google.gson.Gson)"),
                new ParamDef("target_dir", "string", "Path to compiled bytecode directory")
        ));

        // 4. sootup_find_invocations
        tools.add(createTool(
                "sootup_find_invocations",
                "Scans Jimple method bodies for InvokableStmt to find all caller locations for a specific method across classes.",
                new String[]{"target_class", "target_method"},
                new ParamDef("target_class", "string", "Declaring class of invoked method (e.g. org.apache.druid.java.util.common.JodaUtils)"),
                new ParamDef("target_method", "string", "Method name invoked (e.g. condenseIntervals)"),
                new ParamDef("scope_class", "string", "Optional class to restrict search"),
                new ParamDef("target_dir", "string", "Path to compiled bytecode directory")
        ));

        // 5. sootup_callgraph
        tools.add(createTool(
                "sootup_callgraph",
                "Constructs an interprocedural Call Graph using CHA, RTA, or SPARK starting from an entry point signature.",
                new String[]{"algorithm", "entry_class", "entry_method", "return_type"},
                new ParamDef("algorithm", "string", "Call graph algorithm: cha, rta, or spark"),
                new ParamDef("entry_class", "string", "Entry point class name"),
                new ParamDef("entry_method", "string", "Entry point method name"),
                new ParamDef("return_type", "string", "Method return type (e.g. void)"),
                new ParamDef("param_types", "array", "Optional list of parameter types"),
                new ParamDef("target_dir", "string", "Path to compiled bytecode directory")
        ));

        result.add("tools", tools);
        return result;
    }

    private static JsonObject handleToolCall(JsonObject params) {
        String toolName = params.get("name").getAsString();
        JsonObject args = params.has("arguments") ? params.getAsJsonObject("arguments") : new JsonObject();

        String targetDir = defaultTargetDir;
        if (args.has("target_dir") && !args.get("target_dir").getAsString().trim().isEmpty()) {
            targetDir = args.get("target_dir").getAsString().trim();
        }

        if (targetDir.isEmpty()) {
            return makeToolError("No target directory specified. Set target_dir in tool arguments or initialization options.");
        }

        SootUpAnalyzer analyzer = analyzerCache.computeIfAbsent(targetDir, SootUpAnalyzer::new);

        try {
            String outputText;
            switch (toolName) {
                case "sootup_hierarchy": {
                    String targetClass = args.get("target_class").getAsString();
                    outputText = analyzer.getHierarchy(targetClass);
                    break;
                }
                case "sootup_inspect_method": {
                    String targetClass = args.get("target_class").getAsString();
                    String targetMethod = args.get("target_method").getAsString();
                    outputText = analyzer.inspectMethod(targetClass, targetMethod);
                    break;
                }
                case "sootup_find_allocations": {
                    String targetClass = args.get("target_class").getAsString();
                    String scopeClass = args.has("scope_class") ? args.get("scope_class").getAsString() : null;
                    outputText = analyzer.findAllocations(targetClass, scopeClass);
                    break;
                }
                case "sootup_find_invocations": {
                    String targetClass = args.get("target_class").getAsString();
                    String targetMethod = args.get("target_method").getAsString();
                    String scopeClass = args.has("scope_class") ? args.get("scope_class").getAsString() : null;
                    outputText = analyzer.findInvocations(targetClass, targetMethod, scopeClass);
                    break;
                }
                case "sootup_callgraph": {
                    String algorithm = args.get("algorithm").getAsString();
                    String entryClass = args.get("entry_class").getAsString();
                    String entryMethod = args.get("entry_method").getAsString();
                    String returnType = args.get("return_type").getAsString();
                    List<String> paramTypes = new ArrayList<>();
                    if (args.has("param_types") && args.get("param_types").isJsonArray()) {
                        for (JsonElement el : args.getAsJsonArray("param_types")) {
                            paramTypes.add(el.getAsString());
                        }
                    }
                    outputText = analyzer.getCallGraph(algorithm, entryClass, entryMethod, returnType, paramTypes);
                    break;
                }
                default:
                    return makeToolError("Unknown tool: " + toolName);
            }

            JsonObject result = new JsonObject();
            JsonArray content = new JsonArray();
            JsonObject textItem = new JsonObject();
            textItem.addProperty("type", "text");
            textItem.addProperty("text", outputText);
            content.add(textItem);
            result.add("content", content);
            result.addProperty("isError", false);
            return result;

        } catch (Exception e) {
            return makeToolError("Exception executing " + toolName + ": " + e.getMessage());
        }
    }

    private static JsonObject makeToolError(String message) {
        JsonObject result = new JsonObject();
        JsonArray content = new JsonArray();
        JsonObject textItem = new JsonObject();
        textItem.addProperty("type", "text");
        textItem.addProperty("text", message);
        content.add(textItem);
        result.add("content", content);
        result.addProperty("isError", true);
        return result;
    }

    private static JsonObject createTool(String name, String description, String[] required, ParamDef... params) {
        JsonObject tool = new JsonObject();
        tool.addProperty("name", name);
        tool.addProperty("description", description);

        JsonObject schema = new JsonObject();
        schema.addProperty("type", "object");

        JsonObject props = new JsonObject();
        for (ParamDef p : params) {
            JsonObject prop = new JsonObject();
            prop.addProperty("type", p.type);
            prop.addProperty("description", p.description);
            props.add(p.name, prop);
        }
        schema.add("properties", props);

        JsonArray req = new JsonArray();
        for (String r : required) req.add(r);
        schema.add("required", req);

        tool.add("inputSchema", schema);
        return tool;
    }

    private static class ParamDef {
        final String name;
        final String type;
        final String description;

        ParamDef(String name, String type, String description) {
            this.name = name;
            this.type = type;
            this.description = description;
        }
    }
}
