"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import {
  Folder,
  FolderOpen,
  FileCode,
  FileText,
  ChevronRight,
  ChevronDown,
  Info,
  Layers,
  Loader2,
  AlertCircle,
  Copy,
  Check,
  FileBox,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileTreeNode, RepoTreeItem, FileContentResponse } from "@/types";
import { getRepositoryTree, getRepositoryFile } from "@/lib/api";

interface RepositoryTreeProps {
  owner?: string;
  repo?: string;
  branch?: string;
  isLive?: boolean;
}

const INITIAL_TREE: FileTreeNode[] = [
  {
    id: "fastapi",
    name: "fastapi",
    type: "folder",
    path: "fastapi/",
    description: "Core framework package containing request routing, dependency injection, and application lifecycle.",
    children: [
      {
        id: "applications.py",
        name: "applications.py",
        type: "file",
        path: "fastapi/applications.py",
        description: "Defines the main FastAPI application class inheriting from Starlette, configuring OpenAPI schema generation and sub-apps.",
      },
      {
        id: "routing.py",
        name: "routing.py",
        type: "file",
        path: "fastapi/routing.py",
        description: "Handles route registration, APIRouter routing logic, parameter resolution, and request dispatching.",
      },
      {
        id: "params.py",
        name: "params.py",
        type: "file",
        path: "fastapi/params.py",
        description: "Defines parameter descriptors (Query, Path, Header, Body, Depends, Security) for endpoint function signature parsing.",
      },
      {
        id: "dependencies",
        name: "dependencies",
        type: "folder",
        path: "fastapi/dependencies/",
        description: "Internal dependency injection resolution system resolving async generators and callable dependencies.",
        children: [
          {
            id: "models.py",
            name: "models.py",
            type: "file",
            path: "fastapi/dependencies/models.py",
            description: "Internal models representing dependency graph structures and cached sub-dependency values.",
          },
          {
            id: "utils.py",
            name: "utils.py",
            type: "file",
            path: "fastapi/dependencies/utils.py",
            description: "Helper routines executing dependency graphs and binding request parameters to function arguments.",
          },
        ],
      },
    ],
  },
  {
    id: "tests",
    name: "tests",
    type: "folder",
    path: "tests/",
    description: "Comprehensive pytest test suite covering edge cases, async fixtures, tutorial codes, and regression tests.",
    children: [
      {
        id: "test_routing.py",
        name: "test_routing.py",
        type: "file",
        path: "tests/test_routing.py",
        description: "Integration tests verifying HTTP method dispatching, prefix routing, and path parameter conversions.",
      },
      {
        id: "test_dependency.py",
        name: "test_dependency.py",
        type: "file",
        path: "tests/test_dependency.py",
        description: "Unit tests evaluating deep dependency hierarchies, overrides, and session lifecycles.",
      },
    ],
  },
  {
    id: "docs",
    name: "docs",
    type: "folder",
    path: "docs/",
    description: "Documentation markdown files and multilingual community translations generated via MkDocs.",
  },
  {
    id: "README.md",
    name: "README.md",
    type: "file",
    path: "README.md",
    description: "Project homepage documentation detailing benchmarks, quickstart guide, key features, and sponsor list.",
  },
  {
    id: "CONTRIBUTING.md",
    name: "CONTRIBUTING.md",
    type: "file",
    path: "CONTRIBUTING.md",
    description: "Official contribution rules, dev environment setup guide, git commit expectations, and PR review checklist.",
  },
  {
    id: "pyproject.toml",
    name: "pyproject.toml",
    type: "file",
    path: "pyproject.toml",
    description: "Build configuration file declaring project metadata, dependencies (Pydantic, Starlette), and tool configs.",
  },
];

/**
 * Builds a nested FileTreeNode hierarchy from a flat array of repository tree items.
 */
function buildHierarchy(items: RepoTreeItem[]): FileTreeNode[] {
  const root: FileTreeNode = {
    id: "root",
    name: "root",
    type: "folder",
    path: "",
    children: [],
  };

  for (const item of items) {
    const parts = item.path.split("/");
    let current = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isLast = i === parts.length - 1;
      const currentPath = parts.slice(0, i + 1).join("/");

      if (isLast) {
        if (!current.children) current.children = [];
        if (!current.children.some((c) => c.path === currentPath)) {
          current.children.push({
            id: currentPath,
            name: part,
            type: item.type === "directory" ? "folder" : "file",
            path: currentPath,
            description: item.language
              ? `${item.language} (${item.category || "file"})`
              : item.category || undefined,
          });
        }
      } else {
        if (!current.children) current.children = [];
        let folder = current.children.find((c) => c.path === currentPath);
        if (!folder) {
          folder = {
            id: currentPath,
            name: part,
            type: "folder",
            path: currentPath,
            children: [],
          };
          current.children.push(folder);
        }
        current = folder;
      }
    }
  }

  function sortNodes(nodes: FileTreeNode[]) {
    nodes.sort((a, b) => {
      if (a.type !== b.type) {
        return a.type === "folder" ? -1 : 1;
      }
      return a.name.localeCompare(b.name);
    });
    for (const node of nodes) {
      if (node.children) {
        sortNodes(node.children);
      }
    }
  }

  if (root.children) {
    sortNodes(root.children);
    return root.children;
  }
  return [];
}

