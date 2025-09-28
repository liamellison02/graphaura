'use client';

import React, { useRef, useCallback, useMemo, useEffect, useState } from 'react';
import ForceGraph3D, { ForceGraphMethods } from 'react-force-graph-3d';
import * as THREE from 'three';
import SpriteText from 'three-spritetext';
import { useGraphStore } from '@/stores/graphStore';
import { GraphNode, GraphLink, NODE_COLORS, NodeType } from '@/types/graph';

interface Graph3DProps {
  width?: number;
  height?: number;
  backgroundColor?: string;
}

function checkWebGLSupport(): boolean {
  try {
    const canvas = document.createElement('canvas');
    return !!(
      window.WebGLRenderingContext &&
      (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
    );
  } catch (e) {
    return false;
  }
}

export default function Graph3D({
  width,
  height,
  backgroundColor = '#000011',
}: Graph3DProps) {
  const graphRef = useRef<ForceGraphMethods | undefined>(undefined);
  const [webGLSupported, setWebGLSupported] = useState(true);
  const [renderError, setRenderError] = useState(false);
  const [isClient, setIsClient] = useState(false);

  const {
    graphData,
    selectedNode,
    hoveredNode,
    highlightedNodes,
    highlightedLinks,
    filterByType,
    searchQuery,
    setSelectedNode,
    setHoveredNode,
    getNeighbors,
  } = useGraphStore();

  useEffect(() => {
    setIsClient(true);
    const supported = checkWebGLSupport();
    setWebGLSupported(supported);

    const handleError = (e: ErrorEvent) => {
      if (e.message && (e.message.includes('WebGL') || e.message.includes('THREE'))) {
        console.error('WebGL Error caught:', e);
        setRenderError(true);
        setWebGLSupported(false);
        e.preventDefault();
      }
    };

    window.addEventListener('error', handleError);
    return () => window.removeEventListener('error', handleError);
  }, []);

  const filteredData = useMemo(() => {
    let nodes = graphData.nodes;
    let links = graphData.links;

    if (filterByType) {
      nodes = nodes.filter((node) => node.type === filterByType);
      const nodeIds = new Set(nodes.map((n) => n.id));
      links = links.filter((link) => {
        const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
        const targetId = typeof link.target === 'string' ? link.target : link.target.id;
        return nodeIds.has(sourceId) && nodeIds.has(targetId);
      });
    }

    if (searchQuery) {
      nodes = nodes.filter((node) =>
        node.name.toLowerCase().includes(searchQuery.toLowerCase())
      );
      const nodeIds = new Set(nodes.map((n) => n.id));
      links = links.filter((link) => {
        const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
        const targetId = typeof link.target === 'string' ? link.target : link.target.id;
        return nodeIds.has(sourceId) && nodeIds.has(targetId);
      });
    }

    return { nodes, links };
  }, [graphData, filterByType, searchQuery]);

  const handleNodeClick = useCallback(
    (node: any) => {
      setSelectedNode(node);

      if (graphRef.current) {
        const distance = 150;
        const distRatio = 1 + distance / Math.hypot(node.x || 0, node.y || 0, node.z || 0);

        graphRef.current.cameraPosition(
          {
            x: (node.x || 0) * distRatio,
            y: (node.y || 0) * distRatio,
            z: (node.z || 0) * distRatio,
          },
          node as any,
          1500
        );
      }
    },
    [setSelectedNode]
  );

  const handleNodeHover = useCallback(
    (node: any) => {
      setHoveredNode(node);
      document.body.style.cursor = node ? 'pointer' : 'default';

      if (node) {
        const neighbors = getNeighbors(node.id);
        useGraphStore.setState({
          highlightedNodes: neighbors.nodes,
          highlightedLinks: neighbors.links,
        });
      } else {
        useGraphStore.setState({
          highlightedNodes: new Set(),
          highlightedLinks: new Set(),
        });
      }
    },
    [setHoveredNode, getNeighbors]
  );

  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null);
  }, [setSelectedNode]);

  const nodeThreeObject = useCallback((node: any) => {
    try {
      const nodeColor = node.color || NODE_COLORS[node.type as NodeType];
      const group = new THREE.Group();

      const geometry = new THREE.SphereGeometry(node.val || 6, 16, 16);
      const material = new THREE.MeshPhongMaterial({
        color: nodeColor,
        emissive: nodeColor,
        emissiveIntensity: hoveredNode === node || selectedNode === node ? 0.5 : 0.2,
        shininess: 100,
        transparent: true,
        opacity: highlightedNodes.size > 0
          ? highlightedNodes.has(node.id) ? 1 : 0.2
          : 0.9,
      });
      const sphere = new THREE.Mesh(geometry, material);
      group.add(sphere);

      if (hoveredNode === node || selectedNode === node) {
        const glowGeometry = new THREE.SphereGeometry((node.val || 6) * 1.5, 8, 8);
        const glowMaterial = new THREE.MeshBasicMaterial({
          color: nodeColor,
          transparent: true,
          opacity: 0.15,
        });
        const glow = new THREE.Mesh(glowGeometry, glowMaterial);
        group.add(glow);
      }

      const sprite = new SpriteText(node.name);
      sprite.material.depthWrite = false;
      sprite.color = '#ffffff';
      sprite.textHeight = 3;
      sprite.position.y = (node.val || 6) + 8;
      sprite.backgroundColor = 'rgba(0,0,0,0.5)';
      sprite.padding = 2;
      sprite.borderRadius = 2;
      group.add(sprite);

      return group;
    } catch (error) {
      console.error('Error creating node object:', error);
      const geometry = new THREE.SphereGeometry(5);
      const material = new THREE.MeshBasicMaterial({ color: 0x3B82F6 });
      return new THREE.Mesh(geometry, material);
    }
  }, [highlightedNodes, hoveredNode, selectedNode]);

  const linkColor = useCallback((link: any) => {
    const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
    const targetId = typeof link.target === 'string' ? link.target : link.target.id;
    const linkId = `${sourceId}-${targetId}`;
    const isHighlighted = highlightedLinks.has(linkId);
    return isHighlighted ? '#ffffff' : '#4a5568';
  }, [highlightedLinks]);

  useEffect(() => {
    if (graphRef.current) {
      graphRef.current.d3Force('link')?.distance((link: any) => 80);
      graphRef.current.d3Force('charge')?.strength(-500);
      graphRef.current.d3Force('center')?.strength(0.05);
    }
  }, []);

  useEffect(() => {
    if (graphRef.current && !renderError) {
      try {
        const scene = graphRef.current.scene();

        const ambientLight = new THREE.AmbientLight(0x404040, 1);
        scene.add(ambientLight);

        const light1 = new THREE.DirectionalLight(0xffffff, 0.6);
        light1.position.set(1, 1, 1);
        scene.add(light1);
      } catch (error) {
        console.error('Error setting up scene:', error);
        setRenderError(true);
      }
    }
  }, [renderError]);

  if (!isClient || !webGLSupported || renderError) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-900 text-white p-8">
        <div className="text-center max-w-md">
          <h2 className="text-2xl font-bold mb-4">
            {!isClient ? 'Loading 3D Graph...' : '3D Visualization Not Available'}
          </h2>
          {isClient && (
            <>
              <p className="mb-4">
                Your browser or device doesn't support WebGL, which is required for 3D graphics.
              </p>
              <div className="bg-gray-800 rounded-lg p-4 mb-4">
                <h3 className="font-semibold mb-2">Try these solutions:</h3>
                <ul className="text-left space-y-2 text-sm">
                  <li>• Use Chrome, Firefox, or Safari (latest versions)</li>
                  <li>• Enable hardware acceleration in browser settings</li>
                  <li>• Check if WebGL is enabled at chrome://gpu</li>
                  <li>• Try on a different device or browser</li>
                </ul>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <h3 className="font-semibold mb-2">Graph Data Summary:</h3>
                <p className="text-sm">Nodes: {filteredData.nodes.length}</p>
                <p className="text-sm">Links: {filteredData.links.length}</p>
              </div>
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      <ForceGraph3D
        ref={graphRef}
        width={width}
        height={height}
        graphData={filteredData}
        backgroundColor={backgroundColor}
        nodeLabel="name"
        nodeRelSize={1}
        nodeVal={(node: any) => node.val || 6}
        nodeColor={(node: any) => node.color || NODE_COLORS[node.type as NodeType]}
        nodeOpacity={0.9}
        nodeResolution={8}
        nodeThreeObject={nodeThreeObject}
        nodeThreeObjectExtend={false}
        linkWidth={(link: any) => {
          const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
          const targetId = typeof link.target === 'string' ? link.target : link.target.id;
          const linkId = `${sourceId}-${targetId}`;
          return highlightedLinks.has(linkId) ? 2 : 1;
        }}
        linkOpacity={0.5}
        linkColor={linkColor}
        linkDirectionalParticles={(link: any) => {
          const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
          const targetId = typeof link.target === 'string' ? link.target : link.target.id;
          const linkId = `${sourceId}-${targetId}`;
          return highlightedLinks.has(linkId) ? 2 : 0;
        }}
        linkDirectionalParticleSpeed={0.005}
        linkDirectionalParticleWidth={2}
        linkDirectionalParticleColor={() => '#ffffff'}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        onBackgroundClick={handleBackgroundClick}
        showNavInfo={false}
        enableNodeDrag={true}
        enableNavigationControls={true}
        enablePointerInteraction={true}
        controlType="orbit"
        rendererConfig={{
          antialias: false,
          alpha: false,
          powerPreference: 'high-performance',
          failIfMajorPerformanceCaveat: false,
        }}
      />
    </div>
  );
}