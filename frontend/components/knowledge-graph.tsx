"use client";

import { useCallback, useRef, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import type { GraphData } from "../lib/api";

const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
  ssr: false,
  loading: () => null,
});

const TYPE_COLORS: Record<string, string> = {
  person: "#a78bfa",
  company: "#f472b6",
  project: "#34d399",
  topic: "#fbbf24",
  place: "#60a5fa",
  event: "#fb923c",
};

const DEFAULT_COLOR = "#a1a1aa";

interface GraphNode {
  id: number;
  name: string;
  entity_type: string;
  fact_count: number;
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

export function KnowledgeGraph({ data }: { data: GraphData | null }) {
  const router = useRouter();
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const bloomAdded = useRef(false);

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

  // Add bloom post-processing once graph mounts
  useEffect(() => {
    if (!graphRef.current || bloomAdded.current) return;
    try {
      const THREE = require("three");
      const { UnrealBloomPass } = require("three/examples/jsm/postprocessing/UnrealBloomPass.js");
      const composer = graphRef.current.postProcessingComposer();
      if (!composer) return;
      const bloomPass = new UnrealBloomPass(
        new THREE.Vector2(dimensions.width, dimensions.height),
        1.0,  // strength
        0.4,  // radius
        0.85  // threshold
      );
      composer.addPass(bloomPass);
      bloomAdded.current = true;
    } catch {
      // postprocessing not available yet
    }
  });

  // Configure forces after graph mounts
  useEffect(() => {
    if (!graphRef.current) return;
    const fg = graphRef.current;
    try {
      fg.d3Force("charge")?.strength(-200).distanceMax(400);
      fg.d3Force("link")?.distance(80);
    } catch {
      // forces not ready yet
    }
  });

  const handleNodeClick = useCallback(
    (node: any) => {
      if (!node?.id || !graphRef.current) return;
      // Fly camera to clicked node
      const distance = 120;
      const distRatio = 1 + distance / Math.hypot(node.x || 0, node.y || 0, node.z || 0);
      graphRef.current.cameraPosition(
        {
          x: (node.x || 0) * distRatio,
          y: (node.y || 0) * distRatio,
          z: (node.z || 0) * distRatio,
        },
        { x: node.x, y: node.y, z: node.z },
        500
      );
      // Navigate after fly animation
      setTimeout(() => router.push(`/entity/${node.id}`), 600);
    },
    [router]
  );

  const handleEngineStop = useCallback(() => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(400, 100);
    }
  }, []);

  if (!data || !data.entities.length) {
    return (
      <div
        ref={containerRef}
        className="flex items-center justify-center rounded-xl border border-surface-2 bg-surface-1"
        style={{ height: "calc(100vh - 280px)", minHeight: 500 }}
      >
        <p className="text-sm text-text-tertiary">
          {data ? "No entities yet. Start capturing knowledge!" : "Loading graph..."}
        </p>
      </div>
    );
  }

  const nodes: GraphNode[] = data.entities.map((e) => ({
    id: e.id,
    name: e.name,
    entity_type: e.entity_type,
    fact_count: e.fact_count,
    val: Math.max(3, e.fact_count * 2 + 2),
    color: TYPE_COLORS[e.entity_type] || DEFAULT_COLOR,
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
      {/* Legend */}
      <div className="absolute right-3 top-3 z-10 flex flex-wrap gap-2 rounded-lg bg-surface-0/80 px-3 py-2 backdrop-blur-sm">
        {Object.entries(TYPE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <div
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="text-[10px] text-text-tertiary">{type}</span>
          </div>
        ))}
      </div>

      {/* Hint */}
      <div className="absolute bottom-3 left-3 z-10 rounded-lg bg-surface-0/80 px-3 py-1.5 backdrop-blur-sm">
        <span className="text-[10px] text-text-tertiary">
          Orbit to explore · Click a node to dive in
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
        nodeLabel={(d: any) => `${d.name} (${d.entity_type}) — ${d.fact_count} facts`}
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
        onEngineStop={handleEngineStop}
        warmupTicks={100}
        cooldownTicks={300}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
        enableNodeDrag={true}
        enableNavigationControls={true}
      />
    </div>
  );
}