export function RepositoryTree({ owner, repo, branch, isLive = false }: RepositoryTreeProps) {
  // Live tree state
  const [rawTreeItems, setRawTreeItems] = useState<RepoTreeItem[]>([]);
  const [isLoadingTree, setIsLoadingTree] = useState(false);
  const [treeError, setTreeError] = useState<string | null>(null);
  const [isTruncated, setIsTruncated] = useState(false);

  // Folder open/closed states
  const [openFolders, setOpenFolders] = useState<Record<string, boolean>>({
    fastapi: true,
    dependencies: false,
    tests: false,
  });

  // Selected node state
  const [selectedNode, setSelectedNode] = useState<FileTreeNode>({
    id: "routing.py",
    name: "routing.py",
    type: "file",
    path: "fastapi/routing.py",
    description: "Handles route registration, APIRouter routing logic, parameter resolution, and request dispatching.",
  });

  // On-demand file content state
  const [fileContent, setFileContent] = useState<FileContentResponse | null>(null);
  const [isLoadingContent, setIsLoadingContent] = useState(false);
  const [contentError, setContentError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Fetch real repository tree when isLive and owner/repo are present
  const fetchTree = useCallback(async () => {
    if (!isLive || !owner || !repo) return;

    setIsLoadingTree(true);
    setTreeError(null);
    try {
      const data = await getRepositoryTree(owner, repo, branch);
      setRawTreeItems(data.tree);
      setIsTruncated(data.truncated);

      // Auto-open root/top-level folders
      const initialOpen: Record<string, boolean> = {};
      data.tree.forEach((item) => {
        const rootSegment = item.path.split("/")[0];
        if (item.type === "directory" || item.path.includes("/")) {
          initialOpen[rootSegment] = true;
        }
      });
      setOpenFolders(initialOpen);

      // Default select the first file (or README if present)
      const readme = data.tree.find(
        (t) => t.type === "file" && t.path.toLowerCase() === "readme.md"
      );
      const firstFile = readme || data.tree.find((t) => t.type === "file");
      if (firstFile) {
        setSelectedNode({
          id: firstFile.path,
          name: firstFile.path.split("/").pop() || firstFile.path,
          type: "file",
          path: firstFile.path,
          description: firstFile.language
            ? `${firstFile.language} (${firstFile.category || "file"})`
            : firstFile.category || undefined,
        });
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load repository tree";
      setTreeError(message);
    } finally {
      setIsLoadingTree(false);
    }
  }, [isLive, owner, repo, branch]);

  useEffect(() => {
    if (isLive && owner && repo) {
      fetchTree();
    } else {
      setRawTreeItems([]);
      setTreeError(null);
    }
  }, [isLive, owner, repo, branch, fetchTree]);

  // Fetch individual file content on-demand when a file node is selected in live mode
  useEffect(() => {
    if (!isLive || !owner || !repo || !selectedNode || selectedNode.type !== "file") {
      setFileContent(null);
      return;
    }

    let isMounted = true;
    setIsLoadingContent(true);
    setContentError(null);

    getRepositoryFile(owner, repo, selectedNode.path, branch)
      .then((data) => {
        if (isMounted) {
          setFileContent(data);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const message = err instanceof Error ? err.message : "Failed to load file content";
          setContentError(message);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoadingContent(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [isLive, owner, repo, branch, selectedNode]);

  // Build tree hierarchy
  const activeTree: FileTreeNode[] = useMemo(() => {
    if (isLive && rawTreeItems.length > 0) {
      return buildHierarchy(rawTreeItems);
    }
    return INITIAL_TREE;
  }, [isLive, rawTreeItems]);

  const toggleFolder = (folderId: string) => {
    setOpenFolders((prev) => ({
      ...prev,
      [folderId]: !prev[folderId],
    }));
  };

  const handleCopyCode = () => {
    if (!fileContent?.content) return;
    navigator.clipboard.writeText(fileContent.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatFileSize = (bytes?: number | null) => {
    if (!bytes && bytes !== 0) return null;
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const renderTree = (nodes: FileTreeNode[], depth = 0) => {
    return (
      <ul className="space-y-1">
        {nodes.map((node) => {
          const isFolder = node.type === "folder";
          const isOpen = openFolders[node.id];
          const isSelected = selectedNode?.id === node.id;

          return (
            <li key={node.id} className="select-none">
              <div
                onClick={() => {
                  if (isFolder) toggleFolder(node.id);
                  setSelectedNode(node);
                }}
                className={`flex items-center space-x-2 px-2.5 py-1.5 rounded-md text-xs font-mono transition-colors cursor-pointer ${
                  isSelected
                    ? "bg-primary/15 text-primary font-medium border border-primary/30"
                    : "text-muted-foreground hover:bg-secondary/70 hover:text-foreground"
                }`}
                style={{ paddingLeft: `${depth * 14 + 10}px` }}
              >
                {isFolder ? (
                  <span className="flex items-center space-x-1.5 shrink-0">
                    {isOpen ? (
                      <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                    )}
                    {isOpen ? (
                      <FolderOpen className="h-4 w-4 text-sky-500 dark:text-sky-400" />
                    ) : (
                      <Folder className="h-4 w-4 text-sky-500 dark:text-sky-400" />
                    )}
                  </span>
                ) : (
                  <span className="flex items-center space-x-1.5 shrink-0 pl-4">
                    {node.name.endsWith(".md") || node.name.endsWith(".rst") ? (
                      <FileText className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
                    ) : (
                      <FileCode className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                    )}
                  </span>
                )}
                <span className="truncate">{node.name}</span>
              </div>

              {isFolder && isOpen && node.children && (
                <div className="border-l border-border/40 ml-4 pl-1 mt-0.5">
                  {renderTree(node.children, depth + 1)}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    );
  };

  return (
    <section id="structure" className="py-12 border-t border-border/40">
      <div className="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary mb-1">
              <Layers className="h-3.5 w-3.5" />
              <span>Codebase Topology</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Repository Structure
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {isLive
                ? "Browse the actual file hierarchy and inspect source code on demand."
                : "Explore key directories and files with contextual role explanations."}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {isLive ? (
              <Badge variant="outline" className="border-emerald-500/40 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 text-xs font-medium uppercase tracking-wider">
                Live GitHub Tree
              </Badge>
            ) : (
              <Badge variant="warning" className="text-xs font-medium uppercase tracking-wider self-start sm:self-auto">
                Example Preview • Demo Data
              </Badge>
            )}
            {isTruncated && (
              <Badge variant="outline" className="text-[10px] text-amber-600 dark:text-amber-400 border-amber-500/30">
                Truncated Tree
              </Badge>
            )}
          </div>
        </div>

        {/* Interactive Dual Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Tree Navigation Panel */}
          <Card className="lg:col-span-5 border-border bg-card/60 shadow-lg">
            <CardHeader className="p-4 border-b border-border/40 bg-secondary/20">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xs font-mono font-semibold text-foreground truncate">
                  {isLive && owner && repo ? `${owner}/${repo}` : "fastapi / src"}
                </CardTitle>
                <span className="text-[10px] text-muted-foreground font-mono shrink-0 ml-2">
                  {isLive && rawTreeItems.length > 0 ? `${rawTreeItems.length} items` : "Click to inspect"}
                </span>
              </div>
            </CardHeader>
            <CardContent className="p-3 max-h-[500px] overflow-y-auto">
              {isLoadingTree ? (
                <div className="flex flex-col items-center justify-center py-16 space-y-3 text-muted-foreground">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                  <p className="text-xs">Fetching repository tree from GitHub...</p>
                </div>
              ) : treeError ? (
                <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20 space-y-2 text-center">
                  <AlertCircle className="h-5 w-5 text-destructive mx-auto" />
                  <p className="text-xs text-destructive font-medium">{treeError}</p>
                  <Button size="sm" variant="outline" onClick={fetchTree} className="text-xs h-7 mt-2">
                    Retry
                  </Button>
                </div>
              ) : (
                renderTree(activeTree)
              )}
            </CardContent>
          </Card>

          {/* Inspector / Explanation / Code Panel */}
          <Card className="lg:col-span-7 border-border bg-card/80 shadow-lg">
            <CardHeader className="p-5 border-b border-border/40 bg-secondary/15">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1 truncate">
                  <div className="flex items-center gap-2 truncate">
                    <span className="font-mono text-sm font-bold text-foreground truncate">
                      {selectedNode.path}
                    </span>
                    <Badge variant="outline" className="text-[10px] uppercase font-mono shrink-0">
                      {selectedNode.type}
                    </Badge>
                    {isLive && fileContent?.language && (
                      <Badge variant="secondary" className="text-[10px] font-mono shrink-0">
                        {fileContent.language}
                      </Badge>
                    )}
                    {isLive && fileContent?.category && (
                      <Badge variant="outline" className="text-[10px] uppercase text-muted-foreground shrink-0">
                        {fileContent.category}
                      </Badge>
                    )}
                  </div>
                  <CardDescription className="text-xs">
                    {isLive
                      ? fileContent?.size
                        ? `File size: ${formatFileSize(fileContent.size)}`
                        : "Source code inspection"
                      : "File Role & Responsibility Breakdown"}
                  </CardDescription>
                </div>

                {isLive && fileContent?.content && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleCopyCode}
                    className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground shrink-0"
                  >
                    {copied ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-emerald-400 mr-1" />
                        <span className="text-emerald-400">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5 mr-1" />
                        <span>Copy Code</span>
                      </>
                    )}
                  </Button>
                )}
              </div>
            </CardHeader>

            <CardContent className="p-5 space-y-4">
              {/* Live File Content Viewer */}
              {isLive ? (
                <div>
                  {selectedNode.type === "folder" ? (
                    <div className="py-12 text-center space-y-2 text-muted-foreground">
                      <Folder className="h-8 w-8 mx-auto text-sky-500/80 dark:text-sky-400/80" />
                      <p className="text-sm font-medium text-foreground">Directory: {selectedNode.name}</p>
                      <p className="text-xs">Select any file inside this folder to view its contents.</p>
                    </div>
                  ) : isLoadingContent ? (
                    <div className="flex flex-col items-center justify-center py-16 space-y-3 text-muted-foreground">
                      <Loader2 className="h-6 w-6 animate-spin text-primary" />
                      <p className="text-xs font-mono">Loading file content from GitHub...</p>
                    </div>
                  ) : contentError ? (
                    <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20 space-y-2 text-center">
                      <AlertCircle className="h-5 w-5 text-destructive mx-auto" />
                      <p className="text-xs text-destructive font-medium">{contentError}</p>
                    </div>
                  ) : fileContent?.skip_reason ? (
                    <div className="p-6 rounded-lg bg-secondary/30 border border-border/60 text-center space-y-2">
                      <FileBox className="h-8 w-8 mx-auto text-amber-500 dark:text-amber-400" />
                      <p className="text-sm font-medium text-foreground">File Content Omitted</p>
                      <p className="text-xs text-muted-foreground">{fileContent.skip_reason}</p>
                    </div>
                  ) : fileContent?.content !== undefined && fileContent?.content !== null ? (
                    <div className="relative rounded-lg border border-border/60 bg-background/80 overflow-hidden">
                      <div className="max-h-[440px] overflow-auto p-4 font-mono text-xs text-foreground/90 leading-relaxed">
                        <pre className="table w-full">
                          {fileContent.content.split("\n").map((line, idx) => (
                            <div key={idx} className="table-row hover:bg-secondary/30">
                              <span className="table-cell pr-4 select-none text-right text-[11px] text-muted-foreground/50 w-10">
                                {idx + 1}
                              </span>
                              <span className="table-cell whitespace-pre font-mono">{line || " "}</span>
                            </div>
                          ))}
                        </pre>
                      </div>
                    </div>
                  ) : (
                    <div className="py-12 text-center text-xs text-muted-foreground">
                      Select a file from the repository tree to inspect its code.
                    </div>
                  )}
                </div>
              ) : (
                /* Demo Inspector */
                <>
                  <div className="p-4 rounded-lg bg-secondary/30 border border-border/60 space-y-2">
                    <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                      <Info className="h-4 w-4 text-primary" />
                      <span>Component Summary</span>
                    </div>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {selectedNode.description ||
                        "Select any file in the tree to view its role and architecture breakdown."}
                    </p>
                  </div>

                  <div className="text-xs text-muted-foreground space-y-2">
                    <p className="font-medium text-foreground">Contribution Relevance:</p>
                    <ul className="list-disc list-inside space-y-1 text-muted-foreground/80 pl-1">
                      <li>
                        Changes in this module require running unit tests under{" "}
                        <code className="font-mono text-[11px] text-foreground/90 bg-secondary px-1 py-0.5 rounded">
                          tests/
                        </code>
                      </li>
                      <li>
                        Referenced by routing decorators:{" "}
                        <code className="font-mono text-[11px] text-foreground/90 bg-secondary px-1 py-0.5 rounded">
                          @app.get()
                        </code>
                        ,{" "}
                        <code className="font-mono text-[11px] text-foreground/90 bg-secondary px-1 py-0.5 rounded">
                          @app.post()
                        </code>
                      </li>
                      <li>High architectural significance for API dispatching.</li>
                    </ul>
                  </div>

                  <div className="pt-2 border-t border-border/40 text-[11px] text-muted-foreground">
                    Demonstration UI: Clicking any file/folder updates the contextual inspector dynamically.
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}
