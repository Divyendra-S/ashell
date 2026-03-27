"use client";

import { useCallback, useRef, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { motion, AnimatePresence } from "framer-motion";
import { useTheme } from "../lib/theme";
import type { GraphData, ConceptDetail, Stats } from "../lib/api";
import { getConceptDetail, createNote, deleteNote } from "../lib/api";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => null,
});

const CONCEPT_COLORS = [
  "#fbbf24", "#34d399", "#60a5fa", "#a78bfa",
  "#fb923c", "#f472b6", "#2dd4bf", "#e879f9",
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
}

interface GraphLink {
  source: number | GraphNode;
  target: number | GraphNode;
  label: string;
}

/* ── Collapsible section for secondary content ── */
function CollapsibleSection({ title, delay, children }: { title: string; delay: number; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
      className="border-t border-surface-2/25 py-4"
    >
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary transition-colors hover:text-text-tertiary"
      >
        <motion.svg
          width="10" height="10" viewBox="0 0 10 10" fill="none"
          animate={{ rotate: open ? 90 : 0 }}
          transition={{ duration: 0.15 }}
        >
          <path d="M3.5 2L6.5 5L3.5 8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
        </motion.svg>
        {title}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="overflow-hidden"
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/* ── Collapsible stats overlay ── */
function StatsOverlay({ stats }: { stats: Stats | null }) {
  const [open, setOpen] = useState(false);

  if (!stats) return null;

  const items = [
    { label: "Concepts", value: stats.entity_count, delta: stats.new_entities_7d },
    { label: "Facts", value: stats.fact_count, delta: stats.new_facts_7d },
    { label: "Articles", value: stats.article_count, delta: stats.new_articles_7d },
    { label: "Health", value: stats.health_score, suffix: "/ 100" },
  ];

  return (
    <div className="absolute left-4 top-4 z-20">
      <motion.button
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-full border border-surface-2/35 bg-surface-0/60 px-3 py-1.5 text-[11px] text-text-tertiary backdrop-blur-xl transition-colors duration-200 hover:border-surface-2/40 hover:text-text-secondary"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 14 14"
          fill="none"
          className="text-text-tertiary"
        >
          <rect x="1" y="1" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.2" />
          <rect x="8" y="1" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.2" />
          <rect x="1" y="8" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.2" />
          <rect x="8" y="8" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.2" />
        </svg>
        Stats
        <motion.svg
          width="10"
          height="10"
          viewBox="0 0 10 10"
          fill="none"
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <path d="M2.5 4L5 6.5L7.5 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
        </motion.svg>
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.97 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="mt-2 grid grid-cols-2 gap-2"
          >
            {items.map((item, i) => (
              <motion.div
                key={item.label}
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04, duration: 0.2 }}
                className="rounded-xl border border-surface-2/35 bg-surface-0/70 px-3.5 py-2.5 backdrop-blur-xl"
              >
                <p className="text-[9px] font-medium uppercase tracking-[0.12em] text-text-tertiary">
                  {item.label}
                </p>
                <div className="mt-0.5 flex items-baseline gap-1.5">
                  <span className="text-[18px] font-extralight leading-none tracking-tight text-text-primary">
                    {item.value}
                  </span>
                  {item.delta !== undefined && item.delta > 0 && (
                    <span className="text-[9px] font-medium text-mode-query">
                      +{item.delta}
                    </span>
                  )}
                  {item.suffix && (
                    <span className="text-[9px] text-text-tertiary">{item.suffix}</span>
                  )}
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ── Main component ── */
export function KnowledgeGraph({
  data,
  userId,
  stats,
}: {
  data: GraphData | null;
  userId: string;
  stats: Stats | null;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const hasInteracted = useRef(false);

  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [conceptDetail, setConceptDetail] = useState<ConceptDetail | null>(null);
  const [panelLoading, setPanelLoading] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [savingNote, setSavingNote] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) setDimensions({ width, height });
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    if (!graphRef.current) return;
    try {
      graphRef.current.d3Force("charge")?.strength(-150).distanceMax(300);
      graphRef.current.d3Force("link")?.distance(60);
    } catch {}
  });

  const focusNode = useCallback((node: any) => {
    if (!graphRef.current || !node) return;
    graphRef.current.centerAt(node.x, node.y, 500);
    graphRef.current.zoom(2.5, 500);
  }, []);

  const loadConceptDetail = useCallback(
    async (nodeId: number) => {
      setPanelLoading(true);
      try {
        setConceptDetail(await getConceptDetail(nodeId, userId));
      } catch {
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
      hasInteracted.current = true;
      focusNode(node);
      setSelectedNodeId(node.id);
      setNoteText("");
      loadConceptDetail(node.id);
    },
    [focusNode, loadConceptDetail]
  );

  const handleBackgroundClick = useCallback(() => {
    setSelectedNodeId(null);
    setConceptDetail(null);
    setNoteText("");
  }, []);

  const handleEngineStop = useCallback(() => {
    if (!hasInteracted.current) {
      graphRef.current?.zoomToFit(400, 60);
    }
  }, []);

  const handleNodeHover = useCallback((node: any) => {
    setHoveredNode(node || null);
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
      } catch {}
      setSavingNote(false);
    },
    [noteText, selectedNodeId, userId, loadConceptDetail]
  );

  const handleDeleteNote = useCallback(
    async (noteId: number) => {
      if (!selectedNodeId) return;
      try {
        await deleteNote(noteId, userId);
        await loadConceptDetail(selectedNodeId);
      } catch {}
    },
    [selectedNodeId, userId, loadConceptDetail]
  );

  const handleRelationClick = useCallback(
    (entityId: number) => {
      if (!graphRef.current) return;
      const node = graphRef.current.graphData().nodes.find((n: any) => n.id === entityId);
      if (node) focusNode(node);
      setSelectedNodeId(entityId);
      setNoteText("");
      loadConceptDetail(entityId);
    },
    [focusNode, loadConceptDetail]
  );

  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const size = Math.sqrt(node.val) * 4;
      const isHovered = hoveredNode?.id === node.id;
      const isSelected = selectedNodeId === node.id;
      const fontSize = Math.max(11 / globalScale, 1.5);

      if (isHovered || isSelected) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, size + 4, 0, 2 * Math.PI);
        ctx.fillStyle = node.color + "20";
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
      ctx.fillStyle = node.color + (isHovered || isSelected ? "cc" : "88");
      ctx.fill();
      ctx.strokeStyle = node.color + "40";
      ctx.lineWidth = 0.5;
      ctx.stroke();

      if (globalScale > 0.6 || isHovered || isSelected) {
        ctx.font = `${fontSize}px "Geist", system-ui, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle =
          isHovered || isSelected
            ? isDark ? "rgba(250, 250, 250, 0.95)" : "rgba(20, 20, 30, 0.95)"
            : isDark ? "rgba(250, 250, 250, 0.6)" : "rgba(20, 20, 30, 0.55)";
        ctx.fillText(node.name, node.x, node.y + size + 3);
      }
    },
    [hoveredNode, selectedNodeId, isDark]
  );

  const nodePointerAreaPaint = useCallback(
    (node: any, color: string, ctx: CanvasRenderingContext2D) => {
      ctx.beginPath();
      ctx.arc(node.x, node.y, Math.sqrt(node.val) * 4 + 4, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();
    },
    []
  );

  if (!data || !data.entities.length) {
    return (
      <div
        ref={containerRef}
        className="gradient-page flex h-full items-center justify-center bg-surface-0"
      >
        <div className="flex flex-col items-center text-center">
          {data ? (
            <>
              <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-accent/8">
                <span className="text-2xl font-extralight text-accent">K</span>
              </div>
              <p className="mb-2 text-[14px] font-light text-text-secondary">
                Your knowledge graph is empty
              </p>
              <p className="mb-5 max-w-xs text-[12px] text-text-tertiary">
                Ingest an article or chat with Kuro to start building your knowledge graph
              </p>
              <button
                onClick={() => {
                  sessionStorage.setItem("kuro_prefill", "/ingest-url ");
                  window.location.href = "/";
                }}
                className="rounded-full border border-accent/20 bg-accent/5 px-5 py-2 text-[12px] text-accent transition-all duration-200 hover:border-accent/35 hover:bg-accent/10"
              >
                Ingest your first article
              </button>
            </>
          ) : (
            <div className="space-y-3">
              <div className="mx-auto h-5 w-32 skeleton" />
              <div className="mx-auto h-3 w-48 skeleton" />
            </div>
          )}
        </div>
      </div>
    );
  }

  const communityIds = [
    ...new Set(data.entities.map((e) => e.community_id).filter((c): c is number => c != null)),
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
    val: Math.max(2, e.fact_count * 1.5 + 1),
    color: e.community_id != null ? communityColorMap[e.community_id] : hashColor(e.name),
  }));

  const nodeIds = new Set(nodes.map((n) => n.id));
  const links: GraphLink[] = data.relations
    .filter((r) => nodeIds.has(r.source_id) && nodeIds.has(r.target_id))
    .map((r) => ({ source: r.source_id, target: r.target_id, label: r.relation_type }));

  const selectedNodeColor = selectedNodeId != null
    ? nodes.find((n) => n.id === selectedNodeId)?.color
    : undefined;

  return (
    <div ref={containerRef} className="relative h-full overflow-hidden bg-surface-0">
      {/* Stats overlay — collapsible top-left */}
      <StatsOverlay stats={stats} />

      {/* Node count + hint — bottom-left */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6, duration: 0.5 }}
        className="absolute bottom-4 left-4 z-10 flex items-center gap-3"
      >
        <span className="rounded-full border border-surface-2/35 bg-surface-0/60 px-3 py-1.5 text-[10px] text-text-tertiary backdrop-blur-xl">
          {nodes.length} concepts · {links.length} connections
        </span>
        <span className="text-[10px] text-text-tertiary">
          Drag to pan · Scroll to zoom · Click to explore
        </span>
      </motion.div>

      {dimensions.width > 0 && dimensions.height > 0 && (
      <ForceGraph2D
        ref={graphRef}
        graphData={{ nodes, links }}
        width={dimensions.width}
        height={dimensions.height}
        backgroundColor={isDark ? "#0c0c0f" : "#fafafa"}
        nodeRelSize={4}
        nodeVal="val"
        nodeCanvasObject={nodeCanvasObject}
        nodePointerAreaPaint={nodePointerAreaPaint}
        linkColor={() => isDark ? "rgba(161, 161, 170, 0.12)" : "rgba(100, 100, 120, 0.15)"}
        linkWidth={0.6}
        linkLabel={(d: any) => d.label?.replace(/_/g, " ")}
        linkDirectionalArrowLength={3}
        linkDirectionalArrowRelPos={0.9}
        linkDirectionalArrowColor={() => isDark ? "rgba(161, 161, 170, 0.25)" : "rgba(100, 100, 120, 0.3)"}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        onBackgroundClick={handleBackgroundClick}
        onEngineStop={handleEngineStop}
        warmupTicks={100}
        cooldownTicks={300}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
        enableNodeDrag={true}
        enableZoomInteraction={true}
        enablePanInteraction={true}
      />
      )}

      {/* Detail Panel — inset from top, rounded */}
      <AnimatePresence>
        {selectedNodeId && (
          <motion.div
            key="detail-panel"
            initial={{ x: "100%", opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: "100%", opacity: 0 }}
            transition={{ type: "spring", damping: 28, stiffness: 280 }}
            className="absolute right-3 top-3 bottom-3 z-20 flex w-[380px] flex-col overflow-hidden rounded-2xl border border-surface-2/35 bg-surface-0/[0.97] backdrop-blur-2xl"
          >
            {/* Top accent gradient */}
            <div
              className="h-[2px] w-full shrink-0"
              style={{ background: `linear-gradient(90deg, ${selectedNodeColor || "#818cf8"}80, transparent)` }}
            />

            {/* Close */}
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              onClick={handleBackgroundClick}
              className="absolute right-3 top-4 z-30 rounded-full p-1.5 text-text-tertiary transition-all duration-200 hover:bg-surface-2/40 hover:text-text-primary"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M3.5 3.5l7 7M10.5 3.5l-7 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </motion.button>

            {panelLoading ? (
              <div className="gradient-panel flex-1 p-5">
                <div className="space-y-3">
                  <div className="h-5 w-36 skeleton" />
                  <div className="h-3 w-56 skeleton" />
                </div>
                <div className="mt-6 space-y-2">
                  <div className="h-2 w-20 skeleton" />
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-3 skeleton" style={{ animationDelay: `${i * 100}ms`, width: `${90 - i * 15}%` }} />
                  ))}
                </div>
              </div>
            ) : conceptDetail ? (
              <div className="flex flex-1 flex-col overflow-hidden">
                {/* Header — fixed at top */}
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: 0.1 }}
                  className="shrink-0 px-5 pb-3 pt-4"
                  style={{ background: `linear-gradient(180deg, rgba(var(--gradient-accent-rgb),0.03) 0%, transparent 100%)` }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="text-[17px] font-light tracking-tight text-text-primary leading-snug">
                      {conceptDetail.name}
                    </h3>
                  </div>
                  <div className="mt-1 flex items-center gap-2">
                    <span className="rounded-full bg-accent/8 px-2 py-[2px] text-[9px] font-medium uppercase tracking-wider text-accent">
                      {conceptDetail.entity_type}
                    </span>
                    {(conceptDetail as any).community && (
                      <>
                        <span className="text-text-tertiary">·</span>
                        <div className="flex items-center gap-1">
                          <span
                            className="inline-block h-[5px] w-[5px] rounded-full"
                            style={{
                              backgroundColor: (conceptDetail as any).community_id != null
                                ? communityColorMap[(conceptDetail as any).community_id]
                                : undefined,
                            }}
                          />
                          <span className="text-[9px] text-text-tertiary">
                            {(conceptDetail as any).community.name}
                          </span>
                        </div>
                      </>
                    )}
                  </div>
                  {conceptDetail.summary && (
                    <p className="mt-2.5 text-[12px] leading-[1.7] text-text-secondary">
                      {conceptDetail.summary}
                    </p>
                  )}

                  {/* Connected Concepts — right below header, navigation first */}
                  {conceptDetail.relations.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.2 }}
                      className="mt-3 flex flex-wrap gap-1.5"
                    >
                      {conceptDetail.relations.map((r, i) => {
                        const isSource = r.source_id === selectedNodeId;
                        const linkedId = isSource ? r.target_id : r.source_id;
                        const linkedName = isSource ? r.target_name : r.source_name;
                        const linkedNode = nodes.find((n) => n.id === linkedId);
                        return (
                          <motion.button
                            key={r.id}
                            initial={{ opacity: 0, scale: 0.92 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ duration: 0.15, delay: 0.22 + i * 0.025 }}
                            whileHover={{ scale: 1.04 }}
                            whileTap={{ scale: 0.97 }}
                            onClick={() => handleRelationClick(linkedId)}
                            className="flex items-center gap-1 rounded-full border border-surface-2/35 px-2 py-[3px] text-[10px] text-text-tertiary transition-all duration-150 hover:border-accent/25 hover:text-accent"
                          >
                            {linkedNode && (
                              <span className="inline-block h-1 w-1 rounded-full" style={{ backgroundColor: linkedNode.color, opacity: 0.6 }} />
                            )}
                            {linkedName}
                          </motion.button>
                        );
                      })}
                    </motion.div>
                  )}
                </motion.div>

                <div className="h-px shrink-0 bg-surface-2/15" />

                {/* Scrollable content */}
                <div className="flex-1 overflow-y-auto px-5 pb-20">
                  {/* Key Facts — bullet list style, no cards */}
                  <motion.div
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: 0.15 }}
                    className="py-4"
                  >
                    <h4 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
                      Key Facts
                    </h4>
                    {conceptDetail.facts.length > 0 ? (
                      <ul className="space-y-2">
                        {conceptDetail.facts.map((f, i) => (
                          <motion.li
                            key={f.id}
                            initial={{ opacity: 0, x: -6 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.2, delay: 0.2 + i * 0.035 }}
                            className="flex gap-2.5 text-[12px] leading-[1.65] text-text-secondary"
                          >
                            <span className="mt-[9px] h-[3px] w-[3px] shrink-0 rounded-full bg-accent/40" />
                            <span>{f.content}</span>
                          </motion.li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-[11px] text-text-tertiary">No facts recorded yet.</p>
                    )}
                  </motion.div>

                  {/* Source Passages — blockquote style with left border */}
                  {conceptDetail.passages && conceptDetail.passages.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: 0.2 }}
                      className="border-t border-surface-2/25 py-4"
                    >
                      <h4 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
                        Sources
                      </h4>
                      <div className="space-y-3">
                        {conceptDetail.passages.map((p, i) => (
                          <motion.div
                            key={p.id}
                            initial={{ opacity: 0, x: -6 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.2, delay: 0.25 + i * 0.04 }}
                            className="border-l-2 border-accent/20 pl-3.5"
                          >
                            <p className="whitespace-pre-line text-[11.5px] leading-[1.7] text-text-secondary italic">
                              {p.content}
                            </p>
                            {p.articles && (
                              <a
                                href={p.articles.url || "#"}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="mt-1.5 inline-flex items-center gap-1 text-[10px] text-accent transition-colors hover:text-accent"
                              >
                                <svg width="10" height="10" viewBox="0 0 10 10" fill="none" className="shrink-0">
                                  <path d="M3.5 1.5h5v5M8.5 1.5l-7 7" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                                {p.articles.title}
                              </a>
                            )}
                          </motion.div>
                        ))}
                      </div>
                    </motion.div>
                  )}

                  {/* Notes — clean list */}
                  {conceptDetail.notes.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: 0.25 }}
                      className="border-t border-surface-2/25 py-4"
                    >
                      <h4 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
                        Notes
                      </h4>
                      <div className="space-y-1.5">
                        {conceptDetail.notes.map((n, i) => (
                          <motion.div
                            key={n.id}
                            initial={{ opacity: 0, x: -4 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.15, delay: 0.3 + i * 0.03 }}
                            className="group flex items-start gap-2"
                          >
                            <span className="mt-[7px] text-[10px] text-mode-ingest/40">~</span>
                            <p className="flex-1 text-[12px] leading-[1.6] text-text-secondary">{n.content}</p>
                            <button
                              onClick={() => handleDeleteNote(n.id)}
                              className="mt-0.5 shrink-0 rounded p-0.5 text-text-tertiary opacity-0 transition-all duration-150 hover:text-red-400/80 group-hover:opacity-100"
                            >
                              <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                                <path d="M2.5 2.5l5 5M7.5 2.5l-5 5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                              </svg>
                            </button>
                          </motion.div>
                        ))}
                      </div>
                    </motion.div>
                  )}

                  {/* Learning History — collapsible */}
                  {conceptDetail.learning_entries.length > 0 && (
                    <CollapsibleSection title="Learning History" delay={0.3}>
                      <div className="space-y-2 pt-1">
                        {conceptDetail.learning_entries.map((l) => (
                          <div key={l.id} className="flex gap-2.5 text-[11.5px] leading-[1.6]">
                            <span className="shrink-0 text-[10px] text-text-tertiary">{new Date(l.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</span>
                            <span className="text-text-secondary">{l.content}</span>
                          </div>
                        ))}
                      </div>
                    </CollapsibleSection>
                  )}

                  {/* Related Articles — compact links */}
                  {conceptDetail.related_articles.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: 0.35 }}
                      className="border-t border-surface-2/25 py-4"
                    >
                      <h4 className="mb-2.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
                        Related Reading
                      </h4>
                      <div className="space-y-1">
                        {conceptDetail.related_articles.map((a, i) => (
                          <motion.a
                            key={a.id}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.4 + i * 0.03 }}
                            href={a.url || "#"}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="group flex items-center gap-2 py-1 text-[11px] text-text-tertiary transition-colors hover:text-accent"
                          >
                            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" className="shrink-0 opacity-40 group-hover:opacity-70">
                              <path d="M3.5 1.5h5v5M8.5 1.5l-7 7" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                            <span className="truncate">{a.title}</span>
                          </motion.a>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </div>

                {/* Sticky note input — pinned at bottom */}
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="shrink-0 border-t border-surface-2/30 bg-surface-0/90 px-5 py-3 backdrop-blur-md"
                >
                  <form onSubmit={handleAddNote} className="flex gap-2">
                    <input
                      type="text"
                      value={noteText}
                      onChange={(e) => setNoteText(e.target.value)}
                      placeholder="Add a note..."
                      className="flex-1 rounded-lg border border-surface-2/35 bg-transparent px-3 py-2 text-[12px] text-text-primary placeholder:text-text-tertiary transition-colors duration-200 focus:border-accent/30 focus:outline-none"
                    />
                    <button
                      type="submit"
                      disabled={!noteText.trim() || savingNote}
                      className="shrink-0 rounded-lg bg-accent/10 px-3 py-2 text-[11px] font-medium text-accent transition-all duration-200 hover:bg-accent/20 hover:text-accent disabled:opacity-20"
                    >
                      {savingNote ? (
                        <span className="inline-block h-3 w-3 animate-spin rounded-full border border-accent/40 border-t-accent" />
                      ) : "Save"}
                    </button>
                  </form>
                </motion.div>
              </div>
            ) : (
              <div className="flex flex-1 items-center justify-center">
                <p className="text-[12px] text-text-tertiary">Could not load concept details.</p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
