'use client';

import React, { useRef, useCallback, useMemo, useEffect } from 'react';
import ForceGraph3D, { ForceGraphMethods } from 'react-force-graph-3d';
import * as THREE from 'three';
import { useGraphStore } from '@/stores/graphStore';
import { GraphNode, GraphLink, NODE_COLORS } from '@/types/graph';

interface Graph3DProps {
  width?: number;
  height?: number;
  backgroundColor?: string;
}

export default function Graph3D({
  width,
  height,
  backgroundColor = '#0a0a0a',
}: Graph3DProps) {
  const graphRef = useRef<ForceGraphMethods>();

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
    (node: GraphNode) => {
      setSelectedNode(node);

      if (graphRef.current) {
        const distance = 100;
        const distRatio = 1 + distance / Math.hypot(node.x || 0, node.y || 0, node.z || 0);

        graphRef.current.cameraPosition(
          {
            x: (node.x || 0) * distRatio,
            y: (node.y || 0) * distRatio,
            z: (node.z || 0) * distRatio,
          },
          node as any,
          1000
        );
      }
    },
    [setSelectedNode]
  );

  const handleNodeHover = useCallback(
    (node: GraphNode | null) => {
      setHoveredNode(node);

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

  const nodeThreeObject = useCallback((node: GraphNode) => {
    const geometry = new THREE.SphereGeometry(node.val || 5);
    const material = new THREE.MeshLambertMaterial({
      color: node.color || NODE_COLORS[node.type],
      transparent: true,
      opacity: highlightedNodes.size > 0
        ? highlightedNodes.has(node.id) ? 1 : 0.3
        : 1,
    });

    const mesh = new THREE.Mesh(geometry, material);

    if (node === selectedNode) {
      const ringGeometry = new THREE.RingGeometry(
        (node.val || 5) + 2,
        (node.val || 5) + 4,
        32
      );
      const ringMaterial = new THREE.MeshBasicMaterial({
        color: 0xffffff,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.5,
      });
      const ring = new THREE.Mesh(ringGeometry, ringMaterial);
      mesh.add(ring);
    }

    return mesh;
  }, [highlightedNodes, selectedNode]);

  const linkThreeObject = useCallback((link: GraphLink) => {
    const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
    const targetId = typeof link.target === 'string' ? link.target : link.target.id;
    const linkId = `${sourceId}-${targetId}`;

    const material = new THREE.MeshLambertMaterial({
      color: link.color || 0x666666,
      transparent: true,
      opacity: highlightedLinks.size > 0
        ? highlightedLinks.has(linkId) ? 0.8 : 0.2
        : 0.5,
    });

    const geometry = new THREE.CylinderGeometry(0.5, 0.5, 1);
    const mesh = new THREE.Mesh(geometry, material);

    return mesh;
  }, [highlightedLinks]);

  useEffect(() => {
    if (graphRef.current) {
      graphRef.current.d3Force('link')?.distance((link: any) => link.strength ? 100 / link.strength : 100);
      graphRef.current.d3Force('charge')?.strength(-300);
    }
  }, []);

  return (
    <div className="relative w-full h-full">
      <ForceGraph3D
        ref={graphRef}
        width={width}
        height={height}
        graphData={filteredData}
        nodeLabel="name"
        nodeColor={(node: any) => node.color || NODE_COLORS[node.type]}
        nodeOpacity={0.9}
        nodeThreeObject={nodeThreeObject}
        nodeThreeObjectExtend={false}
        linkLabel="relationship"
        linkThreeObject={linkThreeObject}
        linkThreeObjectExtend={false}
        linkPositionUpdate={(sprite: any, { start, end }: any) => {
          const middlePos = Object.assign(
            ...['x', 'y', 'z'].map(c => ({
              [c]: start[c] + (end[c] - start[c]) / 2
            }))
          );
          Object.assign(sprite.position, middlePos);

          const distance = Math.sqrt(
            Math.pow(end.x - start.x, 2) +
            Math.pow(end.y - start.y, 2) +
            Math.pow(end.z - start.z, 2)
          );
          sprite.scale.z = distance;

          sprite.lookAt(end.x, end.y, end.z);
          sprite.rotateX(Math.PI / 2);
        }}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        onBackgroundClick={handleBackgroundClick}
        backgroundColor={backgroundColor}
        showNavInfo={false}
        enableNodeDrag={true}
        enableNavigationControls={true}
        enablePointerInteraction={true}
      />
    </div>
  );
}