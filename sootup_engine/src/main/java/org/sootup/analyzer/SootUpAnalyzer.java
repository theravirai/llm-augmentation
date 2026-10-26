package org.sootup.analyzer;

import sootup.core.inputlocation.AnalysisInputLocation;
import sootup.java.bytecode.frontend.inputlocation.PathBasedAnalysisInputLocation;
import sootup.java.bytecode.frontend.inputlocation.DefaultRuntimeAnalysisInputLocation;
import sootup.core.model.SourceType;
import sootup.java.core.views.JavaView;
import sootup.core.typehierarchy.TypeHierarchy;
import sootup.core.typehierarchy.ViewTypeHierarchy;
import sootup.java.core.types.JavaClassType;
import sootup.core.types.ClassType;
import sootup.java.core.JavaIdentifierFactory;
import sootup.core.signatures.MethodSignature;
import sootup.callgraph.CallGraph;
import sootup.callgraph.ClassHierarchyAnalysisAlgorithm;
import sootup.callgraph.RapidTypeAnalysisAlgorithm;
import sootup.spark.Spark;
import sootup.spark.SparkOptions;
import sootup.core.jimple.common.stmt.Stmt;
import sootup.core.jimple.common.stmt.JAssignStmt;
import sootup.core.jimple.common.expr.JNewExpr;
import sootup.core.jimple.common.expr.AbstractInvokeExpr;
import sootup.java.core.JavaSootClass;
import sootup.core.model.SootMethod;
import sootup.core.frontend.SootClassSource;

import java.nio.file.Paths;
import java.util.*;

/**
 * Core static analysis fact extractor built on SootUp 3.x.
 * Exposes 5 deterministic bytecode primitives over Jimple IR.
 */
public class SootUpAnalyzer {

    private final JavaView view;
    private final JavaIdentifierFactory factory;

    public SootUpAnalyzer(String targetDir) {
        List<AnalysisInputLocation> inputLocations = new ArrayList<>();
        inputLocations.add(new DefaultRuntimeAnalysisInputLocation());
        for (String path : targetDir.split(",")) {
            String trimmed = path.trim();
            if (!trimmed.isEmpty()) {
                inputLocations.add(PathBasedAnalysisInputLocation.create(Paths.get(trimmed), SourceType.Application));
            }
        }
        this.view = new JavaView(inputLocations);
        this.factory = view.getIdentifierFactory();
    }

    public JavaView getView() {
        return view;
    }

    public JavaIdentifierFactory getFactory() {
        return factory;
    }

    /**
     * Primitive 1: Class Hierarchy
     * Finds superclasses, direct/indirect subclasses, and implemented interfaces.
     */
    public String getHierarchy(String targetClassName) {
        StringBuilder sb = new StringBuilder();
        JavaClassType classType = factory.getClassType(targetClassName);
        sb.append("=== CLASS HIERARCHY FACT ===\n");
        sb.append("Target: ").append(targetClassName).append("\n");

        if (!view.getClass(classType).isPresent()) {
            sb.append("Status: Class not found in view.\n");
            return sb.toString();
        }

        TypeHierarchy th = new ViewTypeHierarchy(view);
        sb.append("\nSuperclasses:\n");
        th.superClassesOf(classType).forEach(sc -> sb.append(" - ").append(sc.getFullyQualifiedName()).append("\n"));

        sb.append("\nSubclasses:\n");
        th.subclassesOf(classType).forEach(sc -> sb.append(" - ").append(sc.getFullyQualifiedName()).append("\n"));

        sb.append("\nImplemented Interfaces:\n");
        th.implementedInterfacesOf(classType).forEach(sc -> sb.append(" - ").append(sc.getFullyQualifiedName()).append("\n"));

        return sb.toString();
    }

    /**
     * Primitive 2: Inspect Method
     * Disassembles method body into Jimple 3-address IR with source line mappings.
     */
    public String inspectMethod(String targetClass, String targetMethod) {
        StringBuilder sb = new StringBuilder();
        JavaClassType classType = factory.getClassType(targetClass);
        Optional<JavaSootClass> scOpt = view.getClass(classType);

        if (!scOpt.isPresent()) {
            return "Error: Class " + targetClass + " not found.";
        }

        JavaSootClass sc = scOpt.get();
        Set<? extends SootMethod> methods = sc.getMethodsByName(targetMethod);
        if (methods.isEmpty()) {
            return "Error: Method " + targetMethod + " not found in " + targetClass;
        }

        for (SootMethod method : methods) {
            sb.append("=== METHOD INSPECTION FACT ===\n");
            sb.append("Signature: ").append(method.getSignature()).append("\n");
            sb.append("Declaring Class: ").append(sc.getName()).append("\n");

            if (sc.hasOuterClass()) {
                sb.append("Outer Class: ").append(sc.getOuterClass().get().getClassName()).append("\n");
            }

            SootClassSource source = sc.getClassSource();
            if (source != null) {
                sb.append("Source File: ").append(source.getSourcePath()).append("\n");
            }

            sb.append("\nJimple Body:\n");
            if (method.hasBody()) {
                for (Stmt stmt : method.getBody().getStmts()) {
                    int line = stmt.getPositionInfo().getStmtPosition().getFirstLine();
                    String linePrefix = line > 0 ? "[Line " + line + "] " : "[Line ?] ";
                    sb.append(linePrefix).append(stmt.toString()).append("\n");
                }
            } else {
                sb.append("<No body available>\n");
            }
            sb.append("\n");
        }
        return sb.toString();
    }

