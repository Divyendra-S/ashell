"use client";

import { useCallback, useRef, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import type { GraphData, ConceptDetail } from "../lib/api";
import { getConceptDetail, createNote, deleteNote } from "../lib/api";

const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
  ssr: false,
  loading: () => null,
});

// Concept-focused palette — varied hues for visual distinction
const CONCEPT_COLORS = [
  "#fbbf24", // amber
  "#34d399", // emerald
  "#60a5fa", // blue
  "#a78bfa", // violet
  "#fb923c", // orange
  "#f472b6", // pink
  "#2dd4bf", // teal
  "#e879f9", // fuchsia
];

function hashColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return CONCEPT_COLORS[Math.abs(hash) % CONCEPT_COLORS.length];
}

interface GraphNode {
  id: number;
  name: string;
  entity_type: string;
  fact_count: number;
  community_id: number | null;
  val: number;
  color: string;
  x?: number;
  y?: number;
  z?: number;
}

interface GraphLink {
  source: number | GraphNode;
  target: number | GraphNode;
  label: string;
}

export function KnowledgeGraph({
  data,
  userId,
}: {
  data: GraphData | null;
  userId: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const bloomAdded = useRef(false);

  // Panel state
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [conceptDetail, setConceptDetail] = useState<ConceptDetail | null>(null);
  const [panelLoading, setPanelLoading] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [savingNote, setSavingNote] = useState(false);

  // Track container size
  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) {
        setDimensions({ width, height });
      }
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  // Bloom post-processing
  useEffect(() => {
    if (!graphRef.current || bloomAdded.current) return;
    try {
      const THREE = require("three");
      const { UnrealBloomPass } = require("three/examples/jsm/postprocessing/UnrealBloomPass.js");
      const composer = graphRef.current.postProcessingComposer();
      if (!composer) return;
      const bloomPass = new UnrealBloomPass(
        new THREE.Vector2(dimensions.width, dimensions.height),
        1.0,
        0.4,
        0.85
      );
      composer.addPass(bloomPass);
      bloomAdded.current = true;
    } catch {
      // not ready yet
    }
  });

  // Configure forces
  useEffect(() => {
    if (!graphRef.current) return;
    try {
      graphRef.current.d3Force("charge")?.strength(-200).distanceMax(400);
      graphRef.current.d3Force("link")?.distance(80);
    } catch {
      // not ready
    }
  });

  const flyToNode = useCallback((node: any) => {
    if (!graphRef.current || !node) return;
    const distance = 120;
    const distRatio =
      1 + distance / Math.hypot(node.x || 0, node.y || 0, node.z || 0 || 1);
    graphRef.current.cameraPosition(
      {
        x: (node.x || 0) * distRatio,
        y: (node.y || 0) * distRatio,
        z: (node.z || 0) * distRatio,
      },
      { x: node.x, y: node.y, z: node.z },
      500
    );
  }, []);

  const loadConceptDetail = useCallback(
    async (nodeId: number) => {
      setPanelLoading(true);
      try {
        const detail = await getConceptDetail(nodeId, userId);
        setConceptDetail(detail);
      } catch (err) {
        console.error("Failed to load concept detail:", err);
        setConceptDetail(null);
      } finally {
        setPanelLoading(false);
      }
    },
    [userId]
  );

  const handleNodeClick = useCallback(
    (node: any) => {
      if (!node?.id) return;
      flyToNode(node);
      setSelectedNodeId(node.id);
      setNoteText("");
      loadConceptDetail(node.id);
    },
    [flyToNode, loadConceptDetail]
  );

  const handleBackgroundClick = useCallback(() => {
    setSelectedNodeId(null);
    setConceptDetail(null);
    setNoteText("");
  }, []);

  const handleEngineStop = useCallback(() => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(400, 100);
    }
  }, []);

  const handleAddNote = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!noteText.trim() || !selectedNodeId) return;
      setSavingNote(true);
      try {
        await createNote(userId, noteText.trim(), selectedNodeId);
        setNoteText("");
        await loadConceptDetail(selectedNodeId);
      } catch (err) {
        console.error("Failed to save note:", err);
      } finally {
        setSavingNote(false);
      }
    },
    [noteText, selectedNodeId, userId, loadConceptDetail]
  );

  const handleDeleteNote = useCallback(
    async (noteId: number) => {
      if (!selectedNodeId) return;
      try {
        await deleteNote(noteId, userId);
        await loadConceptDetail(selectedNodeId);
      } catch (err) {
        console.error("Failed to delete note:", err);
      }
    },
    [selectedNodeId, userId, loadConceptDetail]
  );

  const handleRelationClick = useCallback(
    (entityId: number) => {
      if (!data) return;
      // Find the node in graph data
      const entity = data.entities.find((e) => e.id === entityId);
      if (!entity) return;
      // Find the rendered node (with x/y/z coords)
      const fg = graphRef.current;
      if (!fg) return;
      const graphData = fg.graphData();
      const node = graphData.nodes.find((n: any) => n.id === entityId);
      if (node) {
        flyToNode(node);
      }
      setSelectedNodeId(entityId);
      setNoteText("");
      loadConceptDetail(entityId);
    },
    [data, flyToNode, loadConceptDetail]
  );

  if (!data || !data.entities.length) {
    return (
      <div
        ref={containerRef}
        className="flex items-center justify-center rounded-xl border border-surface-2 bg-surface-1"
        style={{ height: "calc(100vh - 280px)", minHeight: 500 }}
      >
        <p className="text-sm text-text-tertiary">
          {data
            ? "No concepts yet. Ingest an article to build your knowledge graph!"
            : "Loading graph..."}
        </p>
      </div>
    );
  }

  // Build community -> color map for consistent cluster coloring
  const communityIds = [
    ...new Set(
      data.entities.map((e) => e.community_id).filter((c): c is number => c != null)
    ),
  ].sort((a, b) => a - b);
  const communityColorMap: Record<number, string> = {};
  communityIds.forEach((cid, i) => {
    communityColorMap[cid] = CONCEPT_COLORS[i % CONCEPT_COLORS.length];
  });

  const nodes: GraphNode[] = data.entities.map((e) => ({
    id: e.id,
    name: e.name,
    entity_type: e.entity_type,
    fact_count: e.fact_count,
    community_id: e.community_id,
    val: Math.max(3, e.fact_count * 2 + 2),
    color: e.community_id != null
      ? communityColorMap[e.community_id]
      : hashColor(e.name),
  }));

  const nodeIds = new Set(nodes.map((n) => n.id));
  const links: GraphLink[] = data.relations
    .filter((r) => nodeIds.has(r.source_id) && nodeIds.has(r.target_id))
    .map((r) => ({
      source: r.source_id,
      target: r.target_id,
      label: r.relation_type,
    }));

  return (
    <div
      ref={containerRef}
      className="relative rounded-xl border border-surface-2 bg-[#09090b]"
      style={{ height: "calc(100vh - 280px)", minHeight: 500 }}
    >
      {/* Hint */}
      <div className="absolute bottom-3 left-3 z-10 rounded-lg bg-surface-0/80 px-3 py-1.5 backdrop-blur-sm">
        <span className="text-[10px] text-text-tertiary">
          Orbit to explore · Click a concept to learn more
        </span>
      </div>

      {/* Node count badge */}
      <div className="absolute left-3 top-3 z-10 rounded-lg bg-surface-0/80 px-3 py-1.5 backdrop-blur-sm">
        <span className="text-[10px] text-text-tertiary">
          {nodes.length} concepts · {links.length} connections
        </span>
      </div>

      <ForceGraph3D
        ref={graphRef}
        graphData={{ nodes, links }}
        width={dimensions.width}
        height={dimensions.height}
        backgroundColor="#09090b"
        nodeRelSize={5}
        nodeVal="val"
        nodeColor="color"
        nodeLabel={(d: any) => `${d.name} — ${d.fact_count} facts`}
        nodeOpacity={0.9}
        linkColor={() => "rgba(129, 140, 248, 0.25)"}
        linkWidth={0.8}
        linkLabel={(d: any) => d.label?.replace(/_/g, " ")}
        linkDirectionalParticles={2}
        linkDirectionalParticleSpeed={0.005}
        linkDirectionalParticleWidth={1.5}
        linkDirectionalParticleColor={() => "#818cf8"}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={0.9}
        linkDirectionalArrowColor={() => "rgba(129, 140, 248, 0.5)"}
        onNodeClick={handleNodeClick}
        onBackgroundClick={handleBackgroundClick}
        onEngineStop={handleEngineStop}
        warmupTicks={100}
        cooldownTicks={300}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
        enableNodeDrag={true}
        enableNavigationControls={true}
      />

      {/* Detail Panel */}
      {selectedNodeId && (
        <div className="absolute right-0 top-0 z-20 flex h-full w-96 flex-col border-l border-surface-2 bg-surface-0/95 backdrop-blur-md">
          {/* Close button */}
          <button
            onClick={handleBackgroundClick}
            className="absolute right-3 top-3 z-30 rounded-md p-1 text-text-tertiary hover:bg-surface-2 hover:text-text-primary"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>

          {panelLoading ? (
            <div className="flex flex-1 items-center justify-center">
              <div className="text-sm text-text-tertiary">Loading...</div>
            </div>
          ) : conceptDetail ? (
            <div className="flex-1 space-y-4 overflow-y-auto p-4 pt-8">
              {/* Header */}
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-medium text-text-primary">
                    {conceptDetail.name}
                  </h3>
                  <span className="rounded-full bg-accent/15 px-2 py-0.5 text-[10px] font-medium text-accent">
                    {conceptDetail.entity_type}
                  </span>
                </div>
                {conceptDetail.summary && (
                  <p className="mt-1 text-xs text-text-secondary">
                    {conceptDetail.summary}
                  </p>
                )}
                {(conceptDetail as any).community && (
                  <div className="mt-1.5 flex items-center gap-1.5">
                    <span className="inline-block h-2 w-2 rounded-full" style={{
                      backgroundColor: (conceptDetail as any).community_id != null
                        ? communityColorMap[(conceptDetail as any).community_id]
                        : undefined
                    }} />
                    <span className="text-[10px] text-text-tertiary">
                      {(conceptDetail as any).community.name}
                    </span>
                  </div>
                )}
              </div>

              {/* Facts — What you know */}
              <div>
                <h4 className="mb-2 text-[11px] font-medium uppercase tracking-wider text-text-tertiary">
                  What you know
                </h4>
                {conceptDetail.facts.length > 0 ? (
                  <div className="space-y-1.5">
                    {conceptDetail.facts.map((f) => (
                      <div
                        key={f.id}
                        className="rounded-lg border border-surface-2 bg-surface-1 px-3 py-2 text-xs text-text-secondary"
                      >
                        {f.content}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-text-tertiary">No facts recorded yet.</p>
                )}
              </div>

              {/* Passages — From Articles */}
              {conceptDetail.passages && conceptDetail.passages.length > 0 && (
                <div>
                  <h4 className="mb-2 text-[11px] font-medium uppercase tracking-wider text-text-tertiary">
                    From Articles
                  </h4>
                  <div className="space-y-2">
                    {conceptDetail.passages.map((p) => (
                      <div
                        key={p.id}
                        className="rounded-lg border border-accent/20 bg-accent/5 px-3 py-2.5"
                      >
                        <p className="text-xs leading-relaxed text-text-secondary whitespace-pre-line">
                          {p.content}
                        </p>
                        {p.articles && (
                          <p className="mt-1.5 text-[10px] text-text-tertiary">
                            From:{" "}
                            <a
                              href={p.articles.url || "#"}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-accent hover:underline"
                            >
                              {p.articles.title}
                            </a>
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Notes */}
              <div>
                <h4 className="mb-2 text-[11px] font-medium uppercase tracking-wider text-text-tertiary">
                  Your Notes
                </h4>
                {conceptDetail.notes.length > 0 && (
                  <div className="mb-2 space-y-1.5">
                    {conceptDetail.notes.map((n) => (
                      <div
                        key={n.id}
                        className="group flex items-start gap-2 rounded-lg border border-surface-2 bg-surface-1 px-3 py-2"
                      >
                        <p className="flex-1 text-xs text-text-secondary">
                          {n.content}
                        </p>
                        <button
                          onClick={() => handleDeleteNote(n.id)}
                          className="shrink-0 text-text-tertiary opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
                          title="Delete note"
                        >
                          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                            <path d="M3 3l6 6M9 3l-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                <form onSubmit={handleAddNote} className="flex gap-2">
                  <input
                    type="text"
                    value={noteText}
                    onChange={(e) => setNoteText(e.target.value)}
                    placeholder="Add a note..."
                    className="flex-1 rounded-lg border border-surface-2 bg-surface-1 px-3 py-1.5 text-xs text-text-primary placeholder:text-text-tertiary focus:border-accent/40 focus:outline-none"
                  />
                  <button
                    type="submit"
                    disabled={!noteText.trim() || savingNote}
                    className="shrink-0 rounded-lg bg-accent/15 px-3 py-1.5 text-xs font-medium text-accent transition-colors hover:bg-accent/25 disabled:opacity-40"
                  >
                    {savingNote ? "..." : "Save"}
                  </button>
                </form>
              </div>

              {/* Learning entries from voice/chat */}
              {conceptDetail.learning_entries.length > 0 && (
                <div>
                  <h4 className="mb-2 text-[11px] font-medium uppercase tracking-wider text-text-tertiary">
                    Learning History
                  </h4>
                  <div className="space-y-1.5">
                    {conceptDetail.learning_entries.map((l) => (
                      <div
                        key={l.id}
                        className="rounded-lg border border-surface-2 bg-surface-1 px-3 py-2"
                      >
                        <p className="text-xs text-text-secondary">{l.content}</p>
                        <p className="mt-0.5 text-[10px] text-text-tertiary">
                          {new Date(l.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Related articles */}
              {conceptDetail.related_articles.length > 0 && (
                <div>
                  <h4 className="mb-2 text-[11px] font-medium uppercase tracking-wider text-text-tertiary">
                    Related Articles
                  </h4>
                  <div className="space-y-1">
                    {conceptDetail.related_articles.map((a) => (
                      <a
                        key={a.id}
                        href={a.url || "#"}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block rounded-lg border border-surface-2 bg-surface-1 px-3 py-2 text-xs text-accent hover:bg-surface-2"
                      >
                        {a.title}
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Related concepts (from relations) */}
              {conceptDetail.relations.length > 0 && (
                <div>
                  <h4 className="mb-2 text-[11px] font-medium uppercase tracking-wider text-text-tertiary">
                    Connected Concepts
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {conceptDetail.relations.map((r) => {
                      const isSource = r.source_id === selectedNodeId;
                      const linkedId = isSource ? r.target_id : r.source_id;
                      const linkedName = isSource ? r.target_name : r.source_name;
                      return (
                        <button
                          key={r.id}
                          onClick={() => handleRelationClick(linkedId)}
                          className="rounded-full border border-surface-3 px-2.5 py-1 text-[11px] text-text-secondary transition-colors hover:border-accent/40 hover:text-accent"
                        >
                          {r.relation_type.replace(/_/g, " ")} → {linkedName}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-1 items-center justify-center">
              <p className="text-xs text-text-tertiary">
                Could not load concept details.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