    /**
     * Primitive 3: Find Allocations
     * Scans Jimple bodies for JNewExpr to locate instantiation sites of targetClass.
     */
    public String findAllocations(String targetClass, String scopeClass) {
        StringBuilder sb = new StringBuilder();
        sb.append("=== ALLOCATION SITE FACT ===\n");
        sb.append("Target Class: ").append(targetClass).append("\n");
        if (scopeClass != null && !scopeClass.isEmpty()) {
            sb.append("Scope Class: ").append(scopeClass).append("\n");
        }

        List<JavaSootClass> classesToScan = getClassesToScan(scopeClass);
        int matchCount = 0;

        for (JavaSootClass sc : classesToScan) {
            for (SootMethod method : sc.getMethods()) {
                if (!method.hasBody()) continue;
                for (Stmt stmt : method.getBody().getStmts()) {
                    if (stmt instanceof JAssignStmt) {
                        JAssignStmt assign = (JAssignStmt) stmt;
                        if (assign.getRightOp() instanceof JNewExpr) {
                            JNewExpr newExpr = (JNewExpr) assign.getRightOp();
                            String typeStr = newExpr.getType().toString();
                            boolean match = typeStr.equals(targetClass);
                            if (!match && newExpr.getType() instanceof ClassType) {
                                match = ((ClassType) newExpr.getType()).getClassName().equals(targetClass)
                                     || ((ClassType) newExpr.getType()).getFullyQualifiedName().equals(targetClass);
                            }
                            if (match) {
                                matchCount++;
                                appendMatch(sb, method, stmt, "Allocates: " + typeStr);
                            }
                        }
                    }
                }
            }
        }
        if (matchCount == 0) {
            sb.append("No allocation sites found for ").append(targetClass).append("\n");
        }
        return sb.toString();
    }

    /**
     * Primitive 4: Find Invocations
     * Traces caller sites for a target method across classes.
     */
    public String findInvocations(String targetClass, String targetMethod, String scopeClass) {
        StringBuilder sb = new StringBuilder();
        sb.append("=== INVOCATION SITE FACT ===\n");
        sb.append("Target Method: ").append(targetClass).append(".").append(targetMethod).append("\n");
        if (scopeClass != null && !scopeClass.isEmpty()) {
            sb.append("Scope Class: ").append(scopeClass).append("\n");
        }

        List<JavaSootClass> classesToScan = getClassesToScan(scopeClass);
        int matchCount = 0;

        for (JavaSootClass sc : classesToScan) {
            for (SootMethod method : sc.getMethods()) {
                if (!method.hasBody()) continue;
                for (Stmt stmt : method.getBody().getStmts()) {
                    AbstractInvokeExpr invokeExpr = null;
                    if (stmt.isInvokableStmt()) {
                        Optional<AbstractInvokeExpr> opt = stmt.asInvokableStmt().getInvokeExpr();
                        if (opt.isPresent()) invokeExpr = opt.get();
                    } else if (stmt.isJAssignStmt()) {
                        JAssignStmt assign = stmt.asJAssignStmt();
                        if (assign.getRightOp() instanceof AbstractInvokeExpr) {
                            invokeExpr = (AbstractInvokeExpr) assign.getRightOp();
                        }
                    }
                    if (invokeExpr != null) {
                        MethodSignature sig = invokeExpr.getMethodSignature();
                        String fqName = sig.getDeclClassType().getFullyQualifiedName();
                        String simpleName = sig.getDeclClassType().getClassName();
                        if ((fqName.equals(targetClass) || simpleName.equals(targetClass)) && sig.getName().equals(targetMethod)) {
                            matchCount++;
                            appendMatch(sb, method, stmt, "Invokes: " + sig);
                        }
                    }
                }
            }
        }
        if (matchCount == 0) {
            sb.append("No invocation sites found for ").append(targetClass).append(".").append(targetMethod).append("\n");
        }
        return sb.toString();
    }

    /**
     * Primitive 5: Call Graph
     * Computes interprocedural call graph using CHA, RTA, or SPARK.
     */
    public String getCallGraph(String algorithm, String entryClass, String entryMethod, String returnType, List<String> paramTypes) {
        StringBuilder sb = new StringBuilder();
        if (paramTypes == null) paramTypes = Collections.emptyList();

        JavaClassType classType = factory.getClassType(entryClass);
        MethodSignature entrySignature = factory.getMethodSignature(classType, entryMethod, returnType, paramTypes);

        CallGraph cg;
        String algoUpper = algorithm.toUpperCase();
        if (algoUpper.equals("CHA")) {
            cg = new ClassHierarchyAnalysisAlgorithm(view).initialize(Collections.singletonList(entrySignature));
        } else if (algoUpper.equals("RTA")) {
            cg = new RapidTypeAnalysisAlgorithm(view).initialize(Collections.singletonList(entrySignature));
        } else if (algoUpper.equals("SPARK")) {
            SparkOptions options = SparkOptions.builder().onFlyCallGraph(true).build();
            Spark spark = Spark.builder().view(view).entryPoints(Collections.singletonList(entrySignature)).sparkOptions(options).build();
            spark.solve();
            cg = spark.getCallGraph();
        } else {
            return "Error: Unknown algorithm: " + algorithm + ". Choose CHA, RTA, or SPARK.";
        }

        sb.append("=== CALL GRAPH FACT ===\n");
        sb.append("Target: ").append(entrySignature).append("\n");
        sb.append("Algorithm: ").append(algoUpper).append("\n");
        sb.append("Total Reachable Methods: ").append(cg.getMethodSignatures().size()).append("\n");

        sb.append("\nCalls FROM target:\n");
        cg.callTargetsFrom(entrySignature).forEach(callee -> sb.append(" -> ").append(callee).append("\n"));

        sb.append("\nCalls TO target:\n");
        cg.callSourcesTo(entrySignature).forEach(caller -> sb.append(" <- ").append(caller).append("\n"));

        return sb.toString();
    }

    private List<JavaSootClass> getClassesToScan(String scopeClass) {
        List<JavaSootClass> classes = new ArrayList<>();
        if (scopeClass != null && !scopeClass.trim().isEmpty()) {
            view.getClass(factory.getClassType(scopeClass.trim())).ifPresent(classes::add);
        } else {
            // Only scan application classes (from target/classes), skipping runtime JDK library classes
            view.getClasses()
                .filter(c -> c.isApplicationClass() && c instanceof JavaSootClass)
                .map(c -> (JavaSootClass) c)
                .forEach(classes::add);
        }
        return classes;
    }

    private void appendMatch(StringBuilder sb, SootMethod enclosingMethod, Stmt stmt, String detail) {
        sb.append("\nMatch Found:\n");
        sb.append(" - ").append(detail).append("\n");
        sb.append(" - Enclosing Method: ").append(enclosingMethod.getSignature()).append("\n");

        int line = stmt.getPositionInfo().getStmtPosition().getFirstLine();
        if (line > 0) {
            sb.append(" - Source Line: ").append(line).append("\n");
        }
        sb.append(" - Jimple Stmt: ").append(stmt.toString()).append("\n");
    }

    public static void main(String[] args) {
        if (args.length < 2) {
            System.err.println("Usage: java org.sootup.analyzer.SootUpAnalyzer <target-dir> <mode> [args...]");
            System.exit(1);
        }
        String targetDir = args[0];
        String mode = args[1].toLowerCase();
        SootUpAnalyzer analyzer = new SootUpAnalyzer(targetDir);

        switch (mode) {
            case "hierarchy":
                if (args.length < 3) {
                    System.err.println("Usage: hierarchy <class-name>");
                    System.exit(1);
                }
                System.out.println(analyzer.getHierarchy(args[2]));
                break;
            case "inspect-method":
                if (args.length < 4) {
                    System.err.println("Usage: inspect-method <class-name> <method-name>");
                    System.exit(1);
                }
                System.out.println(analyzer.inspectMethod(args[2], args[3]));
                break;
            case "find-allocations":
                if (args.length < 3) {
                    System.err.println("Usage: find-allocations <class-name> [scope-class]");
                    System.exit(1);
                }
                System.out.println(analyzer.findAllocations(args[2], args.length > 3 ? args[3] : null));
                break;
            case "find-invocations":
                if (args.length < 4) {
                    System.err.println("Usage: find-invocations <class-name> <method-name> [scope-class]");
                    System.exit(1);
                }
                System.out.println(analyzer.findInvocations(args[2], args[3], args.length > 4 ? args[4] : null));
                break;
            case "callgraph":
                if (args.length < 6) {
                    System.err.println("Usage: callgraph <cha|rta|spark> <entry-class> <entry-method> <return-type> [param-types...]");
                    System.exit(1);
                }
                List<String> params = new ArrayList<>();
                for (int i = 6; i < args.length; i++) params.add(args[i]);
                System.out.println(analyzer.getCallGraph(args[2], args[3], args[4], args[5], params));
                break;
            default:
                System.err.println("Error: Unknown mode '" + mode + "'");
                System.exit(1);
        }
    }
}
